from __future__ import annotations

import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from autocite_mcp.application.engine_adapter import CallableReviewEngine
from autocite_mcp.application.http_api import AutoCiteApplicationServer
from autocite_mcp.application.service import ApplicationService
from autocite_mcp.application.store import SessionStore


async def _review(_: str, **__: object) -> dict[str, object]:
    return {"issues": []}


@pytest.fixture
def application_server(tmp_path):
    service = ApplicationService(
        store=SessionStore(tmp_path / "api.sqlite3"),
        engine=CallableReviewEngine(_review),
    )
    server = AutoCiteApplicationServer(("127.0.0.1", 0), service=service, token="test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, object] | None = None,
    token: str | None = "test-token",
) -> tuple[int, dict[str, object]]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_health_is_public_but_session_routes_require_token(application_server) -> None:
    status, health = _request(f"{application_server}/health", token=None)
    assert status == 200
    assert health["status"] == "ok"

    status, payload = _request(f"{application_server}/sessions", token=None)
    assert status == 401
    assert payload["error"] == "unauthorized"


def test_create_autosave_and_revision_conflict(application_server) -> None:
    status, created = _request(
        f"{application_server}/sessions",
        method="POST",
        body={"title": "Brief", "text": "See 1 U.S. 1.", "source_format": "md"},
    )
    assert status == 201
    session = created["session"]

    status, updated = _request(
        f"{application_server}/sessions/{session['id']}",
        method="PATCH",
        body={"expected_revision": 1, "text": "See 1 U.S. 1, 2."},
    )
    assert status == 200
    assert updated["session"]["revision"] == 2

    status, conflict = _request(
        f"{application_server}/sessions/{session['id']}",
        method="PATCH",
        body={"expected_revision": 1, "text": "stale"},
    )
    assert status == 409
    assert conflict["error"] == "revision_conflict"
    assert conflict["current_revision"] == 2
