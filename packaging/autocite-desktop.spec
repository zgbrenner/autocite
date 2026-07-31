# PyInstaller specification for a fast-starting, installer-free desktop bundle.
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    get_package_paths,
)


root = Path(SPECPATH).resolve().parent
_, docx_package_path = get_package_paths("docx")
docx_package_dir = Path(docx_package_path)
docx_templates_dir = docx_package_dir / "templates"

datas = collect_data_files("autocite_mcp")
datas += collect_data_files("courts_db")
datas += collect_data_files("reporters_db")
for template_file in sorted(docx_templates_dir.rglob("*")):
    if not template_file.is_file():
        continue
    relative_parent = template_file.relative_to(docx_templates_dir).parent
    destination = Path("docx/templates") / relative_parent
    datas.append((str(template_file), destination.as_posix()))
hiddenimports = collect_submodules("eyecite")

analysis = Analysis(
    [str(root / "packaging/autocite-desktop.py")],
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
