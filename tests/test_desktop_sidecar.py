from __future__ import annotations

from autocite_mcp.desktop_sidecar import (
    sidecar_preservation_self_test,
    sidecar_self_test,
)


def test_desktop_sidecar_self_test_stays_local_and_authenticated():
    result = sidecar_self_test()

    assert result == {
        "status": "ok",
        "host": "127.0.0.1",
        "authenticated": True,
        "local_first": True,
    }


def test_desktop_sidecar_preservation_self_test_keeps_word_structure():
    result = sidecar_preservation_self_test()

    assert result["status"] == "ok"
    assert result["preservation_mode"] == "original_docx"
    assert result["source_unchanged"] is True
    assert result["header_preserved"] is True
    assert result["table_preserved"] is True
    assert result["export_size_bytes"] > 0
