from autocite_mcp.workspace import WORKSPACE_HTML, workspace_payload


def test_workspace_is_self_contained_and_interactive():
    assert "ui/notifications/tool-result" in WORKSPACE_HTML
    assert "Accept" in WORKSPACE_HTML
    assert "Reject" in WORKSPACE_HTML
    assert "Copy corrected text" in WORKSPACE_HTML
    assert "selectedText" in WORKSPACE_HTML
    assert "applied_edits" in WORKSPACE_HTML
    assert "<script src=" not in WORKSPACE_HTML


def test_workspace_payload_is_bounded_and_contains_side_by_side_text():
    review = {
        "mode": "bluepages",
        "original_text": "See 42 USC §1983.",
        "corrected_text": "See 42 U.S.C. § 1983.",
        "remaining_issues": [],
        "applied_edits": [
            {
                "code": "STATUTE_CODE_ABBREVIATION",
                "start": 4,
                "end": 15,
                "original": "42 USC §1983",
                "suggestion": "42 U.S.C. § 1983",
            }
        ],
        "deep_review_results": {"cases": []},
    }
    payload = workspace_payload(review)
    assert payload["summary"]["mode"] == "bluepages"
    assert payload["original_text"] == review["original_text"]
    assert payload["corrected_text"] == review["corrected_text"]


def test_workspace_payload_surfaces_rule_findings_alongside_remaining_issues():
    review = {
        "mode": "bluepages",
        "original_text": "text",
        "corrected_text": "text",
        "remaining_issues": [
            {
                "code": "CASE_PINCITE_REVIEW",
                "severity": "warning",
                "message": "Pincite recommended.",
                "rule": "R10.2",
                "start": 0,
                "end": 4,
                "original": "text",
            }
        ],
        "rule_findings": [
            {
                "issue_code": "QUOTATION_PINCITE_REQUIRED",
                "family": "quotations",
                "severity": "warning",
                "correction_level": "review_required",
                "confidence": "medium",
                "start": 10,
                "end": 20,
                "original": "text",
                "suggestion": None,
                "explanation": "A direct quotation needs a pincite.",
                "rule_profile": "bluepages",
                "rule_family_reference": "R10.2",
                "required_facts": [],
                "missing_facts": [],
            }
        ],
        "applied_edits": [],
        "deep_review_results": {"cases": []},
    }
    payload = workspace_payload(review)
    codes = {issue["code"] for issue in payload["issues"]}
    assert codes == {"CASE_PINCITE_REVIEW", "QUOTATION_PINCITE_REQUIRED"}
    assert payload["summary"]["remaining_issue_count"] == 2
    rule_finding_issue = next(
        issue for issue in payload["issues"] if issue["code"] == "QUOTATION_PINCITE_REQUIRED"
    )
    assert rule_finding_issue["message"] == "A direct quotation needs a pincite."
    assert rule_finding_issue["rule"] == "R10.2"
