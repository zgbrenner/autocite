from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from autocite_mcp.application_http import configure_application_service
from autocite_mcp.application_service import AutoCiteApplicationService
from autocite_mcp.application_sessions import DocumentSessionStore
from autocite_mcp.hosting import build_http_app
from autocite_mcp.server import mcp


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
    }


def _service(tmp_path: Path) -> AutoCiteApplicationService:
    return AutoCiteApplicationService(
        DocumentSessionStore(tmp_path / "sessions.sqlite3"),
        reviewer=_fake_reviewer,
    )


def test_application_routes_cover_document_review_and_export(tmp_path: Path) -> None:
    configure_application_service(_service(tmp_path))
    with TestClient(mcp.streamable_http_app()) as client:
        health = client.get("/app/health")
        assert health.status_code == 200
        assert health.json()["schema_version"] == "1.0"

        created = client.post(
            "/app/documents",
            json={
                "title": "Brief",
                "text": "See 42 USC § 1983.",
                "source_format": "markdown",
                "mode": "bluepages",
            },
        )
        assert created.status_code == 201
        document = created.json()["document"]
        session_id = document["session_id"]
        assert document["revision"] == 1

        reviewed = client.post(f"/app/documents/{session_id}/review", json={})
        assert reviewed.status_code == 200
        assert reviewed.json()["job"]["status"] == "completed"

        review = client.get(f"/app/documents/{session_id}/review")
        item = review.json()["items"][0]
        assert item["decision"] == "accepted"

        decision = client.post(
            f"/app/documents/{session_id}/decisions",
            json={
                "item_id": item["item_id"],
                "decision": "rejected",
                "expected_revision": 1,
            },
        )
        assert decision.status_code == 200
        assert decision.json()["item"]["decision"] == "rejected"

        exported = client.post(
            f"/app/documents/{session_id}/export",
            json={"format": "txt"},
        )
        assert exported.status_code == 200
        assert base64.b64decode(exported.json()["data_base64"]).decode() == (
            "See 42 USC § 1983."
        )

        conflict = client.patch(
            f"/app/documents/{session_id}",
            json={"text": "stale", "expected_revision": 99},
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"] == "revision_conflict"


def test_bearer_gate_protects_application_document_routes(tmp_path: Path) -> None:
    configure_application_service(_service(tmp_path))
    with TestClient(build_http_app(api_token="secret")) as client:
        assert client.get("/health").status_code == 200
        unauthorized = client.get("/app/documents")
        assert unauthorized.status_code == 401
        authorized = client.get(
            "/app/documents",
            headers={"Authorization": "Bearer secret"},
        )
        assert authorized.status_code == 200
