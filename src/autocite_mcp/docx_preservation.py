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
    unanchored_annotations: list[dict[str, object]] = []
    for annotation in plan.annotations:
        try:
            location, local_start, local_end = _map_single_text_node(
                indexed,
                start=annotation.start,
                end=annotation.end,
                expected=annotation.original,
                purpose=f"review annotation {annotation.item_id}",
            )
        except DocxMappingError as exc:
            unanchored_annotations.append(
                {
                    **annotation.as_dict(),
                    "reason": str(exc),
                }
            )
            continue
        if location.node is None or id(location.node) in edit_nodes:
            unanchored_annotations.append(
                {
                    **annotation.as_dict(),
                    "reason": (
                        "Annotation shares text with an accepted edit or cannot "
                        "be anchored to a single safe Word text node."
                    ),
                }
            )
            continue
        annotation_mappings.append(
            (annotation, location, local_start, local_end)
        )

    annotation_ids: dict[str, int] = {}
    comment_id = _max_numeric_attribute(
        package,
        W + "id",
    )
    if annotation_mappings:
        comments_root, comments_part = _ensure_comments_support(package)
        for annotation, _location, _start, _end in annotation_mappings:
            comment_id += 1
            annotation_ids[annotation.item_id] = comment_id
            _append_comment(
                comments_root,
                annotation,
                comment_id=comment_id,
            )
        package.parts["word/comments.xml"] = comments_part

    for annotation, location, local_start, local_end in sorted(
        annotation_mappings,
        key=lambda item: (item[1].part_name, item[1].order, item[2]),
        reverse=True,
    ):
        _anchor_comment(
            location,
            local_start,
            local_end,
            comment_id=annotation_ids[annotation.item_id],
        )

    revision_id = _max_numeric_attribute(package, W + "id")
    applied_edit_ids: list[str] = []
    for edit, location, local_start, local_end in sorted(
        edit_mappings,
        key=lambda item: (item[1].part_name, item[1].order, item[2]),
        reverse=True,
    ):
        revision_id += 1
        _replace_run_with_edits(
            location,
            local_start,
            local_end,
            edit,
            tracked=tracked,
            revision_id=revision_id,
        )
        applied_edit_ids.append(edit.item_id)

    output = _write_package(package)
    validation = validate_docx_package(output)
    if not validation.valid:
        raise DocxValidationError(
            "Generated DOCX did not pass package validation: "
            + "; ".join(validation.errors)
        )
    return PreservedDocxResult(
        payload=output,
        applied_edit_ids=tuple(sorted(applied_edit_ids)),
        anchored_annotation_ids=tuple(sorted(annotation_ids)),
        unanchored_annotations=tuple(unanchored_annotations),
        validation=validation,
    )
