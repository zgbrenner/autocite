from autocite_mcp.engine import CitationEngine


def test_extracts_multiple_legal_source_types():
    text = (
        "See Obergefell v. Hodges, 576 U.S. 644, 675 (2015); "
        "42 U.S.C. § 1983 (2018); and 17 C.F.R. § 240.10b-5 (2025). Id."
    )
    report = CitationEngine().analyze(text, mode="bluepages")
    kinds = {citation["source_type"] for citation in report["citations"]}
    assert {"case", "statute", "regulation", "short_form"}.issubset(kinds)


def test_zero_width_characters_do_not_hide_a_citation_from_extraction():
    # Zero-width/invisible Unicode characters (ZWSP, ZWNJ, ZWJ, word joiner)
    # render identically to a human reader whether present or not, but
    # previously broke both eyecite's and AutoCite's own regex tokenization
    # entirely -- a citation with these interspersed matched nothing at all.
    # Real in copy-pasted text (rich-text/PDF extraction artifacts), not
    # just adversarial input. Written with explicit \\uXXXX escapes (not
    # literal characters) so the test stays auditable.
    poisoned = (
        "Brown​ v.‌ Board‍ of Education, 347⁠ U.S. 483 (1954)."
    )
    matches = CitationEngine().extract(poisoned)
    assert len(matches) == 1
    case = matches[0]
    assert case.source_type == "case"
    # The span must be valid against the ORIGINAL (unsanitized) text: the
    # citation's own reported text, with spaces put back where the
    # neutralized invisible characters were, must equal what's literally at
    # that span in the original string.
    original_slice = poisoned[case.start : case.end]
    assert original_slice.translate(
        {0x200B: " ", 0x200C: " ", 0x200D: " ", 0x2060: " "}
    ) == case.text


def test_zero_width_characters_do_not_block_a_safe_fix_from_applying():
    # extract() finding the citation is necessary but not sufficient --
    # _lint does its own separate regex matching and previously still
    # failed silently even after extraction was fixed, so no fix was ever
    # applied to a citation containing an invisible character.
    poisoned = "42 USC​ § 1983."
    result = CitationEngine().fix(poisoned)
    assert result["applied_edits"]
    assert result["applied_edits"][0]["code"] == "STATUTE_CODE_ABBREVIATION"
    assert "U.S.C." in result["fixed_text"]


def test_regulation_citation_with_letter_embedded_subsection_is_not_truncated():
    # eyecite's law-citation matcher stops at the digit-letter boundary in
    # "240.10b-5" and returns a truncated FullLawCitation ("17 C.F.R. §
    # 240"); its span then blocks the engine's fallback regex from ever
    # running over that region, so the truncation used to leak through to
    # extract().
    text = "The rule appears at 17 C.F.R. § 240.10b-5."
    citations = CitationEngine().extract(text)
    regulation = next(item for item in citations if item.source_type == "regulation")
    assert regulation.text == "17 C.F.R. § 240.10b-5"
    assert regulation.components["section"] == "240.10b-5"
    # The sentence-ending period must not be absorbed into the citation.
    assert text[regulation.end] == "."


def test_statute_citation_with_letter_embedded_subsection_is_not_truncated():
    text = "The rule appears at 29 U.S.C. § 216.10b-5."
    citations = CitationEngine().extract(text)
    statute = next(item for item in citations if item.source_type == "statute")
    assert statute.text == "29 U.S.C. § 216.10b-5"
    assert statute.components["section"] == "216.10b-5"
    assert text[statute.end] == "."


def test_malformed_regulation_citation_fixes_to_full_subsection_text():
    # Mirrors evals/system/documents.jsonl train-reg-01: the malformed
    # "17 CFR §240.10b-5" must both normalize its abbreviation *and* keep
    # the full subsection once re-extracted from the corrected text.
    text = "The rule appears at 17 CFR §240.10b-5."
    result = CitationEngine().fix(text, mode="bluepages")
    assert result["fixed_text"] == "The rule appears at 17 C.F.R. § 240.10b-5."
    report = CitationEngine().analyze(result["fixed_text"], mode="bluepages")
    regulation = next(
        item for item in report["citations"] if item["source_type"] == "regulation"
    )
    assert regulation["text"] == "17 C.F.R. § 240.10b-5"


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


def test_orphan_ibid_short_form_message_names_ibid_not_id():
    # eyecite classifies "Ibid." under the same IdCitation/"id" form as
    # "Id.", so it hits the same orphan-check branch -- found via real-world
    # document testing (a real SCOTUS opinion used house-style "Ibid."),
    # where the flagged message wrongly said "Id." must unambiguously refer
    # to..." even though the actual token was "Ibid.".
    report = CitationEngine().analyze("Ibid. at 12.", mode="whitepages")
    issue = next(item for item in report["issues"] if item["code"] == "SHORT_FORM_ORPHAN_ID")
    assert "Ibid." in issue["message"]
    assert "Id." not in issue["message"]


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


