from __future__ import annotations

import sys

from autocite_mcp.desktop import main


def test_version_command_succeeds_without_console_streams(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    assert main(["--version"]) == 0
