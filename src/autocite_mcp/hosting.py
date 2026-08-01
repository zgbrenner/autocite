from __future__ import annotations

import json
import os
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from .application_http import build_application_http_app
from .documents import MAX_DOCUMENT_BYTES
from .server import mcp

ASGIApp = Callable[
    [
        dict[str, Any],
        Callable[[], Awaitable[dict[str, Any]]],
        Callable[[dict[str, Any]], Awaitable[None]],
    ],
    Awaitable[None],
]

# JSON request bodies carry document bytes base64-encoded (~4/3 expansion)
# plus a JSON envelope, so the ASGI-layer cap must clear that inflated size,
# not the raw document limit.
_MAX_REQUEST_BODY_BYTES = (MAX_DOCUMENT_BYTES * 4 // 3) + 65_536


class _RequestEntityTooLarge(Exception):
    """Raised by the size-capped receive callable once the cap is exceeded."""


async def _send_json(
    send,
    status: int,
    error: str,
    message: str,
    *,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    payload = json.dumps({"error": error, "message": message}).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"cache-control", b"no-store"),
        (b"content-length", str(len(payload)).encode("ascii")),
        *(extra_headers or []),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": payload})


def _size_capped_receive(
    receive: Callable[[], Awaitable[dict[str, Any]]], limit: int
) -> Callable[[], Awaitable[dict[str, Any]]]:
    received = 0

    async def capped_receive() -> dict[str, Any]:
        nonlocal received
        message = await receive()
        if message.get("type") == "http.request":
            received += len(message.get("body") or b"")
            if received > limit:
                raise _RequestEntityTooLarge()
        return message

    return capped_receive


class BearerGate:
    """Optional bearer gate and no-store wrapper for hosted local services."""

    def __init__(self, app: ASGIApp, token: str | None = None) -> None:
        self.app = app
        self.token = token or None

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }

        declared_length = headers.get("content-length")
        if declared_length is not None:
            try:
                declared_bytes = int(declared_length)
            except ValueError:
                declared_bytes = None
            if declared_bytes is not None and declared_bytes > _MAX_REQUEST_BODY_BYTES:
                await _send_json(
                    send,
                    413,
                    "request_too_large",
                    "The request body exceeds the maximum allowed size.",
                )
                return

        path = str(scope.get("path") or "")
        protected_path = (
            path == "/mcp"
            or path.startswith("/mcp/")
            or path == "/app"
            or path.startswith("/app/")
        )
        if self.token and protected_path:
            supplied = headers.get("authorization", "")
            expected = f"Bearer {self.token}"
            if not secrets.compare_digest(supplied, expected):
                await _send_json(
                    send,
                    401,
                    "unauthorized",
                    "A valid AutoCite bearer token is required.",
                    extra_headers=[(b"www-authenticate", b"Bearer")],
                )
                return

        async def send_no_store(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ]
                headers.append((b"cache-control", b"no-store"))
                message = {**message, "headers": headers}
            await send(message)

        capped_receive = _size_capped_receive(receive, _MAX_REQUEST_BODY_BYTES)
        try:
            await self.app(scope, capped_receive, send_no_store)
        except _RequestEntityTooLarge:
            await _send_json(
                send,
                413,
                "request_too_large",
                "The request body exceeds the maximum allowed size.",
            )


def build_http_app(api_token: str | None = None) -> BearerGate:
    """Build the hosted MCP and local application API surface."""
    token = (
        api_token
        if api_token is not None
        else os.getenv("AUTOCITE_API_TOKEN")
    )
    combined = build_application_http_app(mcp.streamable_http_app())
    return BearerGate(combined, token=token)


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_loopback_host(host: str) -> str:
    normalized = host.strip().lower()
    if normalized not in _LOOPBACK_HOSTS:
        raise ValueError(
            "AutoCite HTTP mode is local-only and must bind to a loopback host"
        )
    return host


def resolve_bind_host(
    host: str | None = None,
    *,
    allow_remote: str | None = None,
    api_token: str | None = None,
) -> str:
    """Resolve the HTTP bind host, defaulting to local-only.

    Binding beyond loopback requires both an explicit AUTOCITE_ALLOW_REMOTE opt-in
    and a configured AUTOCITE_API_TOKEN, so a hosted deployment can never start
    unauthenticated by accident.
    """
    resolved = (
        host
        if host is not None
        else os.getenv("AUTOCITE_HOST", "127.0.0.1")
    ).strip()
    if resolved.lower() in _LOOPBACK_HOSTS:
        return resolved
    opt_in = (
        allow_remote
        if allow_remote is not None
        else os.getenv("AUTOCITE_ALLOW_REMOTE", "")
    ).strip().lower()
    if opt_in not in {"1", "true", "yes"}:
        raise ValueError(
            "AutoCite binds to loopback by default. To serve a non-loopback "
            f"host such as {resolved!r}, set AUTOCITE_ALLOW_REMOTE=1 and "
            "configure AUTOCITE_API_TOKEN."
        )
    token = (
        api_token
        if api_token is not None
        else os.getenv("AUTOCITE_API_TOKEN")
    )
    if not token:
        raise ValueError(
            "Refusing to bind a non-loopback host without AUTOCITE_API_TOKEN. "
            "An unauthenticated public /mcp or /app endpoint would expose "
            "document review capabilities."
        )
    return resolved


def main() -> None:
    transport = os.getenv("AUTOCITE_TRANSPORT", "stdio").strip().lower()
    allowed = {"stdio", "sse", "streamable-http"}
    if transport not in allowed:
        raise ValueError(
            f"AUTOCITE_TRANSPORT must be one of {sorted(allowed)}"
        )
    if transport == "streamable-http":
        import uvicorn

        host = resolve_bind_host()
        port = int(
            os.getenv("PORT", os.getenv("AUTOCITE_PORT", "8000"))
        )
        uvicorn.run(build_http_app(), host=host, port=port)
        return
    if os.getenv("AUTOCITE_API_TOKEN"):
        raise ValueError(
            "AUTOCITE_API_TOKEN applies only to streamable-http. "
            "Use a private local client for stdio."
        )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
