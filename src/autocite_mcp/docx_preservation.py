from __future__ import annotations

from ._docx_preservation_index import (
    _build_index,
    _map_single_text_node,
    index_docx_text,
)
from ._docx_preservation_model import (
    W,
    DocxMappingError,
    DocxPreservationError,
    DocxTextIndex,
    DocxTextLocation,
    DocxValidationError,
    DocxValidationReport,
    PreservedDocxResult,
    _IndexedPackage,
    _InternalLocation,
)
from ._docx_preservation_mutation import (
    _anchor_comment,
    _append_comment,
    _ensure_comments_support,
    _max_numeric_attribute,
    _replace_run_with_edits,
)
from ._docx_preservation_package import (
    _read_package,
    _validate_parts,
    _write_package,
    validate_docx_package,
)
from .review_session import ExportPlan, PlannedAnnotation, PlannedTextEdit

__all__ = [
    "DocxMappingError",
    "DocxPreservationError",
    "DocxTextIndex",
    "DocxTextLocation",
    "DocxValidationError",
    "DocxValidationReport",
    "PreservedDocxResult",
    "apply_docx_export_plan",
    "index_docx_text",
    "validate_docx_package",
]


def apply_docx_export_plan(
    payload: bytes,
    plan: ExportPlan,
    *,
    tracked: bool = True,
) -> PreservedDocxResult:
    package = _read_package(payload)
    _validate_parts(package, raise_on_error=True)
    indexed = _build_index(package)

    edit_mappings: list[
        tuple[PlannedTextEdit, _InternalLocation, int, int]
    ] = []
    edit_nodes: set[int] = set()
    for edit in sorted(plan.text_edits, key=lambda item: (item.start, item.end)):
        location, local_start, local_end = _map_single_text_node(
            indexed,
            start=edit.start,
            end=edit.end,
            expected=edit.original,
            purpose=f"accepted edit {edit.item_id}",
        )
        if location.node is None:
            raise DocxMappingError(
                f"accepted edit {edit.item_id} cannot be mapped unambiguously"
            )
        edit_mappings.append((edit, location, local_start, local_end))
        edit_nodes.add(id(location.node))

    annotation_mappings: list[
        tuple[PlannedAnnotation, _InternalLocation, int, int]
    ] = []
    unanchored: list[PlannedAnnotation] = []
    used_annotation_nodes: set[int] = set()
    for annotation in plan.annotations:
        try:
            location, local_start, local_end = _map_single_text_node(
                indexed,
                start=annotation.start,
                end=annotation.end,
                expected=annotation.original,
                purpose=f"annotation {annotation.item_id}",
            )
        except DocxMappingError:
            unanchored.append(annotation)
            continue
        node_id = id(location.node)
        if (
            location.public.part_name != "word/document.xml"
            or node_id in edit_nodes
            or node_id in used_annotation_nodes
        ):
            unanchored.append(annotation)
            continue
        used_annotation_nodes.add(node_id)
        annotation_mappings.append(
            (annotation, location, local_start, local_end)
        )

    modified_parts: set[str] = set()
    grouped_edits: dict[int, list[tuple[PlannedTextEdit, int, int]]] = {}
    edit_locations: dict[int, _InternalLocation] = {}
    for edit, location, local_start, local_end in edit_mappings:
        node_key = id(location.node)
        grouped_edits.setdefault(node_key, []).append((edit, local_start, local_end))
        edit_locations[node_key] = location

    next_revision_id = _max_numeric_attribute(
        indexed.roots.values(), f"{W}id"
    ) + 1
    for node_key, edits in grouped_edits.items():
        location = edit_locations[node_key]
        next_revision_id = _replace_run_with_edits(
            location,
            edits,
            tracked=tracked,
            next_revision_id=next_revision_id,
        )
        modified_parts.add(location.public.part_name)

    anchored_ids: list[str] = []
    if annotation_mappings:
        comments_root, next_comment_id, support_modified = _ensure_comments_support(
            indexed
        )
        modified_parts.update(support_modified)
        for annotation, location, local_start, local_end in annotation_mappings:
            _anchor_comment(
                location,
                local_start=local_start,
                local_end=local_end,
                comment_id=next_comment_id,
            )
            _append_comment(
                comments_root,
                annotation,
                comment_id=next_comment_id,
            )
            next_comment_id += 1
            anchored_ids.append(annotation.item_id)
            modified_parts.add(location.public.part_name)
            modified_parts.add("word/comments.xml")

    output = _write_package(indexed, modified_parts)
    validation = validate_docx_package(output, raise_on_error=True)
    return PreservedDocxResult(
        payload=output,
        applied_edit_ids=tuple(edit.item_id for edit, _, _, _ in edit_mappings),
        anchored_annotation_ids=tuple(anchored_ids),
        unanchored_annotations=tuple(unanchored),
        modified_parts=tuple(sorted(modified_parts)),
        validation=validation,
    )
