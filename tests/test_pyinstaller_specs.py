from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_spec(name: str) -> str:
    return (ROOT / "packaging" / name).read_text(encoding="utf-8")


def test_portable_desktop_spec_resolves_entrypoint_from_repository_root():
    spec = read_spec("autocite-desktop.spec")

    assert "Path(SPECPATH).resolve().parent.parent" in spec
    assert 'root / "src/autocite_mcp/desktop_entry.py"' in spec
    assert 'pathex=[str(root / "src")]' in spec


def test_tauri_sidecar_spec_resolves_entrypoint_from_repository_root():
    spec = read_spec("autocite-sidecar.spec")

    assert "Path(SPECPATH).resolve().parent.parent" in spec
    assert 'root / "packaging/autocite-sidecar.py"' in spec
    assert 'pathex=[str(root / "src")]' in spec
