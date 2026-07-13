import base64
import io
import zipfile

import pytest
from docx import Document

from autocite_mcp.documents import (
    DocumentLoadError,
    build_review_docx,
    load_document_bytes,
    validate_download_url,
)


def test_loads_plain_text_and_markdown():
    plain = load_document_bytes("42 USC §1983".encode("utf-8"), "brief.txt", "text/plain")
    assert plain.text == "42 USC §1983"
    markdown = load_document_bytes(b"# Note\n\n576 U.S. 644", "note.md", "text/markdown")
    assert "576 U.S. 644" in markdown.text


def test_loads_docx():
    document = Document()
    document.add_paragraph("Obergefell v. Hodges, 576 U.S. 644 (2015)")
    stream = io.BytesIO()
    document.save(stream)
    loaded = load_document_bytes(
        stream.getvalue(),
        "brief.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert "576 U.S. 644" in loaded.text


def test_scanned_pdf_requires_ocr():
    minimal_pdf = b"%PDF-1.4\n%%EOF"
    with pytest.raises(DocumentLoadError) as exc:
        load_document_bytes(minimal_pdf, "scan.pdf", "application/pdf")
    assert exc.value.code == "ocr_required"


def test_remote_file_urls_require_public_https():
    assert validate_download_url("https://files.example.com/document.docx").startswith("https://")
    for url in (
        "http://files.example.com/document.docx",
        "https://127.0.0.1/document.docx",
        "https://169.254.169.254/latest/meta-data/",
        "https://localhost/document.docx",
    ):
        with pytest.raises(DocumentLoadError) as exc:
            validate_download_url(url)
        assert exc.value.code == "unsafe_download_url"


def test_build_review_docx_contains_tracked_changes():
    payload = build_review_docx("42 USC §1983", "42 U.S.C. § 1983", tracked=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert "w:ins" in xml
    assert "w:del" in xml


def test_export_payload_can_be_base64_encoded():
    payload = build_review_docx("Id", "Id.", tracked=False)
    assert base64.b64decode(base64.b64encode(payload)) == payload
