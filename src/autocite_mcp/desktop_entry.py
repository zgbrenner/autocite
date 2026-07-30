from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from typing import TextIO

from .desktop import main as desktop_main


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
    return desktop_main(argv)


if __name__ == "__main__":
    raise SystemExit(run())
