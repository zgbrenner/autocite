from __future__ import annotations

from autocite_mcp.tools import export_review_docx


def test_export_review_docx_defaults_filename_when_blank():
    result = export_review_docx("original", "corrected", filename="")
    assert result["filename"] == "autocite-review.docx"


def test_export_review_docx_appends_docx_extension_when_missing():
    result = export_review_docx("original", "corrected", filename="my-review")
    assert result["filename"] == "my-review.docx"


def test_export_review_docx_preserves_given_docx_filename():
    result = export_review_docx("original", "corrected", filename="brief.docx")
    assert result["filename"] == "brief.docx"
