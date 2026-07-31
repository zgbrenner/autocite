from __future__ import annotations

import os
import sys


def main() -> None:
    mode = os.environ.get("AUTOCITE_APPLICATION_MODE", "mcp").strip().lower()
    if mode in {"http", "desktop", "sidecar"}:
        from .http_api import main as http_main

        http_main(sys.argv[1:])
        return
    from .mcp_server import main as mcp_main

    mcp_main()


if __name__ == "__main__":
    main()
