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
