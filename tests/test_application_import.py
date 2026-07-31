from __future__ import annotations

import base64
from pathlib import Path

from starlette.testclient import TestClient

from autocite_mcp.application_http import configure_application_service
from autocite_mcp.application_service import AutoCiteApplicationService
from autocite_mcp.application_sessions import DocumentSessionStore
from autocite_mcp.hosting import build_http_app


def test_import_route_loads_text_into_a_durable_session(tmp_path: Path) -> None:
    configure_application_service(
        AutoCiteApplicationService(
            DocumentSessionStore(tmp_path / "sessions.sqlite3")
        )
    )
    payload = base64.b64encode(b"See 42 U.S.C. \xc2\xa7 1983.").decode("ascii")

    with TestClient(build_http_app()) as client:
        response = client.post(
            "/app/import",
            json={
                "file_name": "brief.txt",
                "mime_type": "text/plain",
                "data_base64": payload,
                "mode": "bluepages",
            },
        )

        assert response.status_code == 201
        document = response.json()["document"]
        assert document["file_name"] == "brief.txt"
        assert document["source_format"] == "text"
        loaded = client.get(f"/app/documents/{document['session_id']}")
        assert loaded.json()["document"]["text"] == "See 42 U.S.C. § 1983."


def test_import_route_rejects_malformed_base64(tmp_path: Path) -> None:
    configure_application_service(
        AutoCiteApplicationService(
            DocumentSessionStore(tmp_path / "sessions.sqlite3")
        )
    )
    with TestClient(build_http_app()) as client:
        response = client.post(
            "/app/import",
            json={"file_name": "brief.txt", "data_base64": "not base64"},
        )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"
