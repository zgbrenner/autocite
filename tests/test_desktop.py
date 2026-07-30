from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document

from autocite_mcp.desktop import (
    DesktopReviewController,
    build_desktop_report,
    default_export_path,
    iter_desktop_issues,
    run_self_test,
    summarize_review,
)
from autocite_mcp.documents import MAX_DOCUMENT_BYTES


async def test_desktop_controller_uses_core_review_and_preserves_original(
    tmp_path: Path,
):
    source = tmp_path / "brief.txt"
    source.write_text("See 42 USC §1983.", encoding="utf-8")
    state = await DesktopReviewController().review_file(source, mode="bluepages")
    assert state.original_text == "See 42 USC §1983."
    assert state.corrected_text == "See 42 U.S.C. § 1983."
    assert source.read_text(encoding="utf-8") == state.original_text
    assert state.result is not None
    assert state.result["schema_version"] == "1.0"
    assert state.source_path == source


async def test_desktop_rejects_unknown_format_without_modifying_it(tmp_path: Path):
    source = tmp_path / "brief.bin"
    source.write_bytes(b"original")
    state = await DesktopReviewController().review_file(source)
    assert state.error_code == "unsupported_format"
    assert "TXT" in (state.error_message or "")
    assert source.read_bytes() == b"original"


async def test_desktop_returns_friendly_missing_file_state(tmp_path: Path):
    source = tmp_path / "missing.docx"
    state = await DesktopReviewController().review_file(source)
    assert state.error_code == "file_not_found"
    assert "could not be found" in (state.error_message or "").lower()
    assert state.source_path == source


async def test_desktop_rejects_oversized_file_before_reading_it(tmp_path: Path):
    source = tmp_path / "huge.txt"
    with source.open("wb") as stream:
        stream.seek(MAX_DOCUMENT_BYTES)
        stream.write(b"x")

    state = await DesktopReviewController().review_file(source)
    assert state.error_code == "document_too_large"
    assert str(MAX_DOCUMENT_BYTES // (1024 * 1024)) in (state.error_message or "")


async def test_desktop_export_is_caller_selected_and_atomic(tmp_path: Path):
    source = tmp_path / "brief.txt"
    source.write_text("See 42 USC §1983.", encoding="utf-8")
    state = await DesktopReviewController().review_file(source, mode="bluepages")
    destination = tmp_path / "review.docx"
    artifact = DesktopReviewController().export_docx(state, destination)
    assert destination.is_file()
    assert artifact["tracked_changes"] is True
    assert artifact["path"] == str(destination)
    assert not list(tmp_path.glob(".review.docx.*.tmp"))


async def test_desktop_never_overwrites_the_source_document(tmp_path: Path):
    source = tmp_path / "brief.docx"
    document = Document()
    document.add_paragraph("See 42 USC §1983.")
    document.save(source)
    original = source.read_bytes()

    state = await DesktopReviewController().review_file(source, mode="bluepages")
    with pytest.raises(ValueError, match="source document"):
        DesktopReviewController().export_docx(state, source)

    assert source.read_bytes() == original


async def test_desktop_exports_a_compact_json_audit_report(tmp_path: Path):
    source = tmp_path / "brief.txt"
    source.write_text("See 42 USC §1983.", encoding="utf-8")
    state = await DesktopReviewController().review_file(source, mode="bluepages")
    destination = tmp_path / "review.json"

    metadata = DesktopReviewController().export_json_report(state, destination)
    report = json.loads(destination.read_text(encoding="utf-8"))

    assert metadata["path"] == str(destination)
    assert report["product"] == "AutoCite Desktop"
    assert report["source"]["filename"] == source.name
    assert report["summary"]["applied_edits"] == 1
    assert "source_path" not in report["source"]


def test_default_export_path_is_clear_and_does_not_replace_source():
    source = Path("/work/Client Brief.docx")
    assert default_export_path(source) == Path(
        "/work/Client Brief - AutoCite Review.docx"
    )


def test_summary_and_issue_rows_are_stable_for_the_desktop_ui():
    result = {
        "mode": "bluepages",
        "mode_detection": {"confidence": "high"},
        "citation_inventory": [{"text": "A"}, {"text": "B"}],
        "applied_edits": [{"original": "USC", "replacement": "U.S.C."}],
        "remaining_issues": [
            {
                "code": "REPORTER_REVIEW",
                "severity": "warning",
                "message": "Review the reporter.",
                "start": 5,
                "end": 10,
                "confidence": "medium",
                "correction_level": "review_required",
                "provenance": "deterministic_logic",
            }
        ],
        "rule_findings": [
            {
                "issue_code": "UNSUPPORTED_LOCAL_RULE",
                "severity": "info",
                "explanation": "Check the current local rule.",
                "start": 20,
                "end": 25,
                "confidence": "high",
                "correction_level": "unsupported",
                "provenance": "deterministic_logic",
            }
        ],
        "mechanical_review_complete": False,
    }

    summary = summarize_review(result)
    issues = iter_desktop_issues(result)

    assert summary.mode == "bluepages"
    assert summary.citations == 2
    assert summary.applied_edits == 1
    assert summary.review_items == 1
    assert summary.unsupported_items == 1
    assert summary.remaining_mechanical_issues == 1
    assert [item["code"] for item in issues] == [
        "REPORTER_REVIEW",
        "UNSUPPORTED_LOCAL_RULE",
    ]
    assert issues[0]["message"] == "Review the reporter."


def test_desktop_report_contains_boundaries_and_no_full_local_path():
    source = Path("/private/client/brief.txt")
    result = {
        "mode": "whitepages",
        "mode_detection": {"confidence": "medium"},
        "citation_inventory": [],
        "applied_edits": [],
        "remaining_issues": [],
        "rule_findings": [],
        "mechanical_review_complete": True,
        "input_document": {
            "filename": "brief.txt",
            "sha256": "abc123",
            "source_format": "text",
            "warnings": [],
        },
    }
    state = DesktopReviewController.state_from_result(source, result)

    report = build_desktop_report(state)

    assert report["source"]["filename"] == "brief.txt"
    assert str(source.parent) not in json.dumps(report)
    assert report["accuracy_boundaries"]
    assert report["summary"]["mechanical_review_complete"] is True


async def test_packaged_self_test_exercises_review_and_export():
    result = await run_self_test()
    assert result["status"] == "ok"
    assert result["corrected_text"] == "See 42 U.S.C. § 1983."
    assert result["export_size_bytes"] > 0
