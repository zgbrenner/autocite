from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_desktop_release_requires_test_build_smoke_and_checksum_stages():
    workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")
    for required in (
        "verify:",
        "build-desktop:",
        "--self-test",
        "Verify release checksums and manifests",
        "Create immutable version tag",
    ):
        assert required in workflow


def test_ci_preserves_diagnostics_and_pipeline_exit_codes():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "set -o pipefail" in workflow
    assert "if: always()" in workflow
    assert "ci-diagnostics-${{ matrix.python-version }}" in workflow
    assert "pytest-results.xml" in workflow


def test_ci_matrix_does_not_hide_independent_failures():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "fail-fast: false" in workflow
    for version in ("3.10", "3.11", "3.12", "3.13"):
        assert f'"{version}"' in workflow
