# PyInstaller signable desktop bundle specification.
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("autocite_mcp")
a = Analysis(["src/autocite_mcp/desktop.py"], pathex=["."], datas=datas)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="AutoCite", console=False)
