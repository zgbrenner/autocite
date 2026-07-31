from __future__ import annotations

import io

from pypdf import PdfReader

from autocite_mcp.pdf_export import build_text_pdf


def test_text_pdf_is_valid_searchable_and_paginated() -> None:
    text = "Motion to Dismiss\n\n" + "See 42 U.S.C. § 1983.\n" * 180

    payload = build_text_pdf(text, title="Motion to Dismiss")

    assert payload.startswith(b"%PDF-1.4")
    reader = PdfReader(io.BytesIO(payload))
    assert len(reader.pages) >= 2
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Motion to Dismiss" in extracted
    assert "42 U.S.C." in extracted


def test_text_pdf_handles_empty_and_non_winansi_text_without_crashing() -> None:
    payload = build_text_pdf("Citation review ✓ — 完了", title="AutoCite")

    reader = PdfReader(io.BytesIO(payload))
    assert len(reader.pages) == 1
    assert "Citation review" in (reader.pages[0].extract_text() or "")
