from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Iterable, Sequence

from lxml import etree

from ._docx_preservation_model import (
    COMMENTS_CONTENT_TYPE,
    COMMENTS_REL_TYPE,
    CT,
    NS,
    PKG_REL_NS,
    REL,
    W,
    W_NS,
    XML_NS,
    DocxMappingError,
    _IndexedPackage,
    _InternalLocation,
    _local_name,
)
from .review_session import PlannedAnnotation, PlannedTextEdit


def _clone_run_properties(run: etree._Element) -> etree._Element | None:
    properties = run.find("w:rPr", NS)
    return copy.deepcopy(properties) if properties is not None else None


def _set_space_preserve(node: etree._Element, value: str) -> None:
    if value[:1].isspace() or value[-1:].isspace():
        node.set(f"{{{XML_NS}}}space", "preserve")


def _plain_run(value: str, run_properties: etree._Element | None) -> etree._Element:
    run = etree.Element(f"{W}r")
    if run_properties is not None:
        run.append(copy.deepcopy(run_properties))
    text = etree.SubElement(run, f"{W}t")
    _set_space_preserve(text, value)
    text.text = value
    return run


def _revision(
    tag: str,
    value: str,
    run_properties: etree._Element | None,
    revision_id: int,
    timestamp: str,
) -> etree._Element:
    revision = etree.Element(f"{W}{tag}")
    revision.set(f"{W}id", str(revision_id))
    revision.set(f"{W}author", "AutoCite")
    revision.set(f"{W}date", timestamp)
    run = etree.SubElement(revision, f"{W}r")
    if run_properties is not None:
        run.append(copy.deepcopy(run_properties))
    text_tag = "delText" if tag == "del" else "t"
    text = etree.SubElement(run, f"{W}{text_tag}")
    _set_space_preserve(text, value)
    text.text = value
    return revision


def _max_numeric_attribute(roots: Iterable[etree._Element], attribute: str) -> int:
    maximum = 0
    for root in roots:
        for node in root.iter():
            raw = node.attrib.get(attribute)
            if raw is None:
                continue
            try:
                maximum = max(maximum, int(raw))
            except ValueError:
                continue
    return maximum


def _replace_run_with_edits(
    location: _InternalLocation,
    edits: Sequence[tuple[PlannedTextEdit, int, int]],
    *,
    tracked: bool,
    next_revision_id: int,
) -> int:
    node = location.node
    if node is None:
        raise DocxMappingError("accepted edit has no mapped Word text node")
    run = node.getparent()
    parent = run.getparent() if run is not None else None
    if (
        run is None
        or parent is None
        or _local_name(run) != "r"
        or _local_name(parent) != "p"
    ):
        raise DocxMappingError(
            "accepted edit cannot be mapped unambiguously to a simple Word run"
        )
    original = location.public.text
    ordered = sorted(edits, key=lambda item: (item[1], item[2]))
    cursor = 0
    for _, start, end in ordered:
        if start < cursor:
            raise DocxMappingError("accepted edits overlap inside one Word text node")
        cursor = end
    if not tracked:
        output: list[str] = []
        cursor = 0
        for edit, start, end in ordered:
            output.append(original[cursor:start])
            output.append(edit.replacement)
            cursor = end
        output.append(original[cursor:])
        node.text = "".join(output)
        _set_space_preserve(node, node.text or "")
        return next_revision_id

    if any(
        "\n" in edit.replacement or "\t" in edit.replacement
        for edit, _, _ in ordered
    ):
        raise DocxMappingError(
            "tracked replacements containing tabs or line breaks are not supported"
        )
    properties = _clone_run_properties(run)
    replacement_nodes: list[etree._Element] = []
    cursor = 0
    timestamp = datetime.now(timezone.utc).isoformat()
    for edit, start, end in ordered:
        prefix = original[cursor:start]
        if prefix:
            replacement_nodes.append(_plain_run(prefix, properties))
        deleted = original[start:end]
        if deleted:
            replacement_nodes.append(
                _revision("del", deleted, properties, next_revision_id, timestamp)
            )
            next_revision_id += 1
        if edit.replacement:
            replacement_nodes.append(
                _revision(
                    "ins", edit.replacement, properties, next_revision_id, timestamp
                )
            )
            next_revision_id += 1
        cursor = end
    suffix = original[cursor:]
    if suffix:
        replacement_nodes.append(_plain_run(suffix, properties))
    position = parent.index(run)
    parent.remove(run)
    for offset, replacement in enumerate(replacement_nodes):
        parent.insert(position + offset, replacement)
    return next_revision_id


def _comment_reference_run(comment_id: int) -> etree._Element:
    run = etree.Element(f"{W}r")
    properties = etree.SubElement(run, f"{W}rPr")
    style = etree.SubElement(properties, f"{W}rStyle")
    style.set(f"{W}val", "CommentReference")
    reference = etree.SubElement(run, f"{W}commentReference")
    reference.set(f"{W}id", str(comment_id))
    return run


