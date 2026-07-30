from __future__ import annotations

import sys

from autocite_mcp.desktop_entry import run


def test_version_command_succeeds_without_console_streams(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    assert run(["--version"]) == 0
    assert sys.stdout is not None
    assert sys.stderr is not None
