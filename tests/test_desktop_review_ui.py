from __future__ import annotations

from autocite_mcp.desktop_review_ui import review_item_details, review_item_label
from autocite_mcp.review_session import ReviewDecision, ReviewSession


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
        }
    ],
    "remaining_issues": [
        {
            "code": "PROPOSITION_PINCITE_REVIEW",
            "start": 20,
            "end": 25,
            "original": "Smith",
            "message": "Review whether this proposition requires a pinpoint citation.",
            "correction_level": "review_required",
            "confidence": "medium",
            "severity": "warning",
            "provenance": "deterministic_logic",
            "source_type": "case",
            "rule": "B10",
            "missing_facts": ["pinpoint page"],
        }
    ],
    "rule_findings": [],
}


def test_ui_module_imports_without_pyside_until_workspace_launch():
    session = ReviewSession.from_result(RESULT)
    assert session.items


def test_review_item_label_exposes_decision_status_and_issue_code():
    item = ReviewSession.from_result(RESULT).items[0]

    label = review_item_label(item)

    assert "Accepted" in label
    assert "Safe mechanical change" in label
    assert "STATUTE_CODE_ABBREVIATION" in label


def test_review_item_details_exposes_source_range_provenance_and_missing_facts():
    item = next(
        item
        for item in ReviewSession.from_result(RESULT).items
        if item.decision is ReviewDecision.PENDING
    )

    details = review_item_details(item)

    assert "Characters 20 through 25" in details
    assert "Source type: case" in details
    assert "Rule family: B10" in details
    assert "Missing facts: pinpoint page" in details
    assert "Provenance: deterministic_logic" in details
    assert "Accept marks this review item resolved" in details
