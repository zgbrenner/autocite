from __future__ import annotations

from typing import Mapping, Sequence

from lxml import etree

from ._docx_preservation_model import (
    NS,
    W,
    DocxMappingError,
    DocxTextIndex,
    DocxTextLocation,
    DocxValidationError,
    _IndexedPackage,
    _InternalLocation,
    _Package,
    _Segment,
    _local_name,
    _parse_xml,
)
from ._docx_preservation_package import _read_package


def _simple_text_node(node: etree._Element) -> tuple[bool, str | None]:
    if _local_name(node) != "t":
        return False, "only ordinary Word text nodes are editable"
    run = node.getparent()
    if run is None or _local_name(run) != "r":
        return False, "text node is not contained in a Word run"
    parent = run.getparent()
    if parent is None or _local_name(parent) != "p":
        return False, "text run is nested in a protected Word structure"
    content_children = [child for child in run if _local_name(child) != "rPr"]
    if content_children != [node]:
        return False, "Word run contains fields, breaks, or multiple text nodes"
    protected = {
        "del",
        "ins",
        "moveFrom",
        "moveTo",
        "hyperlink",
        "fldSimple",
        "sdt",
        "smartTag",
    }
    ancestor = run.getparent()
    while ancestor is not None:
        if _local_name(ancestor) in protected:
            return False, "text is inside an existing revision, hyperlink, or field"
        ancestor = ancestor.getparent()
    return True, None


def _paragraph_segments(
    paragraph: etree._Element,
    *,
    part_name: str,
    root: etree._Element,
    note_numbers: Mapping[str, str],
) -> list[_Segment]:
    segments: list[_Segment] = []

    def walk(element: etree._Element) -> None:
        tag = _local_name(element)
        if tag in {"t", "delText"} and element.text:
            editable, reason = _simple_text_node(element)
            if tag == "delText":
                editable = False
                reason = "text is inside an existing tracked deletion"
            segments.append(
                _Segment(
                    text=element.text,
                    node=element,
                    root=root,
                    part_name=part_name,
                    kind=tag,
                    editable=editable,
                    reason=reason,
                )
            )
            return
        if tag == "tab":
            segments.append(
                _Segment("\t", element, root, part_name, "tab", False, "tab marker")
            )
            return
        if tag in {"br", "cr"}:
            segments.append(
                _Segment("\n", element, root, part_name, tag, False, "line break")
            )
            return
        if tag in {"footnoteReference", "endnoteReference"}:
            note_id = str(element.attrib.get(f"{W}id", ""))
            number = note_numbers.get(note_id, note_id)
            segments.append(
                _Segment(
                    f"[{number}]",
                    element,
                    root,
                    part_name,
                    tag,
                    False,
                    "note reference marker",
                )
            )
            return
        for child in element:
            walk(child)

    walk(paragraph)
    return segments


def _segment_text(segments: Sequence[_Segment]) -> str:
    return "".join(segment.text for segment in segments)


def _synthetic(
    text: str, *, part_name: str, root: etree._Element, kind: str
) -> _Segment:
    return _Segment(text, None, root, part_name, kind, False, "structural separator")


def _note_specs(
    roots: Mapping[str, etree._Element],
) -> tuple[list[tuple[str, list[_Segment]]], dict[str, str], dict[str, str]]:
    specs: list[tuple[str, list[_Segment]]] = []
    footnote_numbers: dict[str, str] = {}
    endnote_numbers: dict[str, str] = {}
    for kind, part_name, element_name, number_map in (
        ("footnote", "word/footnotes.xml", "footnote", footnote_numbers),
        ("endnote", "word/endnotes.xml", "endnote", endnote_numbers),
    ):
        root = roots.get(part_name)
        if root is None:
            continue
        visible = [
            node
            for node in root.findall(f"w:{element_name}", NS)
            if int(node.attrib.get(f"{W}id", "-1")) > 0
        ]
        for note_order, node in enumerate(visible):
            note_id = str(node.attrib.get(f"{W}id", ""))
            number_map[note_id] = str(note_order + 1)
            for paragraph in node.findall("w:p", NS):
                segments = _paragraph_segments(
                    paragraph,
                    part_name=part_name,
                    root=root,
                    note_numbers={},
                )
                if _segment_text(segments).strip():
                    specs.append((part_name, segments))
    return specs, footnote_numbers, endnote_numbers


