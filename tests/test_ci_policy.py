from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_python_ci_is_concurrent_deterministic_and_scoped():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "cancel-in-progress: true" in workflow
    assert 'python-version: ["3.10", "3.11", "3.12", "3.13"]' in workflow
    assert "Package and corpus quality" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/upload-artifact@v7" in workflow


def test_release_builds_do_not_run_for_pull_requests_after_finalization():
    workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")
    finalizer = ROOT / ".github/workflows/repair-ci-once.yml"
    if finalizer.exists():
        finalizer_text = finalizer.read_text(encoding="utf-8")
        assert "branches: [main]" in finalizer_text
        assert "text.index('  pull_request:" in finalizer_text
    else:
        trigger_block = workflow.split("permissions:", 1)[0]
        assert "pull_request:" not in trigger_block


def test_dependency_audits_are_parallel_and_security_scoped():
    workflow = (ROOT / ".github/workflows/dependency-review.yml").read_text(
        encoding="utf-8"
    )
    for job in ("graph-review:", "python-audit:", "desktop-audit:", "rust-audit:"):
        assert job in workflow
    assert "uv lock --upgrade-package cryptography" in workflow
    assert "npm audit --prefix desktop --omit=dev --audit-level=high" in workflow
    assert "cargo audit --file desktop/src-tauri/Cargo.lock" in workflow
