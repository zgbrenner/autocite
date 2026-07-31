"""PyInstaller-safe entry point for the Tauri application sidecar."""

from __future__ import annotations

import multiprocessing
import sys

from .http_api import main


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv[1:])
