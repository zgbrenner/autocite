from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from autocite_mcp.application_http import configure_application_service
from autocite_mcp.application_service import AutoCiteApplicationService
from autocite_mcp.application_sessions import DocumentSessionStore
from autocite_mcp.hosting import build_http_app


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
    # No `with` block: these routes don't depend on ASGI lifespan startup, and
    # entering the lifespan here would start the shared FastMCP session
    # manager, which only tolerates a single start per process — reserve that
    # for test_mcp_endpoint_initializes_without_lifespan_error below.
    client = TestClient(build_http_app())
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


def test_mcp_endpoint_initializes_without_lifespan_error(tmp_path: Path) -> None:
    configure_application_service(_service(tmp_path))
    # build_application_http_app mounts the FastMCP streamable-HTTP app under
    # a plain Mount, which does not forward the outer app's lifespan scope by
    # itself; without explicitly forwarding mcp_app's lifespan_context, every
    # /mcp request fails with "Task group is not initialized" because the
    # StreamableHTTPSessionManager's task group is never started. The Host
    # header must match FastMCP's default DNS-rebinding allow-list
    # (127.0.0.1:* / localhost:* / [::1]:*), which requires an explicit port.
    with TestClient(build_http_app(), base_url="http://127.0.0.1:8000") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0.0"},
                },
            },
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result"]["serverInfo"]["name"] == "AutoCite"


def test_bearer_gate_protects_application_document_routes(tmp_path: Path) -> None:
    configure_application_service(_service(tmp_path))
    # No `with` block — see test_application_routes_cover_document_review_and_export.
    client = TestClient(build_http_app(api_token="secret"))
    assert client.get("/health").status_code == 200
    unauthorized = client.get("/app/documents")
    assert unauthorized.status_code == 401
    authorized = client.get(
        "/app/documents",
        headers={"Authorization": "Bearer secret"},
    )
    assert authorized.status_code == 200
