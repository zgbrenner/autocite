# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, get_package_paths


root = Path(SPECPATH).resolve().parent
_, docx_package_path = get_package_paths("docx")
docx_package_dir = Path(docx_package_path)

packages = (
    "autocite_mcp",
    "mcp",
    "uvicorn",
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_core",
    "httpx",
    "httpcore",
    "anyio",
    "eyecite",
    "courts_db",
    "reporters_db",
    "bs4",
    "lxml",
    "docx",
    "pypdf",
)

datas = []
binaries = []
hiddenimports = []
for package in packages:
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports
datas.append((str(docx_package_dir / "templates"), "docx/templates"))

analysis = Analysis(
    [str(root / "packaging/autocite-sidecar.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "torch", "transformers", "sentence_transformers"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="autocite-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
