from __future__ import annotations

from autocite_mcp.citation_graph import build_citation_graph
from autocite_mcp.deterministic_rules import (
    CORRECTION_LEVELS,
    RULE_SPECS,
    _MAX_BIDI_FINDINGS,
    evaluate_document_rules,
    parse_parentheticals,
    parse_signals,
    rule_coverage_matrix,
)
from autocite_mcp.document_ir import parse_text_ir


def _findings(text: str, mode: str = "bluepages"):
    ir = parse_text_ir(text)
    graph = build_citation_graph(ir, mode=mode)
    return evaluate_document_rules(ir, graph, mode=mode)


def test_every_rule_declares_complete_metadata():
    assert RULE_SPECS
    for code, spec in RULE_SPECS.items():
        assert spec.issue_code == code
        assert spec.bluepages_applicable or spec.whitepages_applicable
        assert spec.source_types
        assert spec.required_context
        assert spec.deterministic_conditions
        assert spec.severity in {"error", "warning", "info"}
        assert spec.correction_level in CORRECTION_LEVELS
        assert spec.original_rule_summary
        assert spec.rule_family_reference
        assert spec.explanation_template
        assert spec.test_cases


def test_ambiguous_id_is_review_required_and_never_autofixed():
    findings = _findings(
        "See Smith v. Jones, 123 F.3d 456 (9th Cir. 2020); "
        "Doe v. State, 456 F.3d 789 (9th Cir. 2021). Id. at 790."
    )
    finding = next(item for item in findings if item.issue_code == "ID_AMBIGUOUS_ANTECEDENT")
    assert finding.correction_level == "review_required"
    assert finding.suggestion is None
    assert finding.provenance == "deterministic_logic"


def test_case_and_statute_cannot_use_supra():
    findings = _findings(
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020). Smith, supra, at 460."
    )
    assert any(item.issue_code == "SUPRA_SOURCE_TYPE_PROHIBITED" for item in findings)


def test_signal_punctuation_is_mechanical_but_substantive_fit_is_not_decided():
    findings = _findings("Cf Smith v. Jones, 123 F.3d 456 (9th Cir. 2020).")
    finding = next(item for item in findings if item.issue_code == "SIGNAL_PUNCTUATION")
    assert not any("support" in item.explanation.lower() for item in findings)
    # Nothing in the codebase ever applies rule_findings to corrected_text
    # (evaluate_document_rules output is informational only), so this must
    # never claim safe_auto_fix -- see test_rule_findings_never_claim_an_unapplied_safe_auto_fix.
    assert finding.correction_level == "suggested_fix"


def test_rule_findings_never_claim_an_unapplied_safe_auto_fix():
    # contextual rule findings (evaluate_document_rules) are informational
    # only -- no code path applies them to corrected_text, so a rule spec
    # marked safe_auto_fix would falsely claim an edit was made. See
    # tools.py's response_contract ("Only high-confidence mechanical edits
    # are applied automatically") and README's identical guarantee.
    for spec in RULE_SPECS.values():
        assert spec.correction_level != "safe_auto_fix", (
            f"{spec.issue_code} is labeled safe_auto_fix but evaluate_document_rules "
            "findings are never applied to corrected_text"
        )


def test_bidi_override_characters_are_flagged_never_silently_applied():
    # Explicit Bidi override/embedding/pop-formatting characters (the
    # "Trojan Source" characters) can make text visually misrepresent its
    # own content -- e.g. digits inside a citation could display in a
    # different order than they're actually stored. Previously these
    # passed through into corrected_text completely unflagged; now they
    # must be surfaced as review_required, never silently stripped or
    # auto-applied (the tool's "never silently modify" principle), and
    # never confused with the newer, legitimate Bidi isolate characters.
    text = "347 U.S. ‮483‬ (1954)."
    findings = _findings(text)
    bidi_findings = [f for f in findings if f.issue_code == "BIDI_CONTROL_CHARACTER_PRESENT"]
    assert len(bidi_findings) == 2
    for finding in bidi_findings:
        assert finding.correction_level == "review_required"
        assert finding.suggestion is None

    isolates_only = "⁦347 U.S. 483⁩ (1954)."
    assert not any(
        f.issue_code == "BIDI_CONTROL_CHARACTER_PRESENT" for f in _findings(isolates_only)
    )


def test_bidi_findings_are_capped_with_a_summary_instead_of_one_per_character():
    # Regression: a hostile or corrupted document can carry many thousands
    # of Bidi control characters. Emitting one RuleFinding per occurrence
    # made this an unbounded output amplifier -- 500,000 characters in a
    # 1.5MB input produced 500,000 findings and ~300MB of serialized JSON,
    # remotely triggerable well under the 15MB document size limit. Findings
    # must now be capped, with any excess rolled into a single summary
    # finding rather than silently dropped.
    total_occurrences = _MAX_BIDI_FINDINGS + 30
    text = "‮" * total_occurrences
    findings = _findings(text)
    bidi_findings = [f for f in findings if f.issue_code == "BIDI_CONTROL_CHARACTER_PRESENT"]
    assert len(bidi_findings) == _MAX_BIDI_FINDINGS + 1
    summary = bidi_findings[-1]
    assert str(total_occurrences) in summary.explanation
    assert "30" in summary.explanation


