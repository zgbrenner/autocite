# PyInstaller specification for a fast-starting, installer-free desktop bundle.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


root = Path(SPECPATH).resolve().parent

datas = collect_data_files("autocite_mcp")
datas += collect_data_files("reporters_db")
hiddenimports = collect_submodules("eyecite")

analysis = Analysis(
    [str(root / "src/autocite_mcp/desktop_entry.py")],
    pathex=[str(root / "src")],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "bitsandbytes",
        "gliner",
        "sentence_transformers",
        "torch",
        "torchvision",
        "transformers",
    ],
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="AutoCite",
    console=False,
    debug=False,
    strip=False,
    upx=False,
)
bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    name="AutoCite",
    strip=False,
    upx=False,
)
