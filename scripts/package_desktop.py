from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "BUILD-MANIFEST.json"
    ]


def _write_portable_zip(source_root: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(source_root.rglob("*")):
            relative = path.relative_to(source_root)
            member = PurePosixPath("AutoCite", *relative.parts).as_posix()
            if path.is_dir():
                info = zipfile.ZipInfo(f"{member}/", date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
                archive.writestr(info, b"")
                continue
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes())


def package_desktop_bundle(
    *,
    dist_dir: Path,
    output_dir: Path,
    platform_label: str,
    version: str,
    commit: str,
    start_here: Path,
    license_file: Path,
) -> dict[str, str]:
    dist_dir = Path(dist_dir)
    output_dir = Path(output_dir)
    start_here = Path(start_here)
    license_file = Path(license_file)
    if not dist_dir.is_dir():
        raise FileNotFoundError(f"desktop distribution directory not found: {dist_dir}")
    if not any(path.is_file() for path in dist_dir.rglob("*")):
        raise ValueError(f"desktop distribution directory is empty: {dist_dir}")
    if not start_here.is_file():
        raise FileNotFoundError(f"start-here guide not found: {start_here}")
    if not license_file.is_file():
        raise FileNotFoundError(f"license file not found: {license_file}")

    normalized_version = version.removeprefix("v")
    safe_platform = platform_label.strip().lower().replace(" ", "-")
    stem = f"AutoCite-{safe_platform}-v{normalized_version}"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{stem}.zip"
    checksum_path = output_dir / f"{stem}.zip.sha256"
    manifest_path = output_dir / f"{stem}.manifest.json"

    with tempfile.TemporaryDirectory(prefix="autocite-package-") as temporary:
        root = Path(temporary) / "AutoCite"
        shutil.copytree(dist_dir, root)
        shutil.copy2(start_here, root / "START HERE.txt")
        shutil.copy2(license_file, root / "LICENSE.txt")
        bundled_manifest = {
            "schema_version": "1.0",
            "product": "AutoCite Desktop",
            "version": normalized_version,
            "platform": safe_platform,
            "commit": commit,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "portable": True,
            "requires_installer": False,
            "requires_python": False,
            "requires_network_for_standard_review": False,
            "archive_sha256": None,
            "files": _file_manifest(root),
        }
        (root / "BUILD-MANIFEST.json").write_text(
            json.dumps(bundled_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_portable_zip(root, archive_path)

    archive_hash = _sha256(archive_path)
    checksum_path.write_text(
        f"{archive_hash}  {archive_path.name}\n", encoding="utf-8"
    )
    external_manifest = {**bundled_manifest, "archive_sha256": archive_hash}
    manifest_path.write_text(
        json.dumps(external_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "archive": str(archive_path),
        "checksum": str(checksum_path),
        "manifest": str(manifest_path),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a self-contained, verifiable AutoCite desktop ZIP."
    )
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--start-here", type=Path, required=True)
    parser.add_argument("--license", dest="license_file", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = package_desktop_bundle(
        dist_dir=args.dist,
        output_dir=args.output,
        platform_label=args.platform,
        version=args.version,
        commit=args.commit,
        start_here=args.start_here,
        license_file=args.license_file,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
