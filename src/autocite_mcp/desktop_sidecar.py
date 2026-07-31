from __future__ import annotations

import os

from .hosting import build_http_app, resolve_bind_host


def main() -> None:
    """Run the authenticated loopback service bundled with the Tauri shell."""
    import uvicorn

    host = resolve_bind_host(
        os.getenv("AUTOCITE_HOST", "127.0.0.1"),
        allow_remote="0",
        api_token=os.getenv("AUTOCITE_API_TOKEN"),
    )
    token = os.getenv("AUTOCITE_API_TOKEN")
    if not token:
        raise RuntimeError("the desktop sidecar requires AUTOCITE_API_TOKEN")
    port = int(os.getenv("AUTOCITE_PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("AUTOCITE_PORT must be between 1 and 65535")
    uvicorn.run(
        build_http_app(api_token=token),
        host=host,
        port=port,
        access_log=False,
        log_level=os.getenv("AUTOCITE_LOG_LEVEL", "warning"),
        server_header=False,
        date_header=False,
        workers=1,
    )


if __name__ == "__main__":
    main()
