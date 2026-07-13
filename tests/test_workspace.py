from autocite_mcp.workspace import WORKSPACE_HTML, workspace_payload


def test_workspace_is_self_contained_and_interactive():
    assert "ui/notifications/tool-result" in WORKSPACE_HTML
    assert "Accept" in WORKSPACE_HTML
    assert "Reject" in WORKSPACE_HTML
    assert "Copy corrected text" in WORKSPACE_HTML
    assert "<script src=" not in WORKSPACE_HTML


def test_workspace_payload_is_bounded_and_model_safe():
    review = {
        "mode": "bluepages",
        "corrected_text": "See 42 U.S.C. § 1983.",
        "remaining_issues": [],
        "applied_edits": [{"code": "STATUTE_CODE_ABBREVIATION"}],
        "deep_review_results": {"cases": []},
    }
    payload = workspace_payload(review)
    assert payload["summary"]["mode"] == "bluepages"
    assert payload["corrected_text"] == review["corrected_text"]
    assert "original_text" not in payload
