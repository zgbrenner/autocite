from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dependabot_monitors_every_runtime_and_workflow_ecosystem():
    config = read(".github/dependabot.yml")

    for ecosystem, directory in (
        ("pip", "/"),
        ("npm", "/desktop"),
        ("cargo", "/desktop/src-tauri"),
        ("github-actions", "/"),
    ):
        assert f'package-ecosystem: "{ecosystem}"' in config
        assert f'directory: "{directory}"' in config


def test_pull_requests_receive_dependency_review():
    workflow = read(".github/workflows/dependency-review.yml")

    assert "pull_request:" in workflow
    assert "actions/dependency-review-action@v5" in workflow
    assert "fail-on-severity: high" in workflow
    assert "deny-licenses:" in workflow


def test_codeql_scans_python_javascript_and_rust_with_current_action():
    workflow = read(".github/workflows/codeql.yml")

    assert "github/codeql-action/init@v4" in workflow
    assert "github/codeql-action/analyze@v4" in workflow
    for language in ("python", "javascript-typescript", "rust"):
        assert f"language: {language}" in workflow
