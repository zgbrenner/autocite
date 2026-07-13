import pytest

from autocite_mcp.formatters import generate_citation


def test_generates_practitioner_case_citation_in_markdown():
    citation = generate_citation(
        "case",
        {
            "case_name": "Obergefell v. Hodges",
            "volume": "576",
            "reporter": "U.S.",
            "first_page": "644",
            "pincite": "675",
            "year": "2015",
        },
        mode="bluepages",
        output_style="markdown",
    )
    assert citation == "*Obergefell v. Hodges*, 576 U.S. 644, 675 (2015)"


def test_generates_whitepages_journal_citation():
    citation = generate_citation(
        "journal_article",
        {
            "author": "Jane Smith",
            "title": "A Theory of Citation",
            "volume": "99",
            "journal": "Yale L.J.",
            "first_page": "101",
            "pincite": "120",
            "year": "2026",
        },
        mode="whitepages",
    )
    assert citation == "Jane Smith, A Theory of Citation, 99 Yale L.J. 101, 120 (2026)"


def test_missing_required_fields_are_reported_not_invented():
    with pytest.raises(ValueError, match="first_page"):
        generate_citation(
            "case",
            {
                "case_name": "Example v. Example",
                "volume": "1",
                "reporter": "U.S.",
                "year": "2026",
            },
            mode="bluepages",
        )


def test_generates_statute_with_section_symbol_spacing():
    citation = generate_citation(
        "statute",
        {"title": "42", "code": "U.S.C.", "section": "1983", "year": "2018"},
        mode="bluepages",
    )
    assert citation == "42 U.S.C. § 1983 (2018)"