def test_california_in_line_citation_case_name_excludes_enclosing_parenthetical():
    # California's standard in-line citation form embeds the whole citation
    # inside a sentence parenthetical with the year directly after the case
    # name: "(Case v. Case (Year) Vol Rep Page.)". Found via real-world
    # document testing (a real Cal. Ct. App. opinion) -- the leading "("
    # and the embedded "(Year)" were both being swept into case_name.
    text = (
        "The rule is settled. (Steiner v. Superior Court (2013) "
        "220 Cal.App.4th 1479, 1485.) Liability follows accordingly."
    )
    citations = CitationEngine().extract(text)
    case = next(item for item in citations if item.source_type == "case")
    assert case.components["case_name"] == "Steiner v. Superior Court"
    assert case.components["year"] == "2013"


def test_year_metadata_is_not_trusted_when_absent_from_the_citations_own_text():
    # eyecite can leak a neighboring citation's year metadata onto the next
    # citation when the preceding one has a page-range plus pincite (e.g.
    # "215-423, 340"). Found via real-world document testing (a real SCOTUS
    # opinion): a citation plainly reading "(June 5, 1984)" was reported
    # with year "2022", leaked from an unrelated preceding citation.
    text = (
        "See 597 S. Ct. 215-423, 340 (June 24, 2022). "
        "See also United States v. Leon, 104 U.S. 897 (June 5, 1984)."
    )
    citations = CitationEngine().extract(text)
    cases = [item for item in citations if item.source_type == "case"]
    leon = next(item for item in cases if "Leon" in item.text)
    assert leon.components["year"] == "1984"


def test_full_date_parenthetical_is_not_misreported_as_a_court():
    # A citation parenthetical containing a full "Month Day, Year" date
    # (real in less-formal citations, e.g. quoting a slip opinion) has no
    # court abbreviation in it at all. Found via real-world document
    # testing: the date fragment "June 24," was being reported as the
    # `court` component.
    text = "See generally 597 S. Ct. 215, 340 (June 24, 2022)."
    citations = CitationEngine().extract(text)
    case = next(item for item in citations if item.source_type == "case")
    assert "court" not in case.components
    assert case.components["year"] == "2022"


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


def test_sentence_initial_id_in_prose_without_antecedent_is_left_alone():
    # "Id"/"id" opening a sentence is a citation short form only when a real
    # authority precedes it; ordinary prose (the Freudian id) must never be
    # rewritten to "Id." by the deterministic autofixer.
    text = (
        "The mind consists of the id, ego, and superego. "
        "Id represents primitive instinct in Freudian theory."
    )
    result = CitationEngine().fix(text, mode="whitepages")
    assert result["fixed_text"] == text
    assert result["applied_edits"] == []
    report = CitationEngine().analyze(text, mode="whitepages")
    assert not any(issue["code"].startswith("SHORT_FORM") for issue in report["issues"])


def test_orphaned_id_with_period_is_still_flagged_not_dropped():
    # A period-terminated "Id." with no antecedent is a genuine B4/Rule 4
    # defect and must still surface as SHORT_FORM_ORPHAN_ID, even though the
    # period-less prose "Id" in the same position would be left alone.
    text = (
        "This is an introduction with no citations at all in this paragraph "
        "whatsoever. Id. controls the outcome of this case."
    )
    report = CitationEngine().analyze(text, mode="bluepages")
    assert any(c["source_type"] == "short_form" for c in report["citations"])
    assert any(issue["code"] == "SHORT_FORM_ORPHAN_ID" for issue in report["issues"])


def test_eyecite_bare_id_without_citation_context_is_not_a_citation():
    # eyecite emits an IdCitation for a bare "id." even with no antecedent;
    # AutoCite must not treat "password id." as a legal short form.
    text = "Please enter your password id. in the field."
    report = CitationEngine().analyze(text, mode="bluepages")
    assert not any(c["source_type"] == "short_form" for c in report["citations"])
    assert not any(issue["code"].startswith("SHORT_FORM") for issue in report["issues"])


def test_spaced_period_reporter_is_recognized_and_normalized():
    text = "See 100 U . S . 200 (1990)."
    result = CitationEngine().fix(text, mode="bluepages")
    assert result["fixed_text"] == "See 100 U.S. 200 (1990)."


def test_bluepages_does_not_flag_unarchived_url():
    # INTERNET_ARCHIVE_REVIEW is a Whitepages-only rule; the same URL must not
    # be flagged in Bluepages mode.
    report = CitationEngine().analyze(
        "See https://example.com/legal-update.", mode="bluepages"
    )
    assert not any(
        issue["code"] == "INTERNET_ARCHIVE_REVIEW" for issue in report["issues"]
    )


def test_citation_dense_document_extracts_all_without_hanging():
    # Overlap resolution is O(n log n); a citation-dense document must extract
    # every authority quickly rather than degrading to a quadratic hang.
    text = " ".join(f"42 U.S.C. § {i}." for i in range(5000))
    citations = CitationEngine().extract(text)
    statutes = [c for c in citations if c.source_type == "statute"]
    assert len(statutes) == 5000


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
