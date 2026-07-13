import pytest

from autocite_mcp.tools import (
    check_citations,
    check_single_citation,
    convert_citation,
    explain_issue,
    list_capabilities,
)


def test_check_single_citation_returns_focused_report():
    result = check_single_citation("42 USC §1983", mode="bluepages")
    assert result["citation"]["source_type"] == "statute"
    assert result["suggested_citation"] == "42 U.S.C. § 1983"


def test_check_single_citation_rejects_multiple_citations():
    with pytest.raises(ValueError, match="exactly one"):
        check_single_citation("42 U.S.C. § 1983 and 17 C.F.R. § 240.10b-5")


def test_convert_case_citation_to_bluepages_markdown():
    result = convert_citation(
        "Obergefell v. Hodges, 576 U.S. 644, 675 (2015)",
        target_mode="bluepages",
        output_style="markdown",
    )
    assert result["converted"] == "*Obergefell v. Hodges*, 576 U.S. 644, 675 (2015)"


def test_convert_state_statute_without_fabricating_title():
    result = convert_citation(
        "Mass. Gen. Laws ch. 1, § 2 (West 1999)",
        target_mode="whitepages",
    )
    assert result["converted"] == "Mass. Gen. Laws ch. 1, § 2 (West 1999)"


def test_explain_issue_returns_mode_specific_rule():
    result = explain_issue("REPORTER_ABBREVIATION", mode="whitepages")
    assert result["rule"] == "Rule 10"


def test_capabilities_disclose_verification_limits():
    result = list_capabilities()
    assert "case" in result["verification"]["courtlistener_supports"]
    assert "statutes" in result["verification"]["courtlistener_does_not_support"]


def test_check_citations_can_apply_safe_fixes():
    result = check_citations("42 USC §1983", mode="bluepages", apply_safe_fixes=True)
    assert result["fixed_text"] == "42 U.S.C. § 1983"


@pytest.mark.asyncio
async def test_review_document_is_primary_model_friendly_workflow():
    from autocite_mcp.tools import review_document

    result = await review_document(
        "IN THE DISTRICT COURT\nSee 42 USC §1983. Id",
        document_type="auto",
        apply_safe_fixes=True,
    )
    assert result["mode_detection"]["mode"] == "bluepages"
    assert result["corrected_text"] == "IN THE DISTRICT COURT\nSee 42 U.S.C. § 1983. Id."
    assert result["knowledge"]["mode"] == "bluepages"
    assert result["response_contract"][0].startswith("Use corrected_text")
    assert result["mechanical_review_complete"] is True
    assert result["completion_scope"] == "detected citation-format issues only"


def test_get_citation_guidance_for_single_source():
    from autocite_mcp.tools import get_citation_guidance

    result = get_citation_guidance(mode="whitepages", source_type="journal_article")
    assert result["mode"] == "whitepages"
    assert set(result["sources"]) == {"journal_article"}
