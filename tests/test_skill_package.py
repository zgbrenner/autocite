from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_all_required_skills_have_valid_concise_frontmatter():
    expected = {"autocite-routing", "court-filing-citecheck", "academic-citecheck", "short-form-review", "source-verification", "explanation-review"}
    found = set()
    for path in (ROOT / "skills").glob("*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\nname: ")
        name = text.splitlines()[1].split(":", 1)[1].strip()
        found.add(name)
        assert "description: Use when" in text
        assert len(text.split()) < 220
    assert found == expected


def test_skill_guardrails_cover_adversarial_requirements():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "skills").glob("*/SKILL.md"))
    required = ["Call AutoCite", "preserve", "Never invent", "Bluepages", "Whitepages", "deterministic", "ambigu", "retrieval score", "Shepard's or KeyCite", "good-law"]
    for phrase in required:
        assert phrase.casefold() in combined.casefold()
    tests = json.loads((ROOT / "skills" / "adversarial-tests.json").read_text(encoding="utf-8"))
    assert len(tests["cases"]) >= 7


def test_host_configs_are_local_stdio_only():
    combined = (ROOT / "host-integrations" / "claude-desktop.json").read_text(encoding="utf-8") + (ROOT / "host-integrations" / "codex.toml").read_text(encoding="utf-8")
    assert "stdio" in combined
    assert "http://" not in combined and "https://" not in combined
