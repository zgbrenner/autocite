from __future__ import annotations

import pytest

from autocite_mcp.review_session import (
    ReviewDecision,
    ReviewItemKind,
    ReviewSession,
)


FIXTURE_RESULT = {
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
        }
    ],
    "remaining_issues": [
        {
            "code": "PROPOSITION_PINCITE_REVIEW",
            "start": 20,
            "end": 30,
            "original": "Smith",
            "message": "Review whether this proposition requires a pinpoint citation.",
            "correction_level": "review_required",
            "confidence": "medium",
            "severity": "warning",
            "provenance": "deterministic_logic",
        }
    ],
    "rule_findings": [],
}


def test_review_session_defaults_safe_edits_to_accepted_and_review_items_to_pending():
    session = ReviewSession.from_result(FIXTURE_RESULT)

    assert session.items[0].kind is ReviewItemKind.TEXT_EDIT
    assert session.items[0].decision is ReviewDecision.ACCEPTED
    assert session.items[1].kind is ReviewItemKind.ANNOTATION
    assert session.items[1].decision is ReviewDecision.PENDING


def test_review_item_ids_are_stable_across_equivalent_results():
    first = ReviewSession.from_result(FIXTURE_RESULT)
    second = ReviewSession.from_result(dict(FIXTURE_RESULT))

    assert [item.item_id for item in first.items] == [
        item.item_id for item in second.items
    ]


def test_rejecting_a_safe_edit_removes_it_from_text_edits_and_records_the_decision():
    session = ReviewSession.from_result(FIXTURE_RESULT)
    edit_id = session.items[0].item_id

    changed = session.reject(edit_id)
    plan = changed.export_plan()

    assert plan.text_edits == ()
    assert any(
        annotation.item_id == edit_id
        and annotation.decision is ReviewDecision.REJECTED
        for annotation in plan.annotations
    )
    assert session.items[0].decision is ReviewDecision.ACCEPTED


def test_accept_all_safe_does_not_accept_judgment_dependent_findings():
    session = ReviewSession.from_result(FIXTURE_RESULT).reset(
        ReviewSession.from_result(FIXTURE_RESULT).items[0].item_id
    )

    changed = session.accept_all_safe()

    assert changed.items[0].decision is ReviewDecision.ACCEPTED
    assert changed.items[1].decision is ReviewDecision.PENDING


def test_duplicate_finding_from_two_result_collections_is_emitted_once():
    duplicate = dict(FIXTURE_RESULT["remaining_issues"][0])
    result = {**FIXTURE_RESULT, "rule_findings": [duplicate]}

    session = ReviewSession.from_result(result)

    assert len(session.items) == 2


def test_export_plan_rejects_overlapping_accepted_edits():
    result = {
        "applied_edits": [
            {
                "code": "ONE",
                "start": 1,
                "end": 5,
                "original": "abcd",
                "suggestion": "A",
                "correction_level": "safe_auto_fix",
                "confidence": "high",
            },
            {
                "code": "TWO",
                "start": 4,
                "end": 7,
                "original": "def",
                "suggestion": "B",
                "correction_level": "safe_auto_fix",
                "confidence": "high",
            },
        ],
        "remaining_issues": [],
        "rule_findings": [],
    }

    with pytest.raises(ValueError, match="overlap"):
        ReviewSession.from_result(result).export_plan()


def test_unknown_item_id_is_rejected():
    session = ReviewSession.from_result(FIXTURE_RESULT)

    with pytest.raises(KeyError, match="unknown review item"):
        session.accept("missing")


def test_session_serialization_excludes_no_data_needed_for_audit():
    session = ReviewSession.from_result(FIXTURE_RESULT)
    payload = session.as_dict()

    assert payload["schema_version"] == "1.0"
    assert payload["items"][0]["decision"] == "accepted"
    assert payload["items"][1]["decision"] == "pending"
    assert payload["items"][0]["suggestion"] == "U.S.C."
