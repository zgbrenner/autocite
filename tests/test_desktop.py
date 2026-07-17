from __future__ import annotations

from pathlib import Path

from autocite_mcp.desktop import DesktopReviewController


async def test_desktop_controller_uses_core_review_and_preserves_original(
    tmp_path: Path,
):
    source = tmp_path / "brief.txt"
    source.write_text("See 42 USC §1983.")
    state = await DesktopReviewController().review_file(source, mode="bluepages")
    assert state.original_text == "See 42 USC §1983."
    assert state.corrected_text == "See 42 U.S.C. § 1983."
    assert source.read_text() == state.original_text
    assert state.result["schema_version"] == "1.0"


async def test_desktop_rejects_unknown_format_without_modifying_it(tmp_path: Path):
    source = tmp_path / "brief.bin"
    source.write_bytes(b"original")
    state = await DesktopReviewController().review_file(source)
    assert state.error_code == "unsupported_format"
    assert source.read_bytes() == b"original"


async def test_desktop_export_is_caller_selected(tmp_path: Path):
    source = tmp_path / "brief.txt"
    source.write_text("See 42 USC §1983.")
    state = await DesktopReviewController().review_file(source, mode="bluepages")
    destination = tmp_path / "review.docx"
    artifact = DesktopReviewController().export_docx(state, destination)
    assert destination.is_file()
    assert artifact["tracked_changes"] is True