def test_direct_quotation_without_pincite_requires_review():
    findings = _findings(
        'The court held that "the right is fundamental." Smith v. Jones, '
        "123 F.3d 456 (9th Cir. 2020)."
    )
    finding = next(item for item in findings if item.issue_code == "QUOTATION_PINCITE_REQUIRED")
    assert finding.correction_level == "review_required"
    assert finding.suggestion is None


def test_mode_profiles_remain_distinct_for_same_authority():
    text = "Materials are available at https://example.org/source."
    blue = _findings(text, "bluepages")
    white = _findings(text, "whitepages")
    assert not any(item.issue_code == "WHITEPAGES_ARCHIVE_REVIEW" for item in blue)
    assert any(item.issue_code == "WHITEPAGES_ARCHIVE_REVIEW" for item in white)


def test_coverage_matrix_discloses_partial_and_unsupported_families():
    matrix = rule_coverage_matrix()
    assert matrix["cases"]["status"] == "partial"
    assert matrix["ai_generated_materials"]["status"] == "unsupported"
    assert {entry["status"] for entry in matrix.values()} >= {"partial", "unsupported"}


def test_long_balanced_parenthetical_is_not_flagged_as_unbalanced():
    long_body = (
        "explaining that the holding rested on several independently "
        "sufficient grounds each fully briefed and argued at length by "
        "both parties over multiple rounds of supplemental briefing "
        "ordered by the court"
    )
    assert len(long_body) > 180
    text = (
        "Jane Author, Useful Article, 12 Example L. Rev. 100 (2020) "
        f"({long_body})."
    )
    findings = _findings(text, "whitepages")
    assert not any(item.issue_code == "PARENTHETICAL_SYNTAX" for item in findings)


def test_unbalanced_parenthetical_after_citation_is_still_flagged():
    text = (
        "Jane Author, Useful Article, 12 Example L. Rev. 100 "
        "(explaining a point that never closes its parenthetical."
    )
    findings = _findings(text, "whitepages")
    assert any(item.issue_code == "PARENTHETICAL_SYNTAX" for item in findings)


def test_signals_and_nested_parentheticals_are_structurally_parsed():
    signals = parse_signals("Compare A with B; but cf. C; see generally D.")
    assert [item.normalized for item in signals] == [
        "compare",
        "with",
        "but cf",
        "see generally",
    ]
    assert {item.group for item in signals} == {"comparative", "contrary", "supportive"}

    parentheticals = parse_parentheticals("(explaining X (quoting Y))")
    assert len(parentheticals) == 2
    assert all(item.balanced for item in parentheticals)
    assert max(item.depth for item in parentheticals) == 1


def test_scare_quoted_defined_term_is_not_treated_as_direct_quotation():
    # A single scare-quoted defined term is not a quotation of the cited
    # authority, so it must not escalate to the assertive QUOTATION_PINCITE_REQUIRED.
    findings = _findings(
        'The statute defines the term "employer" in Smith v. Jones, '
        "123 F.3d 456 (9th Cir. 2020)."
    )
    codes = {item.issue_code for item in findings}
    assert "QUOTATION_PINCITE_REQUIRED" not in codes
    assert "PROPOSITION_PINCITE_REVIEW" in codes


def test_cf_with_only_court_year_parenthetical_still_prompts_review():
    # A routine court/year parenthetical is citation metadata, not the
    # explanatory parenthetical cf. calls for, so the review flag must still fire.
    findings = _findings("Cf. Smith v. Jones, 123 F.3d 456 (9th Cir. 2020).")
    assert any(item.issue_code == "SIGNAL_PARENTHETICAL_REVIEW" for item in findings)


def test_cf_with_explanatory_parenthetical_is_not_flagged():
    findings = _findings(
        "Cf. Smith v. Jones, 123 F.3d 456 (9th Cir. 2020) "
        "(holding that the statute applies)."
    )
    assert not any(
        item.issue_code == "SIGNAL_PARENTHETICAL_REVIEW" for item in findings
    )


def test_cf_explanatory_parenthetical_ending_in_year_is_not_flagged():
    # A genuine explanatory parenthetical that merely ends in a year must not
    # be misread as bare court/year metadata and trigger a spurious review.
    findings = _findings(
        "Cf. Smith v. Jones, 123 F.3d 456 (9th Cir. 2000) "
        "(discussing the statute as amended in 2000)."
    )
    assert not any(
        item.issue_code == "SIGNAL_PARENTHETICAL_REVIEW" for item in findings
    )
