from __future__ import annotations

import hashlib
import io

import pytest
from docx import Document

from autocite_mcp.desktop_export import build_desktop_docx_export


def _docx_bytes() -> bytes:
    document = Document()
    document.add_paragraph("See 42 USC §1983.")
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()


def _result(payload: bytes, *, source_format: str = "docx") -> dict:
    return {
        "original_text": "See 42 USC §1983.",
        "corrected_text": "See 42 U.S.C. § 1983.",
        "applied_edits": [
            {
                "code": "STATUTE_CODE_ABBREVIATION",
                "start": 7,
                "end": 10,
                "original": "USC",
                "suggestion": "U.S.C.",
                "correction_level": "safe_auto_fix",
                "confidence": "high",
                "severity": "error",
                "provenance": "deterministic_logic",
            },
            {
                "code": "SECTION_SYMBOL_SPACING",
                "start": 11,
                "end": 12,
                "original": "§",
                "suggestion": "§ ",
                "correction_level": "safe_auto_fix",
                "confidence": "high",
                "severity": "error",
                "provenance": "deterministic_logic",
            },
        ],
        "remaining_issues": [],
        "rule_findings": [],
        "input_document": {
            "source_format": source_format,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "filename": "brief.docx",
        },
    }


def test_original_docx_export_uses_preservation_pipeline_and_not_fallback():
    source = _docx_bytes()

    def forbidden_fallback(original: str, corrected: str, tracked: bool) -> bytes:
        raise AssertionError("fallback must not run for a valid original DOCX")

    export = build_desktop_docx_export(
        result=_result(source),
        source_bytes=source,
        fallback_builder=forbidden_fallback,
    )

    assert export.metadata["preservation_mode"] == "original_docx"
    assert export.metadata["applied_edit_count"] == 2
    assert export.metadata["unanchored_annotation_count"] == 0
    assert export.metadata["sha256"] == hashlib.sha256(export.payload).hexdigest()
    assert export.payload != source


def test_non_docx_export_uses_clearly_labeled_reconstruction_fallback():
    source = b"See 42 USC section 1983."
    calls: list[tuple[str, str, bool]] = []

    def fallback(original: str, corrected: str, tracked: bool) -> bytes:
        calls.append((original, corrected, tracked))
        return b"fallback-docx"

    result = _result(source, source_format="text")
    export = build_desktop_docx_export(
        result=result,
        source_bytes=source,
        fallback_builder=fallback,
    )

    assert calls == [(result["original_text"], result["corrected_text"], True)]
    assert export.payload == b"fallback-docx"
    assert export.metadata["preservation_mode"] == "reconstructed_text"


def test_docx_export_refuses_source_bytes_that_do_not_match_review_fingerprint():
    source = _docx_bytes()
    changed = source + b"changed"

    with pytest.raises(ValueError, match="changed after review"):
        build_desktop_docx_export(
            result=_result(source),
            source_bytes=changed,
            fallback_builder=lambda *_: b"fallback",
        )


def test_decision_overrides_can_reject_an_automatic_edit():
    source = _docx_bytes()
    baseline = build_desktop_docx_export(
        result=_result(source),
        source_bytes=source,
        fallback_builder=lambda *_: b"fallback",
    )
    first_id = baseline.metadata["review_session"]["items"][0]["item_id"]

    export = build_desktop_docx_export(
        result=_result(source),
        source_bytes=source,
        fallback_builder=lambda *_: b"fallback",
        decisions={first_id: "rejected"},
    )

    assert export.metadata["applied_edit_count"] == 1
    assert any(
        item["item_id"] == first_id and item["decision"] == "rejected"
        for item in export.metadata["review_session"]["items"]
    )