def _build_index(package: _Package) -> _IndexedPackage:
    required = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
    missing = sorted(required - package.parts.keys())
    if missing:
        raise DocxValidationError(f"DOCX is missing required package part: {missing[0]}")

    roots: dict[str, etree._Element] = {}
    for name, data in package.parts.items():
        if name.endswith(".xml") or name.endswith(".rels"):
            roots[name] = _parse_xml(data, name)

    note_specs, footnote_numbers, endnote_numbers = _note_specs(roots)
    document_root = roots["word/document.xml"]
    body = document_root.find("w:body", NS)
    specs: list[tuple[str, list[_Segment]]] = []
    if body is not None:
        for child in body:
            tag = _local_name(child)
            if tag == "p":
                segments = _paragraph_segments(
                    child,
                    part_name="word/document.xml",
                    root=document_root,
                    note_numbers=footnote_numbers | endnote_numbers,
                )
                if _segment_text(segments):
                    specs.append(("word/document.xml", segments))
            elif tag == "tbl":
                table_segments: list[_Segment] = []
                rows = child.findall("w:tr", NS)
                for row_index, row in enumerate(rows):
                    if row_index:
                        table_segments.append(
                            _synthetic(
                                "\n",
                                part_name="word/document.xml",
                                root=document_root,
                                kind="table_row_separator",
                            )
                        )
                    cells = row.findall("w:tc", NS)
                    for cell_index, cell in enumerate(cells):
                        if cell_index:
                            table_segments.append(
                                _synthetic(
                                    "\t",
                                    part_name="word/document.xml",
                                    root=document_root,
                                    kind="table_cell_separator",
                                )
                            )
                        paragraphs = cell.findall("w:p", NS)
                        for paragraph_index, paragraph in enumerate(paragraphs):
                            if paragraph_index:
                                table_segments.append(
                                    _synthetic(
                                        "\n",
                                        part_name="word/document.xml",
                                        root=document_root,
                                        kind="cell_paragraph_separator",
                                    )
                                )
                            table_segments.extend(
                                _paragraph_segments(
                                    paragraph,
                                    part_name="word/document.xml",
                                    root=document_root,
                                    note_numbers={},
                                )
                            )
                specs.append(("word/document.xml", table_segments))
    specs.extend(note_specs)

    text_parts: list[str] = []
    locations: list[_InternalLocation] = []
    offset = 0
    for spec_index, (part_name, segments) in enumerate(specs):
        if spec_index:
            separator_root = roots[part_name]
            text_parts.append("\n\n")
            public = DocxTextLocation(
                part_name=part_name,
                start=offset,
                end=offset + 2,
                text="\n\n",
                node_kind="block_separator",
                node_path=None,
                editable=False,
                reason="structural separator",
            )
            locations.append(_InternalLocation(public, None, separator_root))
            offset += 2
        for segment in segments:
            start = offset
            end = start + len(segment.text)
            path = (
                segment.root.getroottree().getpath(segment.node)
                if segment.node is not None
                else None
            )
            public = DocxTextLocation(
                part_name=segment.part_name,
                start=start,
                end=end,
                text=segment.text,
                node_kind=segment.kind,
                node_path=path,
                editable=segment.editable,
                reason=segment.reason,
            )
            locations.append(_InternalLocation(public, segment.node, segment.root))
            text_parts.append(segment.text)
            offset = end
    return _IndexedPackage(package, roots, "".join(text_parts), locations)


def index_docx_text(payload: bytes) -> DocxTextIndex:
    indexed = _build_index(_read_package(payload))
    return DocxTextIndex(
        text=indexed.text,
        locations=tuple(location.public for location in indexed.locations),
    )


def _overlapping_locations(
    locations: Sequence[_InternalLocation], start: int, end: int
) -> list[_InternalLocation]:
    return [
        location
        for location in locations
        if location.public.end > start and location.public.start < end
    ]


def _map_single_text_node(
    indexed: _IndexedPackage,
    *,
    start: int,
    end: int,
    expected: str,
    purpose: str,
) -> tuple[_InternalLocation, int, int]:
    if start < 0 or end <= start or end > len(indexed.text):
        raise DocxMappingError(f"{purpose} has an invalid source range")
    actual = indexed.text[start:end]
    if actual != expected:
        raise DocxMappingError(
            f"{purpose} source text no longer matches the original document"
        )
    overlaps = _overlapping_locations(indexed.locations, start, end)
    if len(overlaps) != 1:
        raise DocxMappingError(
            f"{purpose} cannot be mapped unambiguously to one Word text node"
        )
    location = overlaps[0]
    if (
        location.node is None
        or not location.public.editable
        or location.public.node_kind != "t"
    ):
        raise DocxMappingError(
            f"{purpose} cannot be mapped unambiguously to editable Word text"
        )
    local_start = start - location.public.start
    local_end = end - location.public.start
    if local_start < 0 or local_end > len(location.public.text):
        raise DocxMappingError(f"{purpose} exceeds its mapped Word text node")
    return location, local_start, local_end
