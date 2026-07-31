from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_spec(name: str) -> str:
    return (ROOT / "packaging" / name).read_text(encoding="utf-8")


def assert_docx_template_mapping(spec: str) -> None:
    assert "get_package_paths" in spec
    assert 'get_package_paths("docx")' in spec
    assert 'docx_templates_dir = docx_package_dir / "templates"' in spec
    assert 'sorted(docx_templates_dir.rglob("*"))' in spec
    assert "template_file.is_file()" in spec
    assert "template_file.relative_to(docx_templates_dir).parent" in spec
    assert 'destination = Path("docx/templates") / relative_parent' in spec
    assert "datas.append((str(template_file), destination.as_posix()))" in spec
    assert 'datas.append((str(docx_package_dir / "templates"), "docx/templates"))' not in spec


def test_portable_desktop_spec_resolves_entrypoint_from_repository_root():
    spec = read_spec("autocite-desktop.spec")

    assert "root = Path(SPECPATH).resolve().parent" in spec
    assert "parent.parent" not in spec
    assert 'root / "packaging/autocite-desktop.py"' in spec
    assert 'pathex=[str(root / "src")]' in spec


def test_portable_launcher_preserves_autocite_package_context():
    launcher = (ROOT / "packaging" / "autocite-desktop.py").read_text(
        encoding="utf-8"
    )

    assert "from autocite_mcp.desktop_entry import run" in launcher
    assert "raise SystemExit(run())" in launcher
    assert "from ." not in launcher


def test_portable_spec_bundles_runtime_data_resources():
    spec = read_spec("autocite-desktop.spec")

    assert 'collect_data_files("courts_db")' in spec
    assert 'collect_data_files("reporters_db")' in spec
    assert_docx_template_mapping(spec)


def test_tauri_sidecar_spec_resolves_entrypoint_from_repository_root():
    spec = read_spec("autocite-sidecar.spec")

    assert "root = Path(SPECPATH).resolve().parent" in spec
    assert "parent.parent" not in spec
    assert 'root / "packaging/autocite-sidecar.py"' in spec
    assert 'pathex=[str(root / "src")]' in spec


def test_tauri_sidecar_bundles_runtime_data_resources():
    spec = read_spec("autocite-sidecar.spec")

    assert '"courts_db"' in spec
    assert '"reporters_db"' in spec
    assert '"docx"' in spec
    assert_docx_template_mapping(spec)
