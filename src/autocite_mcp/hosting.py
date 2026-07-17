from __future__ import annotations

import json
import os
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from .server import mcp

ASGIApp = Callable[
    [dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]],
    Awaitable[None],
]


class BearerGate:
    """Optional bearer gate and no-store wrapper for self-hosted HTTP MCP."""

    def __init__(self, app: ASGIApp, token: str | None = None) -> None:
        self.app = app
        self.token = token or None

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        if self.token and (path == "/mcp" or path.startswith("/mcp/")):
            headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in scope.get("headers", [])
            }
            supplied = headers.get("authorization", "")
            expected = f"Bearer {self.token}"
            if not secrets.compare_digest(supplied, expected):
                payload = json.dumps(
                    {
                        "error": "unauthorized",
                        "message": "A valid AutoCite bearer token is required.",
                    }
                ).encode("utf-8")
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"cache-control", b"no-store"),
                            (b"www-authenticate", b"Bearer"),
                            (b"content-length", str(len(payload)).encode("ascii")),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": payload})
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

        await self.app(scope, receive, send_no_store)


def build_http_app(api_token: str | None = None) -> BearerGate:
    """Build the hosted MCP app with optional AUTOCITE_API_TOKEN protection."""
    token = api_token if api_token is not None else os.getenv("AUTOCITE_API_TOKEN")
    return BearerGate(mcp.streamable_http_app(), token=token)


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_loopback_host(host: str) -> str:
    normalized = host.strip().lower()
    if normalized not in _LOOPBACK_HOSTS:
        raise ValueError("AutoCite HTTP mode is local-only and must bind to a loopback host")
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
    resolved = (host if host is not None else os.getenv("AUTOCITE_HOST", "127.0.0.1")).strip()
    if resolved.lower() in _LOOPBACK_HOSTS:
        return resolved
    opt_in = (allow_remote if allow_remote is not None else os.getenv("AUTOCITE_ALLOW_REMOTE", "")).strip().lower()
    if opt_in not in {"1", "true", "yes"}:
        raise ValueError(
            "AutoCite binds to loopback by default. To serve a non-loopback host such as "
            f"{resolved!r}, set AUTOCITE_ALLOW_REMOTE=1 and configure AUTOCITE_API_TOKEN."
        )
    token = api_token if api_token is not None else os.getenv("AUTOCITE_API_TOKEN")
    if not token:
        raise ValueError(
            "Refusing to bind a non-loopback host without AUTOCITE_API_TOKEN. "
            "An unauthenticated public /mcp endpoint would expose the review tools to anyone."
        )
    return resolved


def main() -> None:
    transport = os.getenv("AUTOCITE_TRANSPORT", "stdio").strip().lower()
    allowed = {"stdio", "sse", "streamable-http"}
    if transport not in allowed:
        raise ValueError(f"AUTOCITE_TRANSPORT must be one of {sorted(allowed)}")
    if transport == "streamable-http":
        import uvicorn

        host = resolve_bind_host()
        port = int(os.getenv("PORT", os.getenv("AUTOCITE_PORT", "8000")))
        uvicorn.run(build_http_app(), host=host, port=port)
        return
    if os.getenv("AUTOCITE_API_TOKEN"):
        raise ValueError(
            "AUTOCITE_API_TOKEN applies only to streamable-http. Use a private local client for stdio."
        )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