def _anchor_comment(
    location: _InternalLocation,
    *,
    local_start: int,
    local_end: int,
    comment_id: int,
) -> None:
    node = location.node
    if node is None:
        raise DocxMappingError("annotation has no mapped Word text node")
    run = node.getparent()
    parent = run.getparent() if run is not None else None
    if run is None or parent is None or _local_name(parent) != "p":
        raise DocxMappingError("annotation cannot be mapped to a simple Word paragraph")
    original = location.public.text
    prefix = original[:local_start]
    target = original[local_start:local_end]
    suffix = original[local_end:]
    if not target:
        raise DocxMappingError("annotation target is empty")
    properties = _clone_run_properties(run)
    nodes: list[etree._Element] = []
    if prefix:
        nodes.append(_plain_run(prefix, properties))
    start_node = etree.Element(f"{W}commentRangeStart")
    start_node.set(f"{W}id", str(comment_id))
    nodes.append(start_node)
    nodes.append(_plain_run(target, properties))
    end_node = etree.Element(f"{W}commentRangeEnd")
    end_node.set(f"{W}id", str(comment_id))
    nodes.append(end_node)
    nodes.append(_comment_reference_run(comment_id))
    if suffix:
        nodes.append(_plain_run(suffix, properties))
    position = parent.index(run)
    parent.remove(run)
    for offset, replacement in enumerate(nodes):
        parent.insert(position + offset, replacement)


def _next_relationship_id(root: etree._Element) -> str:
    used = {node.attrib.get("Id", "") for node in root.findall(f"{REL}Relationship")}
    number = 1
    while f"rId{number}" in used:
        number += 1
    return f"rId{number}"


def _ensure_comments_support(
    indexed: _IndexedPackage,
) -> tuple[etree._Element, int, set[str]]:
    modified: set[str] = set()
    comments_name = "word/comments.xml"
    comments_root = indexed.roots.get(comments_name)
    if comments_root is None:
        comments_root = etree.Element(f"{W}comments", nsmap={"w": W_NS})
        indexed.roots[comments_name] = comments_root
        modified.add(comments_name)

    rels_name = "word/_rels/document.xml.rels"
    rels_root = indexed.roots.get(rels_name)
    if rels_root is None:
        rels_root = etree.Element(f"{REL}Relationships", nsmap={None: PKG_REL_NS})
        indexed.roots[rels_name] = rels_root
        modified.add(rels_name)
    has_comments_relationship = any(
        node.attrib.get("Type") == COMMENTS_REL_TYPE
        for node in rels_root.findall(f"{REL}Relationship")
    )
    if not has_comments_relationship:
        relationship = etree.SubElement(rels_root, f"{REL}Relationship")
        relationship.set("Id", _next_relationship_id(rels_root))
        relationship.set("Type", COMMENTS_REL_TYPE)
        relationship.set("Target", "comments.xml")
        modified.add(rels_name)

    content_types_name = "[Content_Types].xml"
    content_types = indexed.roots[content_types_name]
    has_override = any(
        node.attrib.get("PartName") == "/word/comments.xml"
        for node in content_types.findall(f"{CT}Override")
    )
    if not has_override:
        override = etree.SubElement(content_types, f"{CT}Override")
        override.set("PartName", "/word/comments.xml")
        override.set("ContentType", COMMENTS_CONTENT_TYPE)
        modified.add(content_types_name)

    existing_ids: list[int] = []
    for comment in comments_root.findall("w:comment", NS):
        raw = comment.attrib.get(f"{W}id")
        try:
            existing_ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    return comments_root, max(existing_ids, default=-1) + 1, modified


def _append_comment(
    comments_root: etree._Element,
    annotation: PlannedAnnotation,
    *,
    comment_id: int,
) -> None:
    comment = etree.SubElement(comments_root, f"{W}comment")
    comment.set(f"{W}id", str(comment_id))
    comment.set(f"{W}author", "AutoCite")
    comment.set(f"{W}date", datetime.now(timezone.utc).isoformat())
    paragraph = etree.SubElement(comment, f"{W}p")
    run = etree.SubElement(paragraph, f"{W}r")
    text = etree.SubElement(run, f"{W}t")
    details = [f"{annotation.code}: {annotation.message}"]
    details.append(
        f"Status: {annotation.correction_level}; confidence: {annotation.confidence}."
    )
    if annotation.rule:
        details.append(f"Rule family: {annotation.rule}.")
    if annotation.missing_facts:
        details.append("Missing facts: " + ", ".join(annotation.missing_facts) + ".")
    details.append(f"Provenance: {annotation.provenance}.")
    text.text = " ".join(details)
