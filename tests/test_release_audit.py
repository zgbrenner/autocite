from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_required_release_documentation_exists():
    required = [
        "ARCHITECTURE.md",
        "TRUST_SAFETY.md",
        "RULE_COVERAGE.json",
        "MODEL_CARD.md",
        "EVALUATION_REPORT.md",
        "PRIVACY.md",
        "LOCAL_INSTALL.md",
        "DESKTOP.md",
        "SKILL_INTEGRATIONS.md",
        "DEVELOPER.md",
        "RELEASE_NOTES.md",
    ]
    assert all((ROOT / "docs" / name).is_file() for name in required)


def test_cyclonedx_sbom_covers_locked_project():
    path = ROOT / "scripts" / "generate_sbom.py"
    spec = importlib.util.spec_from_file_location("generate_sbom", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sbom = module.generate(ROOT / "uv.lock")
    assert sbom["bomFormat"] == "CycloneDX"
    assert any(item["name"] == "autocite-mcp" for item in sbom["components"])
    assert len(sbom["components"]) > 20


def test_release_language_does_not_claim_full_bluebook_compliance():
    text = (ROOT / "README.md").read_text().casefold()
    assert "does not claim complete bluebook compliance" in text
    assert "fully bluebook-compliant" not in text
