import json
from pathlib import Path

from autocite_mcp.setup_clients import install_claude_desktop


def test_install_claude_desktop_preserves_existing_servers(tmp_path: Path):
    config = tmp_path / "claude_desktop_config.json"
    config.write_text(
        json.dumps({"mcpServers": {"existing": {"command": "example"}}}),
        encoding="utf-8",
    )

    result = install_claude_desktop(config_path=config, python_executable="python-test")

    payload = json.loads(config.read_text(encoding="utf-8"))
    assert payload["mcpServers"]["existing"]["command"] == "example"
    assert payload["mcpServers"]["autocite"] == {
        "command": "python-test",
        "args": ["-m", "autocite_mcp.server"],
    }
    assert result["backup_path"] is not None
