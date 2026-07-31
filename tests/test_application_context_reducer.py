from __future__ import annotations

import pytest

from autocite_mcp.application.context_reducer import (
    DeterministicLegalContextReducer,
    NoopContextReducer,
)


def test_legal_reducer_preserves_exact_citations_and_source_ranges() -> None:
    filler = "Background facts that are not relevant to this bounded task. " * 30
    citation_paragraph = (
        "The claim arises under 42 U.S.C. § 1983. See Monroe v. Pape, "
        "365 U.S. 167, 171 (1961)."
    )
    text = "\n\n".join([filler, filler, citation_paragraph, filler, filler, filler])
    reducer = DeterministicLegalContextReducer(
        neighbor_paragraphs=0,
        default_max_characters=1_500,
        minimum_savings_ratio=0.05,
    )

    reduced = reducer.reduce(text)

    assert not reduced.metrics.bypassed
    assert reduced.metrics.savings_ratio > 0.5
    assert "42 U.S.C. § 1983" in reduced.text
    assert "365 U.S. 167" in reduced.text
    assert reduced.reconstruct_selected_text(text) == reduced.text
    assert any("case_citation" in item.reason for item in reduced.protected_ranges)
    assert any("statute_or_regulation" in item.reason for item in reduced.protected_ranges)


def test_legal_reducer_bypasses_when_savings_are_negligible() -> None:
    text = "See 410 U.S. 113, 120 (1973)."
    reducer = DeterministicLegalContextReducer(default_max_characters=2_000)

    reduced = reducer.reduce(text)

    assert reduced.text == text
    assert reduced.metrics.bypassed
    assert reduced.metrics.bypass_reason == "within_budget"


def test_reduced_context_refuses_a_different_original() -> None:
    text = ("Introductory paragraph.\n\n" * 100) + "See 1 U.S. 1."
    reduced = DeterministicLegalContextReducer(
        neighbor_paragraphs=0,
        default_max_characters=1_000,
        minimum_savings_ratio=0.01,
    ).reduce(text)

    with pytest.raises(ValueError, match="does not match"):
        reduced.reconstruct_selected_text(text + " changed")


def test_noop_reducer_is_auditable() -> None:
    text = "Original text"
    reduced = NoopContextReducer().reduce(text)
    assert reduced.text == text
    assert reduced.metrics.bypassed
    assert reduced.selected_ranges[0].start == 0
    assert reduced.selected_ranges[0].end == len(text)
