from __future__ import annotations

from autocite_mcp.context_reduction import DeterministicLegalContextReducer


def test_reducer_keeps_exact_focus_and_adjacent_legal_context() -> None:
    text = (
        "INTRODUCTION\n\n"
        "This paragraph contains background that is not needed for the citation task. "
        * 12
        + "\n\nARGUMENT\n\n"
        + "A state actor may be liable for depriving a person of federal rights. "
        + "See 42 U.S.C. § 1983. The cited statute supplies the cause of action.\n\n"
        + "CONCLUSION\n\nThe motion should be denied."
    )
    focus = "42 U.S.C. § 1983"
    start = text.index(focus)
    reducer = DeterministicLegalContextReducer(max_chars=480)

    reduced = reducer.reduce(
        text,
        focus_start=start,
        focus_end=start + len(focus),
    )

    assert focus in reduced.text
    assert "A state actor may be liable" in reduced.text
    assert "The cited statute supplies" in reduced.text
    assert reduced.output_chars < reduced.input_chars
    assert reduced.compression_ratio < 1.0
    assert reduced.bypassed is False
    assert reduced.original_sha256
    assert any(
        span.start <= start and span.end >= start + len(focus)
        for span in reduced.protected_spans
    )
    assert all(text[span.start : span.end] == span.text for span in reduced.spans)


def test_reducer_bypasses_when_savings_are_negligible() -> None:
    text = "The court considered Smith v. Jones, 123 F.3d 456 (9th Cir. 2024)."
    citation = "Smith v. Jones, 123 F.3d 456 (9th Cir. 2024)"
    start = text.index(citation)

    reduced = DeterministicLegalContextReducer(
        max_chars=2_000,
        minimum_savings_ratio=0.15,
    ).reduce(
        text,
        focus_start=start,
        focus_end=start + len(citation),
    )

    assert reduced.bypassed is True
    assert reduced.text == text
    assert reduced.compression_ratio == 1.0


def test_reducer_rejects_invalid_focus_ranges() -> None:
    reducer = DeterministicLegalContextReducer()

    try:
        reducer.reduce("abc", focus_start=2, focus_end=5)
    except ValueError as exc:
        assert "focus range" in str(exc)
    else:
        raise AssertionError("invalid focus range must fail")
