from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from scripts.package_desktop import package_desktop_bundle


def test_package_desktop_bundle_is_self_contained_and_verifiable(tmp_path: Path):
    dist = tmp_path / "dist" / "AutoCite"
    dist.mkdir(parents=True)
    executable = dist / "AutoCite.exe"
    executable.write_bytes(b"portable-autocite")
    (dist / "runtime.dll").write_bytes(b"runtime")

    start_here = tmp_path / "START-HERE.txt"
    start_here.write_text("Double-click AutoCite.exe", encoding="utf-8")
    license_file = tmp_path / "LICENSE"
    license_file.write_text("MIT", encoding="utf-8")

    result = package_desktop_bundle(
        dist_dir=dist,
        output_dir=tmp_path / "release",
        platform_label="windows-x64",
        version="0.6.0",
        commit="abc123",
        start_here=start_here,
        license_file=license_file,
    )

    archive = Path(result["archive"])
    checksum = Path(result["checksum"])
    manifest = Path(result["manifest"])
    assert archive.name == "AutoCite-windows-x64-v0.6.0.zip"
    assert archive.is_file()
    assert checksum.is_file()
    assert manifest.is_file()

    expected_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert checksum.read_text(encoding="utf-8") == f"{expected_hash}  {archive.name}\n"

    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    assert metadata["version"] == "0.6.0"
    assert metadata["platform"] == "windows-x64"
    assert metadata["commit"] == "abc123"
    assert metadata["portable"] is True
    assert metadata["requires_installer"] is False
    assert metadata["requires_python"] is False
    assert {item["path"] for item in metadata["files"]} >= {
        "AutoCite.exe",
        "runtime.dll",
        "START HERE.txt",
        "LICENSE.txt",
    }

    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        assert "AutoCite/AutoCite.exe" in names
        assert "AutoCite/runtime.dll" in names
        assert "AutoCite/START HERE.txt" in names
        assert "AutoCite/LICENSE.txt" in names
        assert "AutoCite/BUILD-MANIFEST.json" in names
        bundled_manifest = json.loads(
            bundle.read("AutoCite/BUILD-MANIFEST.json").decode("utf-8")
        )
        assert bundled_manifest["archive_sha256"] is None


def test_package_desktop_rejects_missing_distribution(tmp_path: Path):
    try:
        package_desktop_bundle(
            dist_dir=tmp_path / "missing",
            output_dir=tmp_path / "release",
            platform_label="windows-x64",
            version="0.6.0",
            commit="abc123",
            start_here=tmp_path / "START-HERE.txt",
            license_file=tmp_path / "LICENSE",
        )
    except FileNotFoundError as exc:
        assert "distribution directory" in str(exc)
    else:
        raise AssertionError("missing distribution must be rejected")
