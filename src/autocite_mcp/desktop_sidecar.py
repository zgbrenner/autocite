from __future__ import annotations

import json
import os
import sys
from typing import Any

from .hosting import build_http_app, resolve_bind_host


def sidecar_self_test() -> dict[str, Any]:
    """Verify the bundled imports and authenticated loopback configuration."""
    token = "autocite-sidecar-self-test"
    host = resolve_bind_host("127.0.0.1", allow_remote="0", api_token=token)
    app = build_http_app(api_token=token)
    if host != "127.0.0.1" or app.token != token:
        raise RuntimeError("the desktop sidecar self-test could not initialize safely")
    return {
        "status": "ok",
        "host": host,
        "authenticated": True,
        "local_first": True,
    }


def main() -> None:
    """Run the authenticated loopback service bundled with the Tauri shell."""
    if "--self-test" in sys.argv[1:]:
        print(json.dumps(sidecar_self_test(), sort_keys=True))
        return

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
