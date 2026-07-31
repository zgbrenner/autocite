from __future__ import annotations

from autocite_mcp.desktop_sidecar import sidecar_self_test


def test_desktop_sidecar_self_test_stays_local_and_authenticated():
    result = sidecar_self_test()

    assert result == {
        "status": "ok",
        "host": "127.0.0.1",
        "authenticated": True,
        "local_first": True,
    }
