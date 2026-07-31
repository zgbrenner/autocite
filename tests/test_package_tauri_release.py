from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.package_tauri_release import package_release


def test_packages_installers_with_checksums_and_manifest(tmp_path: Path):
    bundle_root = tmp_path / "bundle"
    (bundle_root / "nsis").mkdir(parents=True)
    (bundle_root / "msi").mkdir()
    installer = bundle_root / "nsis" / "AutoCite 0.7 setup.exe"
    package = bundle_root / "msi" / "AutoCite_0.7_x64.msi"
    installer.write_bytes(b"nsis-installer")
    package.write_bytes(b"msi-package")

    output = tmp_path / "release"
    manifest_path = package_release(
        bundle_root=bundle_root,
        output_dir=output,
        platform="windows-x64",
        target="x86_64-pc-windows-msvc",
        version="0.7.0-dev.0",
        commit="abc123",
        run_id="42",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["platform"] == "windows-x64"
    assert manifest["target"] == "x86_64-pc-windows-msvc"
    assert manifest["signed"] is False
    assert len(manifest["assets"]) == 2
    for asset in manifest["assets"]:
        copied = output / asset["filename"]
        assert copied.is_file()
        digest = hashlib.sha256(copied.read_bytes()).hexdigest()
        assert asset["sha256"] == digest
        assert copied.with_name(f"{copied.name}.sha256").read_text(
            encoding="utf-8"
        ) == f"{digest}  {copied.name}\n"


def test_rejects_unknown_platform(tmp_path: Path):
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(ValueError, match="unsupported release platform"):
        package_release(
            bundle_root=bundle_root,
            output_dir=tmp_path / "release",
            platform="plan9-x64",
            target="x86_64-plan9",
            version="0.7.0",
            commit="abc123",
            run_id="42",
        )


def test_rejects_release_when_no_expected_installer_exists(tmp_path: Path):
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    (bundle_root / "debug.txt").write_text("not an installer", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="no supported linux-x64 installers"):
        package_release(
            bundle_root=bundle_root,
            output_dir=tmp_path / "release",
            platform="linux-x64",
            target="x86_64-unknown-linux-gnu",
            version="0.7.0",
            commit="abc123",
            run_id="42",
        )


def test_rejects_symlinks_in_bundle_tree(tmp_path: Path):
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    target = tmp_path / "outside.AppImage"
    target.write_bytes(b"external")
    link = bundle_root / "AutoCite.AppImage"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable on this platform")

    with pytest.raises(ValueError, match="contains a symlink"):
        package_release(
            bundle_root=bundle_root,
            output_dir=tmp_path / "release",
            platform="linux-x64",
            target="x86_64-unknown-linux-gnu",
            version="0.7.0",
            commit="abc123",
            run_id="42",
        )
