from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


def default_claude_config_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA is not set")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def install_claude_desktop(
    *,
    config_path: Path | None = None,
    python_executable: str | None = None,
    courtlistener_token: str | None = None,
) -> dict[str, Any]:
    """Add AutoCite to Claude Desktop while preserving all existing MCP servers."""
    path = config_path or default_claude_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = None

    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        payload = json.loads(raw) if raw else {}
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup_path)
    else:
        payload = {}

    if not isinstance(payload, dict):
        raise ValueError("Claude Desktop configuration must contain a JSON object")
    servers = payload.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be a JSON object")

    entry: dict[str, Any] = {
        "command": python_executable or sys.executable,
        "args": ["-m", "autocite_mcp.server"],
    }
    if courtlistener_token:
        entry["env"] = {"COURTLISTENER_TOKEN": courtlistener_token}
    servers["autocite"] = entry
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return {
        "installed": True,
        "config_path": str(path),
        "backup_path": str(backup_path) if backup_path else None,
        "server": entry,
        "next_step": "Completely quit and restart Claude Desktop, then enable AutoCite in Connectors.",
    }
