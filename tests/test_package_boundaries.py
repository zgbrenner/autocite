from pathlib import Path


def test_package_metadata_and_boundaries():
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.3.0"' in pyproject
    assert "beautifulsoup4" in pyproject
    assert "python-docx" in pyproject
    assert "pypdf" in pyproject
    assert '"/reference"' in pyproject


def test_security_source_review_and_release_docs_exist():
    root = Path(__file__).resolve().parents[1]
    security = (root / "docs" / "SECURITY.md").read_text(encoding="utf-8")
    source_review = (root / "docs" / "SOURCE_REVIEW.md").read_text(encoding="utf-8")
    release = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "No retention" in security
    assert "prompt injection" in security.lower()
    assert "not a citator" in source_review.lower()
    assert "pypa/gh-action-pypi-publish@release/v1" in release
    assert "id-token: write" in release
