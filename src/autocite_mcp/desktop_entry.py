from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Sequence
from typing import TextIO

from . import desktop as desktop_module
from .desktop_preservation import (
    PreservationDesktopReviewController,
    run_preservation_self_test,
)


def _writable_null_stream() -> TextIO:
    return open(os.devnull, "w", encoding="utf-8")


def ensure_console_streams() -> None:
    """Provide harmless output streams in windowed PyInstaller processes.

    Windows GUI executables can start with ``sys.stdout`` and ``sys.stderr`` set
    to ``None``. AutoCite's version and packaged self-test commands still need to
    finish cleanly in that environment, even though their output is discarded.
    """
    if sys.stdout is None:
        sys.stdout = _writable_null_stream()
    if sys.stderr is None:
        sys.stderr = _writable_null_stream()


def run(argv: Sequence[str] | None = None) -> int:
    ensure_console_streams()
    # The existing desktop UI resolves this controller from its module globals
    # when a window or packaged self-test starts. Replacing it here upgrades both
    # paths without duplicating the UI or the deterministic review workflow.
    desktop_module.DesktopReviewController = PreservationDesktopReviewController
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--self-test-preservation" in arguments:
        try:
            result = asyncio.run(run_preservation_self_test())
        except Exception as exc:
            print(f"AutoCite preservation self-test failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0
    return desktop_module.main(arguments)


if __name__ == "__main__":
    raise SystemExit(run())
