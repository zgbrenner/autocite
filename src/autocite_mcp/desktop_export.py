from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .docx_preservation import apply_docx_export_plan
from .review_session import ReviewDecision, ReviewSession


FallbackDocxBuilder = Callable[[str, str, bool], bytes]


@dataclass(frozen=True, slots=True)
class DesktopDocxExport:
    payload: bytes
    metadata: dict[str, Any]


def _input_document(result: Mapping[str, Any]) -> Mapping[str, Any]:
    value = result.get("input_document")
    return value if isinstance(value, Mapping) else {}


def _source_format(result: Mapping[str, Any]) -> str:
    return str(_input_document(result).get("source_format") or "text").casefold()


def _verify_review_fingerprint(result: Mapping[str, Any], source_bytes: bytes) -> None:
    expected = _input_document(result).get("sha256")
    if expected is None:
        raise ValueError(
            "The original DOCX fingerprint is missing; preservation export cannot verify the source."
        )
    actual = hashlib.sha256(source_bytes).hexdigest()
    if actual != str(expected):
        raise ValueError(
            "The original DOCX changed after review. Review the current file again before exporting."
        )


def build_desktop_docx_export(
    *,
    result: Mapping[str, Any],
    source_bytes: bytes | None,
    fallback_builder: FallbackDocxBuilder,
    tracked: bool = True,
    decisions: Mapping[str, ReviewDecision | str] | None = None,
) -> DesktopDocxExport:
    """Build the safest available desktop DOCX export for one completed review.

    A DOCX source is edited in place on a copy of its original OPC package. Text,
    Markdown, and PDF sources use the existing reconstruction exporter because
    they do not have a Word package whose structure can be preserved.
    """

    original_text = str(result.get("original_text") or "")
    corrected_text = str(result.get("corrected_text") or original_text)
    session = ReviewSession.from_result(result)
    if decisions:
        session = session.with_decisions(decisions)
    plan = session.export_plan()

    if _source_format(result) == "docx":
        if source_bytes is None:
            raise ValueError(
                "The original DOCX bytes are required for preservation export."
            )
        _verify_review_fingerprint(result, source_bytes)
        preserved = apply_docx_export_plan(source_bytes, plan, tracked=tracked)
        payload = preserved.payload
        metadata: dict[str, Any] = {
            **preserved.as_dict(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "applied_edit_count": len(preserved.applied_edit_ids),
            "anchored_annotation_count": len(preserved.anchored_annotation_ids),
            "unanchored_annotation_count": len(
                preserved.unanchored_annotations
            ),
            "tracked_changes": tracked,
            "review_session": session.as_dict(),
        }
        return DesktopDocxExport(payload=payload, metadata=metadata)

    payload = fallback_builder(original_text, corrected_text, tracked)
    if not isinstance(payload, bytes) or not payload:
        raise ValueError("The reconstructed DOCX exporter returned no document data.")
    return DesktopDocxExport(
        payload=payload,
        metadata={
            "preservation_mode": "reconstructed_text",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "applied_edit_count": len(plan.text_edits),
            "anchored_annotation_count": 0,
            "unanchored_annotation_count": len(plan.annotations),
            "tracked_changes": tracked,
            "review_session": session.as_dict(),
            "limitations": [
                "The source was not a DOCX package, so the export preserves reviewed text and tracked changes rather than an original Word layout."
            ],
        },
    )
