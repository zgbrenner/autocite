from autocite_mcp.engine import CitationEngine


def test_extracts_multiple_legal_source_types():
    text = (
        "See Obergefell v. Hodges, 576 U.S. 644, 675 (2015); "
        "42 U.S.C. § 1983 (2018); and 17 C.F.R. § 240.10b-5 (2025). Id."
    )
    report = CitationEngine().analyze(text, mode="bluepages")
    kinds = {citation["source_type"] for citation in report["citations"]}
    assert {"case", "statute", "regulation", "short_form"}.issubset(kinds)


def test_fixes_safe_mechanical_errors_without_inventing_facts():
    text = "See 576 US 644 and 42 USC §1983. id."
    result = CitationEngine().fix(text, mode="bluepages")
    assert result["fixed_text"] == "See 576 U.S. 644 and 42 U.S.C. § 1983. Id."
    assert all(edit["confidence"] == "high" for edit in result["applied_edits"])


def test_bare_word_id_outside_citation_context_is_left_alone():
    text = "Users must enter their id before proceeding."
    result = CitationEngine().fix(text, mode="bluepages")
    assert result["fixed_text"] == text
    report = CitationEngine().analyze(text, mode="bluepages")
    assert not any(issue["code"] == "SHORT_FORM_CAPITALIZATION" for issue in report["issues"])
    assert not any(issue["code"] == "SHORT_FORM_ORPHAN_ID" for issue in report["issues"])


def test_id_with_signal_and_pincite_is_still_flagged_and_fixed():
    text = "Smith v. Jones, 410 U.S. 113 (1973). See id. at 5."
    result = CitationEngine().fix(text, mode="bluepages")
    assert result["fixed_text"] == "Smith v. Jones, 410 U.S. 113 (1973). See Id. at 5."


def test_id_comma_pincite_variant_is_still_flagged_and_fixed():
    text = "Smith v. Jones, 410 U.S. 113 (1973). id., at 100."
    result = CitationEngine().fix(text, mode="bluepages")
    assert result["fixed_text"] == "Smith v. Jones, 410 U.S. 113 (1973). Id., at 100."


def test_bare_federal_reporter_is_recognized_and_normalized():
    text = "126 f. 605 (2d Cir. 1903)"
    result = CitationEngine().fix(text, mode="bluepages")
    assert result["fixed_text"] == "126 F. 605 (2d Cir. 1903)"


def test_already_canonical_bare_federal_reporter_raises_no_issue():
    report = CitationEngine().analyze("126 F. 605 (2d Cir. 1903)", mode="bluepages")
    assert not any(issue["code"] == "REPORTER_ABBREVIATION" for issue in report["issues"])


def test_federal_reporter_suffixes_still_match():
    for citation in ("5 F.2d 100", "5 F.3d 100", "5 F. Supp. 100", "5 F. Supp. 2d 100"):
        report = CitationEngine().analyze(citation, mode="bluepages")
        assert not any(
            issue["code"] == "REPORTER_ABBREVIATION" for issue in report["issues"]
        ), citation


def test_flags_orphan_id_short_form():
    report = CitationEngine().analyze("Id. at 12.", mode="whitepages")
    assert any(issue["code"] == "SHORT_FORM_ORPHAN_ID" for issue in report["issues"])


def test_whitepages_flags_unarchived_bare_url():
    report = CitationEngine().analyze(
        "See https://example.com/legal-update.", mode="whitepages"
    )
    assert any(issue["code"] == "INTERNET_ARCHIVE_REVIEW" for issue in report["issues"])


def test_rejects_unknown_mode():
    try:
        CitationEngine().analyze("576 U.S. 644", mode="unknown")
    except ValueError as exc:
        assert "mode" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError")


def test_uses_eyecite_full_span_without_including_signal():
    text = (
        "See Brown v. Board of Education, 347 U.S. 483, 495 (1954). "
        "Id. at 496."
    )
    citations = CitationEngine().extract(text)
    case = next(item for item in citations if item.source_type == "case")
    short_form = next(item for item in citations if item.source_type == "short_form")

    assert case.text == "Brown v. Board of Education, 347 U.S. 483, 495 (1954)"
    assert case.start == 4
    assert case.components["case_name"] == "Brown v. Board of Education"
    assert short_form.text == "Id. at 496"
    assert short_form.components["resolved_to"] == case.components["resolved_to"]


def test_extracts_state_statute_and_supra_metadata():
    text = "Mass. Gen. Laws ch. 1, § 2 (West 1999). Foo, supra, at 5."
    citations = CitationEngine().extract(text)

    statute = next(item for item in citations if item.source_type == "statute")
    supra = next(item for item in citations if item.source_type == "short_form")

    assert statute.text == "Mass. Gen. Laws ch. 1, § 2 (West 1999)"
    assert statute.components["code"] == "Mass. Gen. Laws"
    assert statute.components["chapter"] == "1"
    assert statute.components["section"] == "2"
    assert supra.text == "Foo, supra, at 5"
    assert supra.components["form"] == "supra"
    assert supra.components["antecedent_guess"] == "Foo"


def test_extracts_state_reporter_case():
    text = "Smith v. Jones, 12 Cal. 5th 100, 105 (2022)."
    case = next(
        item for item in CitationEngine().extract(text) if item.source_type == "case"
    )
    assert case.components == {
        "case_name": "Smith v. Jones",
        "volume": "12",
        "reporter": "Cal. 5th",
        "first_page": "100",
        "pincite": "105",
        "year": "2022",
        "resolved_to": "resource-1",
    }
