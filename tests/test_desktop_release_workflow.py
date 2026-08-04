from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_tauri_release_workflow_covers_every_supported_desktop_platform():
    workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")

    for runner, platform, target in (
        ("windows-2025", "windows-x64", "x86_64-pc-windows-msvc"),
        ("macos-15-intel", "macos-x64", "x86_64-apple-darwin"),
        ("macos-15", "macos-arm64", "aarch64-apple-darwin"),
        ("ubuntu-24.04", "linux-x64", "x86_64-unknown-linux-gnu"),
    ):
        assert f"os: {runner}" in workflow
        assert f"platform: {platform}" in workflow
        assert f"target: {target}" in workflow

    assert "npm ci --ignore-scripts" in workflow
    assert "packaging/autocite-sidecar.spec" in workflow
    assert "--self-test" in workflow
    assert "scripts/package_tauri_release.py" in workflow
    assert "cargo test --manifest-path desktop/src-tauri/Cargo.toml --locked" in workflow


def test_tauri_context_assets_are_committed_for_rust_tests():
    icon_root = ROOT / "desktop/src-tauri/icons"

    for filename in (
        "32x32.png",
        "128x128.png",
        "128x128@2x.png",
        "icon.ico",
        "icon.icns",
    ):
        path = icon_root / filename
        assert path.is_file(), f"missing committed Tauri icon: {filename}"
        assert path.stat().st_size > 0, f"empty committed Tauri icon: {filename}"


def test_every_successful_main_update_creates_an_attested_prerelease():
    workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")

    assert "branches: [main]" in workflow
    assert "workflow_dispatch:" in workflow
    assert "pull_request:" in workflow
    assert "actions/attest@v4" in workflow
    assert "anchore/sbom-action@v0" in workflow
    assert "attestations: write" in workflow
    assert "id-token: write" in workflow
    assert "desktop-v${VERSION}-${SHORT_SHA}" in workflow
    assert "--prerelease" in workflow
    assert "SHA256SUMS.txt" in workflow
