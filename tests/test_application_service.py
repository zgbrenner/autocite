from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest

from autocite_mcp.application_service import AutoCiteApplicationService
from autocite_mcp.application_sessions import DocumentSessionStore


async def _fake_reviewer(text: str, **_: Any) -> dict[str, Any]:
    original = "42 USC"
    start = text.index(original)
    return {
        "schema_version": "1.0",
        "workflow": "complete_citecheck",
        "mode": "bluepages",
        "original_text": text,
        "corrected_text": text.replace(original, "42 U.S.C."),
        "applied_edits": [
            {
                "issue_code": "STATUTE_ABBREVIATION",
                "start": start,
                "end": start + len(original),
                "original": original,
                "suggestion": "42 U.S.C.",
                "confidence": "high",
                "correction_level": "safe_auto_fix",
                "provenance": "deterministic_logic",
            }
        ],
        "remaining_issues": [],
        "rule_findings": [],
        "citation_inventory": [],
        "final_summary": {"citation_count": 1, "issue_count": 0},
    }


def _fake_docx_exporter(
    original_text: str,
    corrected_text: str,
    *,
    tracked: bool,
    filename: str,
) -> dict[str, Any]:
    payload = b"PK\x03\x04" + corrected_text.encode("utf-8")
    return {
        "filename": filename,
        "mime_type": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        "data_base64": base64.b64encode(payload).decode("ascii"),
        "size_bytes": len(payload),
        "tracked_changes": tracked,
    }


@pytest.mark.asyncio
async def test_service_reviews_persists_decisions_and_exports_current_state(
    tmp_path: Path,
) -> None:
    store = DocumentSessionStore(tmp_path / "sessions.sqlite3")
    service = AutoCiteApplicationService(
        store,
        reviewer=_fake_reviewer,
        docx_exporter=_fake_docx_exporter,
    )
    created = service.create_document(
        title="Brief",
        text="See 42 USC § 1983.",
        source_format="markdown",
        mode="bluepages",
    )

    completed = await service.review_document(created.session_id)

    assert completed["job"]["status"] == "completed"
    assert completed["document"]["review_revision"] == 1
    review_page = service.get_review_items(created.session_id, limit=20)
    assert review_page["total"] == 1
    item = review_page["items"][0]
    assert item["decision"] == "accepted"
    assert service.get_effective_text(created.session_id) == "See 42 U.S.C. § 1983."

    rejected = service.set_review_item_decision(
        created.session_id,
        item_id=item["item_id"],
        decision="rejected",
        expected_revision=1,
    )
    assert rejected["decision"] == "rejected"
    assert service.get_effective_text(created.session_id) == "See 42 USC § 1983."

    text_export = service.export_document(created.session_id, export_format="txt")
    assert base64.b64decode(text_export["data_base64"]).decode("utf-8") == (
        "See 42 USC § 1983."
    )

    docx_export = service.export_document(created.session_id, export_format="docx")
    assert base64.b64decode(docx_export["data_base64"]).startswith(b"PK\x03\x04")


@pytest.mark.asyncio
async def test_editing_document_invalidates_stale_review(tmp_path: Path) -> None:
    store = DocumentSessionStore(tmp_path / "sessions.sqlite3")
    service = AutoCiteApplicationService(store, reviewer=_fake_reviewer)
    created = service.create_document(
        title="Brief",
        text="See 42 USC § 1983.",
        source_format="text",
    )
    await service.review_document(created.session_id)

    updated = service.update_document(
        created.session_id,
        text="See 28 USC § 1331.",
        expected_revision=1,
    )

    assert updated.review_result is None
    assert updated.review_revision is None
    assert service.get_review_items(created.session_id)["total"] == 0


@pytest.mark.asyncio
async def test_review_job_records_failure_without_destroying_document(
    tmp_path: Path,
) -> None:
    async def broken_reviewer(text: str, **_: Any) -> dict[str, Any]:
        raise RuntimeError("model unavailable")

    store = DocumentSessionStore(tmp_path / "sessions.sqlite3")
    service = AutoCiteApplicationService(store, reviewer=broken_reviewer)
    created = service.create_document(
        title="Brief",
        text="See 42 USC § 1983.",
        source_format="text",
    )

    with pytest.raises(RuntimeError, match="model unavailable"):
        await service.review_document(created.session_id)

    jobs = store.list_review_jobs(created.session_id)
    assert jobs[0].status == "failed"
    assert "model unavailable" in (jobs[0].error or "")
    assert store.get_document(created.session_id).text == "See 42 USC § 1983."
