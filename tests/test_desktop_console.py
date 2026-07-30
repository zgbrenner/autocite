from __future__ import annotations

import json
import sys

import autocite_mcp.desktop_entry as desktop_entry


def test_version_command_succeeds_without_console_streams(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    assert desktop_entry.run(["--version"]) == 0
    assert sys.stdout is not None
    assert sys.stderr is not None


def test_preservation_self_test_command_returns_machine_readable_result(
    monkeypatch, capsys
):
    async def fake_self_test():
        return {
            "status": "ok",
            "preservation_mode": "original_docx",
            "source_unchanged": True,
        }

    monkeypatch.setattr(desktop_entry, "run_preservation_self_test", fake_self_test)

    assert desktop_entry.run(["--self-test-preservation"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ok"
    assert output["preservation_mode"] == "original_docx"


def test_normal_launch_uses_the_review_workspace(monkeypatch):
    calls: list[tuple[str, ...]] = []

    def fake_workspace(argv):
        calls.append(tuple(argv))
        return 23

    monkeypatch.setattr(desktop_entry, "run_review_workspace", fake_workspace)

    assert desktop_entry.run([]) == 23
    assert calls == [()]
