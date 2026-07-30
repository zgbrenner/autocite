from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_desktop_release_requires_complete_verification_build_and_smoke_stages():
    workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")
    for required in (
        "Lint complete repository",
        "Test complete repository",
        "Compile complete repository",
        "Evaluate deterministic gold corpus",
        "Evaluate held-out system corpus",
        "Validate training data pipeline",
        "Build and inspect Python distributions",
        "build-desktop:",
        "--self-test",
        "--self-test-preservation",
        "Verify release archives, checksums, and manifests",
    ):
        assert required in workflow


def test_desktop_release_uses_least_privilege_and_idempotent_immutable_tags():
    workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow
    assert "release:\n" in workflow
    assert "    permissions:\n      contents: write" in workflow
    assert "Create or verify immutable version tag" in workflow
    assert 'git fetch origin "refs/tags/$TAG:refs/tags/$TAG"' in workflow
    assert 'EXISTING_COMMIT=$(git rev-list -n 1 "$TAG")' in workflow
    assert 'if [[ "$EXISTING_COMMIT" != "$GITHUB_SHA" ]]' in workflow
    assert 'gh release view "$TAG"' in workflow
    assert "gh release upload \"$TAG\" release/* --clobber" in workflow


def test_desktop_release_rejects_unsafe_archive_members():
    workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")

    for required in (
        "PurePosixPath",
        "duplicate archive member",
        "archive traversal path",
        "unsafe Windows archive path",
        "stat.S_IFLNK",
        "AutoCite/BUILD-MANIFEST.json",
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
