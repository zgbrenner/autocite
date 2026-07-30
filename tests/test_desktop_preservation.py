from __future__ import annotations

import hashlib
from pathlib import Path

from docx import Document

from autocite_mcp.desktop_preservation import (
    PreservationDesktopReviewController,
    PreservationDesktopReviewState,
    run_preservation_self_test,
)


async def test_preservation_controller_retains_original_docx_structure(tmp_path: Path):
    source = tmp_path / "brief.docx"
    document = Document()
    document.sections[0].header.paragraphs[0].text = "Privileged Draft"
    document.add_paragraph("See 42 USC §1983.")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Record citation"
    table.cell(0, 1).text = "ECF 12"
    document.save(source)
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    controller = PreservationDesktopReviewController()
    state = await controller.review_file(source, mode="bluepages")
    assert state.error_code is None
    assert state.result is not None
    assert state.source_bytes is not None

    destination = tmp_path / "review.docx"
    metadata = controller.export_docx(state, destination)

    assert metadata["preservation_mode"] == "original_docx"
    assert metadata["path"] == str(destination)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    reviewed = Document(destination)
    assert reviewed.sections[0].header.paragraphs[0].text == "Privileged Draft"
    assert reviewed.tables[0].cell(0, 0).text == "Record citation"
    assert reviewed.tables[0].cell(0, 1).text == "ECF 12"


async def test_non_docx_desktop_export_remains_a_labeled_fallback(tmp_path: Path):
    source = tmp_path / "brief.txt"
    source.write_text("See 42 USC §1983.", encoding="utf-8")

    controller = PreservationDesktopReviewController()
    state = await controller.review_file(source, mode="bluepages")
    destination = tmp_path / "review.docx"
    metadata = controller.export_docx(state, destination)

    assert destination.is_file()
    assert metadata["preservation_mode"] == "reconstructed_text"


async def test_preservation_self_test_exercises_original_docx_export():
    result = await run_preservation_self_test()

    assert result["status"] == "ok"
    assert result["preservation_mode"] == "original_docx"
    assert result["source_unchanged"] is True
    assert result["header_preserved"] is True
    assert result["table_preserved"] is True
    assert result["export_size_bytes"] > 0


def test_preserved_state_repr_does_not_expose_source_bytes():
    state = PreservationDesktopReviewState(
        original_text="original",
        corrected_text="corrected",
        result={},
        source_bytes=b"confidential document bytes",
    )

    assert "confidential document bytes" not in repr(state)
