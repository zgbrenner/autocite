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


def test_whitepages_case_citation_still_italicizes_case_name_in_markdown():
    citation = generate_citation(
        "case",
        {
            "case_name": "Obergefell v. Hodges",
            "volume": "576",
            "reporter": "U.S.",
            "first_page": "644",
            "year": "2015",
        },
        mode="whitepages",
        output_style="markdown",
    )
    assert citation == "*Obergefell v. Hodges*, 576 U.S. 644 (2015)"


def test_whitepages_case_citation_still_italicizes_case_name_in_html():
    citation = generate_citation(
        "case",
        {
            "case_name": "Obergefell v. Hodges",
            "volume": "576",
            "reporter": "U.S.",
            "first_page": "644",
            "year": "2015",
        },
        mode="whitepages",
        output_style="html",
    )
    assert citation == "<i>Obergefell v. Hodges</i>, 576 U.S. 644 (2015)"


def test_whitepages_book_title_still_italicizes_in_html():
    citation = generate_citation(
        "book",
        {"author": "Jane Smith", "title": "A Treatise", "year": "2020"},
        mode="whitepages",
        output_style="html",
    )
    assert "<i>A Treatise</i>" in citation


def test_html_output_escapes_untrusted_case_name_fields():
    citation = generate_citation(
        "case",
        {
            "case_name": "<img src=x onerror=1>Foo v. Bar",
            "volume": "1",
            "reporter": "U.S.",
            "first_page": "1",
            "year": "2020",
        },
        mode="bluepages",
        output_style="html",
    )
    assert "<img" not in citation
    assert citation.startswith("<i>&lt;img src=x onerror=1&gt;Foo v. Bar</i>")


def test_plain_output_does_not_escape_fields():
    citation = generate_citation(
        "case",
        {
            "case_name": "O'Brien v. Bar",
            "volume": "1",
            "reporter": "U.S.",
            "first_page": "1",
            "year": "2020",
        },
        mode="bluepages",
        output_style="plain",
    )
    assert "O'Brien" in citation
    assert "&#x27;" not in citation
