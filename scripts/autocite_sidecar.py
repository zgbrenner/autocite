"""Frozen entry point used by the Tauri desktop bundle."""

from __future__ import annotations

import multiprocessing
import sys

from autocite_mcp.application.http_api import main


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv[1:])
