#!/usr/bin/env python3
"""Build AutoCite's Python application backend as a Tauri sidecar binary."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINT = REPOSITORY_ROOT / "scripts" / "autocite_sidecar.py"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "apps" / "desktop" / "src-tauri" / "binaries"


def detect_target_triple() -> str:
    completed = subprocess.run(
        ["rustc", "-vV"],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in completed.stdout.splitlines():
        if line.startswith("host: "):
            return line.removeprefix("host: ").strip()
    raise RuntimeError("rustc did not report a host target triple")


def build_sidecar(output_directory: Path, target_triple: str) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    executable_suffix = ".exe" if "windows" in target_triple else ""
    tauri_name = f"autocite-sidecar-{target_triple}{executable_suffix}"
    destination = output_directory / tauri_name

    with tempfile.TemporaryDirectory(prefix="autocite-sidecar-") as temporary:
        temporary_root = Path(temporary)
        dist = temporary_root / "dist"
        work = temporary_root / "work"
        spec = temporary_root / "spec"
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--console",
            "--name",
            "autocite-sidecar",
            "--distpath",
            str(dist),
            "--workpath",
            str(work),
            "--specpath",
            str(spec),
            "--paths",
            str(REPOSITORY_ROOT / "src"),
            "--collect-submodules",
            "autocite_mcp",
            "--collect-data",
            "autocite_mcp",
            "--hidden-import",
            "autocite_mcp.application.http_api",
            "--hidden-import",
            "autocite_mcp.application.engine_adapter",
            str(ENTRY_POINT),
        ]
        environment = os.environ.copy()
        environment.setdefault("PYTHONUTF8", "1")
        subprocess.run(command, cwd=REPOSITORY_ROOT, env=environment, check=True)
        built_name = "autocite-sidecar.exe" if os.name == "nt" else "autocite-sidecar"
        built = dist / built_name
        if not built.is_file():
            raise FileNotFoundError(f"PyInstaller did not create {built}")
        shutil.copy2(built, destination)

    if os.name != "nt":
        destination.chmod(destination.stat().st_mode | 0o111)
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory for target-triple sidecar binaries.",
    )
    parser.add_argument(
        "--target-triple",
        default=None,
        help="Rust target triple. Defaults to rustc's host triple.",
    )
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    target = arguments.target_triple or detect_target_triple()
    output = build_sidecar(arguments.output.resolve(), target)
    print(output)


if __name__ == "__main__":
    main()
