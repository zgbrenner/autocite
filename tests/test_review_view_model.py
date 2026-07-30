from __future__ import annotations

from autocite_mcp.review_session import ReviewDecision, ReviewSession
from autocite_mcp.review_view_model import DesktopReviewViewModel, ReviewFilter


RESULT = {
    "applied_edits": [
        {
            "code": "STATUTE_CODE_ABBREVIATION",
            "start": 7,
            "end": 10,
            "original": "USC",
            "suggestion": "U.S.C.",
            "correction_level": "safe_auto_fix",
            "confidence": "high",
            "severity": "error",
            "provenance": "deterministic_logic",
            "source_type": "statute",
        },
        {
            "code": "SECTION_SYMBOL_SPACING",
            "start": 11,
            "end": 12,
            "original": "§",
            "suggestion": "§ ",
            "correction_level": "safe_auto_fix",
            "confidence": "high",
            "severity": "error",
            "provenance": "deterministic_logic",
            "source_type": "statute",
        },
    ],
    "remaining_issues": [
        {
            "code": "PROPOSITION_PINCITE_REVIEW",
            "start": 18,
            "end": 23,
            "original": "Smith",
            "message": "Review whether this proposition requires a pinpoint citation.",
            "correction_level": "review_required",
            "confidence": "medium",
            "severity": "warning",
            "provenance": "deterministic_logic",
            "source_type": "case",
        }
    ],
    "rule_findings": [
        {
            "issue_code": "UNSUPPORTED_LOCAL_RULE",
            "start": 24,
            "end": 29,
            "original": "Jones",
            "explanation": "Check the current local rule.",
            "correction_level": "unsupported",
            "confidence": "high",
            "severity": "info",
            "provenance": "deterministic_logic",
            "source_type": "case",
        }
    ],
}


def _model() -> DesktopReviewViewModel:
    return DesktopReviewViewModel(ReviewSession.from_result(RESULT))


def test_accept_reject_and_reset_are_undoable_without_mutating_prior_snapshots():
    model = _model()
    first = model.visible_items[0]
    original_session = model.session

    model.reject(first.item_id)
    assert model.item(first.item_id).decision is ReviewDecision.REJECTED
    assert original_session.items[0].decision is ReviewDecision.ACCEPTED
    assert model.can_undo is True

    model.undo()
    assert model.item(first.item_id).decision is ReviewDecision.ACCEPTED
    assert model.can_redo is True

    model.redo()
    assert model.item(first.item_id).decision is ReviewDecision.REJECTED

    model.reset(first.item_id)
    assert model.item(first.item_id).decision is ReviewDecision.PENDING


def test_filters_cover_decision_correction_level_severity_source_and_search():
    model = _model()
    model.set_filter(ReviewFilter.PENDING)
    assert [item.code for item in model.visible_items] == [
        "PROPOSITION_PINCITE_REVIEW",
        "UNSUPPORTED_LOCAL_RULE",
    ]

    model.set_filter(ReviewFilter.UNSUPPORTED)
    assert [item.code for item in model.visible_items] == ["UNSUPPORTED_LOCAL_RULE"]

    model.set_filter(ReviewFilter.ALL)
    model.set_severity("warning")
    assert [item.code for item in model.visible_items] == [
        "PROPOSITION_PINCITE_REVIEW"
    ]

    model.set_severity(None)
    model.set_source_type("statute")
    assert all(item.source_type == "statute" for item in model.visible_items)

    model.set_source_type(None)
    model.set_search("local rule")
    assert [item.code for item in model.visible_items] == ["UNSUPPORTED_LOCAL_RULE"]


def test_accept_all_safe_never_accepts_review_required_or_unsupported_items():
    model = _model()
    for item in tuple(model.session.items):
        model.reset(item.item_id)

    model.accept_all_safe()

    safe = [item for item in model.session.items if item.is_safe_text_edit]
    judgment = [item for item in model.session.items if not item.is_safe_text_edit]
    assert safe and all(item.decision is ReviewDecision.ACCEPTED for item in safe)
    assert judgment and all(item.decision is ReviewDecision.PENDING for item in judgment)


def test_navigation_tracks_visible_items_and_survives_filter_changes():
    model = _model()
    assert model.current_item is not None
    first_id = model.current_item.item_id

    second = model.next_item()
    assert second is not None and second.item_id != first_id
    assert model.previous_item() is not None
    assert model.current_item.item_id == first_id

    model.set_filter(ReviewFilter.UNSUPPORTED)
    assert model.current_item is not None
    assert model.current_item.code == "UNSUPPORTED_LOCAL_RULE"


def test_corrected_preview_reflects_only_currently_accepted_text_edits():
    original = "See 42 USC §1983; Smith Jones."
    model = _model()

    assert model.render_corrected_text(original) == (
        "See 42 U.S.C. § 1983; Smith Jones."
    )

    abbreviation = next(
        item for item in model.session.items if item.code == "STATUTE_CODE_ABBREVIATION"
    )
    model.reject(abbreviation.item_id)

    assert model.render_corrected_text(original) == "See 42 USC § 1983; Smith Jones."


def test_summary_counts_and_decision_mapping_are_stable():
    model = _model()
    summary = model.summary()

    assert summary.total == 4
    assert summary.accepted == 2
    assert summary.pending == 2
    assert summary.rejected == 0
    assert summary.safe_text_edits == 2
    assert len(model.decisions) == 4


def test_history_is_bounded():
    model = DesktopReviewViewModel(ReviewSession.from_result(RESULT), history_limit=3)
    first = model.session.items[0]

    for index in range(10):
        if index % 2:
            model.accept(first.item_id)
        else:
            model.reject(first.item_id)

    undo_count = 0
    while model.can_undo:
        model.undo()
        undo_count += 1

    assert undo_count == 3
