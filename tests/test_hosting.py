import asyncio

import pytest

from autocite_mcp.hosting import _MAX_REQUEST_BODY_BYTES, BearerGate, resolve_bind_host


async def _invoke(
    app,
    path: str,
    authorization: str | None = None,
    *,
    content_length: int | None = None,
    body_chunks: list[bytes] | None = None,
):
    messages = []
    headers = []
    if authorization:
        headers.append((b"authorization", authorization.encode("latin-1")))
    if content_length is not None:
        headers.append((b"content-length", str(content_length).encode("ascii")))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 1234),
        "server": ("example.com", 443),
    }

    chunks = list(body_chunks) if body_chunks is not None else [b""]

    async def receive():
        chunk = chunks.pop(0) if chunks else b""
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": bool(chunks),
        }

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    return messages


def test_bearer_gate_protects_mcp_and_adds_no_store():
    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    gate = BearerGate(inner, token="secret")
    denied = asyncio.run(_invoke(gate, "/mcp"))
    assert denied[0]["status"] == 401

    allowed = asyncio.run(_invoke(gate, "/mcp", "Bearer secret"))
    assert allowed[0]["status"] == 204
    headers = dict(allowed[0]["headers"])
    assert headers[b"cache-control"] == b"no-store"


def test_bearer_gate_rejects_oversized_declared_content_length_before_buffering():
    called = False

    async def inner(scope, receive, send):
        nonlocal called
        called = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    gate = BearerGate(inner, token=None)
    result = asyncio.run(
        _invoke(
            gate,
            "/app/import",
            content_length=_MAX_REQUEST_BODY_BYTES + 1,
        )
    )
    assert result[0]["status"] == 413
    assert called is False


def test_bearer_gate_rejects_stream_that_exceeds_cap_without_declared_length():
    async def inner(scope, receive, send):
        while True:
            message = await receive()
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    gate = BearerGate(inner, token=None)
    chunk = b"a" * (1024 * 1024)
    chunk_count = _MAX_REQUEST_BODY_BYTES // len(chunk) + 2
    result = asyncio.run(
        _invoke(
            gate,
            "/app/import",
            body_chunks=[chunk] * chunk_count,
        )
    )
    assert result[0]["status"] == 413


def test_bearer_gate_allows_body_under_the_cap():
    async def inner(scope, receive, send):
        while True:
            message = await receive()
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    gate = BearerGate(inner, token=None)
    result = asyncio.run(
        _invoke(
            gate,
            "/app/import",
            content_length=1024,
            body_chunks=[b"x" * 1024],
        )
    )
    assert result[0]["status"] == 200


def test_bearer_gate_leaves_health_public():
    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    gate = BearerGate(inner, token="secret")
    result = asyncio.run(_invoke(gate, "/health"))
    assert result[0]["status"] == 200


def test_resolve_bind_host_allows_loopback_without_opt_in():
    assert resolve_bind_host("127.0.0.1", allow_remote="", api_token=None) == "127.0.0.1"
    assert resolve_bind_host("localhost", allow_remote="", api_token=None) == "localhost"


def test_resolve_bind_host_rejects_public_host_without_opt_in():
    with pytest.raises(ValueError, match="AUTOCITE_ALLOW_REMOTE"):
        resolve_bind_host("0.0.0.0", allow_remote="", api_token="secret")


def test_resolve_bind_host_rejects_unauthenticated_public_bind():
    with pytest.raises(ValueError, match="AUTOCITE_API_TOKEN"):
        resolve_bind_host("0.0.0.0", allow_remote="1", api_token="")


def test_resolve_bind_host_allows_container_deployment_with_token():
    assert resolve_bind_host("0.0.0.0", allow_remote="1", api_token="secret") == "0.0.0.0"
