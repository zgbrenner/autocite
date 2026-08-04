from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Iterable


PLATFORM_SUFFIXES: dict[str, tuple[str, ...]] = {
    "windows-x64": (".exe", ".msi"),
    "macos-x64": (".dmg",),
    "macos-arm64": (".dmg",),
    "linux-x64": (".appimage", ".deb"),
}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._+-]+")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def matching_assets(bundle_root: Path, platform: str) -> Iterable[Path]:
    suffixes = PLATFORM_SUFFIXES.get(platform)
    if suffixes is None:
        raise ValueError(f"unsupported release platform: {platform}")
    for path in sorted(bundle_root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"release bundle contains a symlink: {path}")
        if path.is_file() and path.suffix.lower() in suffixes:
            yield path


def safe_asset_name(platform: str, source_name: str) -> str:
    cleaned = SAFE_NAME.sub("-", source_name.strip()).strip("-.")
    if not cleaned:
        raise ValueError("release asset name became empty after sanitization")
    return f"AutoCite-{platform}-{cleaned}"


def package_release(
    *,
    bundle_root: Path,
    output_dir: Path,
    platform: str,
    target: str,
    version: str,
    commit: str,
    run_id: str,
) -> Path:
    bundle_root = bundle_root.resolve(strict=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()

    sources = list(matching_assets(bundle_root, platform))
    if not sources:
        raise FileNotFoundError(
            f"no supported {platform} installers were found under {bundle_root}"
        )

    assets: list[dict[str, object]] = []
    seen: set[str] = set()
    for source in sources:
        name = safe_asset_name(platform, source.name)
        folded = name.casefold()
        if folded in seen:
            raise ValueError(f"duplicate normalized release asset: {name}")
        seen.add(folded)
        destination = output_dir / name
        shutil.copyfile(source, destination)
        digest = sha256(destination)
        checksum = destination.with_name(f"{destination.name}.sha256")
        checksum.write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
        assets.append(
            {
                "filename": destination.name,
                "bytes": destination.stat().st_size,
                "sha256": digest,
                "source": source.relative_to(bundle_root).as_posix(),
            }
        )

    manifest = {
        "schema_version": 1,
        "product": "AutoCite Desktop",
        "version": version,
        "platform": platform,
        "target": target,
        "commit": commit,
        "workflow_run_id": run_id,
        "signed": False,
        "assets": assets,
    }
    manifest_path = output_dir / f"AutoCite-{platform}.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize and verify installers emitted by a Tauri build."
    )
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--platform", choices=sorted(PLATFORM_SUFFIXES), required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    manifest = package_release(
        bundle_root=args.bundle_root,
        output_dir=args.output,
        platform=args.platform,
        target=args.target,
        version=args.version,
        commit=args.commit,
        run_id=args.run_id,
    )
    print(manifest)


if __name__ == "__main__":
    main()
