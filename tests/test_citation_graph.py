from __future__ import annotations

from autocite_mcp.citation_graph import build_citation_graph
from autocite_mcp.document_ir import parse_markdown_ir, parse_text_ir
from autocite_mcp.tools import get_citation_graph, resolve_short_form


def _graph(text: str, mode: str = "bluepages"):
    return build_citation_graph(parse_text_ir(text), mode=mode)


def _resolution(graph, form: str, index: int = 0):
    matches = [result for result in graph.resolutions if result.form == form]
    return matches[index]


def test_pairwise_edge_building_breaks_early_instead_of_scanning_every_pair():
    # citation_graph.py's same_citation_sentence/same_citation_clause
    # edge-builder previously compared every occurrence against every
    # OTHER occurrence in the whole document (full O(n^2)), independent of
    # proximity. A citation-dense document (a real brief's table of
    # authorities, or an adversarial one) could take tens of seconds on top
    # of citation extraction's own cost.
    #
    # Wall-clock timing is too noisy to assert reliably at the small scales
    # a fast test suite can afford (extraction itself, a third-party
    # eyecite call, has its own separate O(n^2) confound this fix doesn't
    # touch). Instead, deterministically count how many times the
    # sentence-break regex actually runs. Each "sentence" below has 3
    # citations separated by ";" (so `";" in gap` -- the first half of the
    # original `and` condition -- stays true across a growing gap, meaning
    # the sentence-break regex is genuinely exercised for every pair rather
    # than short-circuited away): the fixed algorithm must stop scanning
    # once it crosses into the next sentence rather than continuing to
    # compare against every one of the far-away occurrences that follow,
    # which a real string cite followed by ordinary prose forces the old
    # code to keep doing for every citation near the start of each sentence.
    from unittest.mock import patch

    n_groups = 60
    group = (
        "CaseA v. X, 1 F.3d 1 (2020); CaseB v. Y, 2 F.3d 2 (2020); "
        "CaseC v. Z, 3 F.3d 3 (2020). "
    )
    text = group * n_groups
    ir = parse_text_ir(text)

    with patch("autocite_mcp.citation_graph.re.search", wraps=__import__("re").search) as spy:
        build_citation_graph(ir)

    # Measured: ~1,140 calls with the early break, ~16,800 without it (a
    # true O(n^2) scan) for this input (180 citations across 60
    # sentence-groups of 3). Threshold set well between the two, with
    # headroom for re.search's other (linear) call sites in the same
    # function, while still clearly catching a regression to the full scan.
    assert spy.call_count < 4000, f"sentence-break regex called {spy.call_count} times"


def test_same_citation_sentence_edges_match_full_pairwise_scan_on_realistic_text():
    # Verifies the early-break optimization (stop once a sentence break
    # appears in the gap, since the gap only grows and can never lose that
    # break) produces the exact same edges a full O(n^2) pairwise scan
    # would, not just "doesn't crash" -- confirmed independently by diffing
    # against the pre-optimization implementation's output on this input.
    text = (
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020); Doe v. State, 456 F.3d 789 (9th Cir. 2021). "
        "See also Brown v. Board, 347 U.S. 483 (1954); Roe v. Wade, 410 U.S. 113 (1973); "
        "Obergefell v. Hodges, 576 U.S. 644 (2015). "
        "The court explained the reasoning at length before turning to the merits."
    )
    graph = _graph(text)
    sentence_edges = {
        (edge.source_id, edge.target_id)
        for edge in graph.edges
        if edge.edge_type == "same_citation_sentence"
    }
    assert sentence_edges == {
        ("occurrence:0000", "occurrence:0001"),
        ("occurrence:0002", "occurrence:0003"),
        ("occurrence:0003", "occurrence:0004"),
    }


def test_same_citation_sentence_edge_survives_footnote_position_reordering():
    # Regression: occurrence_nodes is ordered by _logical_key, which
    # relocates a footnote's citations to their reference marker's position
    # in the body -- not their own .start -- so occurrence_nodes is NOT
    # sorted by textual position whenever a footnote is present. The
    # sentence-edge early break previously assumed occurrence_nodes order
    # was textual order, so once it hit the footnote-relocated occurrence
    # (whose true .start is far away, near the end of the document) it saw
    # a fabricated sentence break spanning the whole document and stopped
    # scanning -- silently losing the genuinely adjacent Smith/Doe pair,
    # separated only by "; [1] " in the body text.
    text = (
        "See Smith v. Jones, 123 F.3d 456 (9th Cir. 2020);[1] Doe v. State, 456 F.3d 789 (9th Cir. 2021). "
        "The panel then turned to the remedy.\n\n"
        "[1] See Brown v. Board, 347 U.S. 483 (1954)."
    )
    ir = parse_text_ir(text)
    graph = build_citation_graph(ir)
    starts = {occ.occurrence_id: occ.start for occ in graph.occurrences}
    smith_id = next(oid for oid, start in starts.items() if start == 4)
    doe_id = next(oid for oid, start in starts.items() if start == 53)
    sentence_edges = {
        (edge.source_id, edge.target_id)
        for edge in graph.edges
        if edge.edge_type == "same_citation_sentence"
    }
    assert (smith_id, doe_id) in sentence_edges


def test_zero_width_characters_do_not_hide_a_short_form_citation():
    # _raw_occurrences' custom short-form patterns (Id./supra/etc.) and the
    # statutory-short/hereinafter scans all matched directly against
    # ir.text, unaffected by CitationEngine.extract's own fix -- an
    # invisible character inside "Id." made the whole short form invisible
    # to citation_graph too.
    text = (
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020). "
        "Id.​ at 460."
    )
    graph = _graph(text)
    ids = [occ for occ in graph.occurrences if occ.form == "id"]
    assert len(ids) == 1


def test_valid_id_resolves_immediately_preceding_single_authority():
    graph = _graph("Smith v. Jones, 123 F.3d 456, 460 (9th Cir. 2020). Id. at 461.")
    result = _resolution(graph, "id")
    assert result.resolved_authority_id is not None
    assert result.resolution_method == "immediately_preceding_single_authority"
    assert result.confidence == "high"
    assert result.human_review_required is False


def test_chained_id_resolves_through_prior_resolved_id():
    graph = _graph("Smith v. Jones, 410 U.S. 113 (1973). Id. at 115. Id. at 116.")
    first, second = (
        result for result in graph.resolutions if result.form == "id"
    )
    assert first.resolved_authority_id is not None
    assert second.resolved_authority_id == first.resolved_authority_id
    assert second.resolution_method == "immediately_preceding_single_authority"
    assert second.human_review_required is False


def test_chained_id_stays_unresolved_when_prior_id_is_ambiguous():
    graph = _graph(
        "See Smith v. Jones, 123 F.3d 456 (9th Cir. 2020); "
        "Doe v. State, 456 F.3d 789 (9th Cir. 2021). Id. at 790. Id. at 791."
    )
    first, second = (
        result for result in graph.resolutions if result.form == "id"
    )
    assert first.resolved_authority_id is None
    assert second.resolved_authority_id is None
    assert "no_immediately_preceding_authority" in second.disqualifying_facts


def test_id_after_multi_authority_group_abstains():
    graph = _graph(
        "See Smith v. Jones, 123 F.3d 456 (9th Cir. 2020); "
        "Doe v. State, 456 F.3d 789 (9th Cir. 2021). Id. at 790."
    )
    result = _resolution(graph, "id")
    assert result.resolved_authority_id is None
    assert "preceding_citation_group_has_multiple_authorities" in result.disqualifying_facts
    assert result.human_review_required is True


def test_id_with_intervening_citation_clause_is_not_back_resolved():
    graph = _graph(
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020). "
        "See 42 U.S.C. § 1983; Id. at 460."
    )
    result = _resolution(graph, "id")
    assert result.resolved_authority_id is None
    assert any("multiple" in fact or "intervening" in fact for fact in result.disqualifying_facts)


def test_multiple_authorities_in_one_footnote_make_id_ambiguous():
    ir = parse_markdown_ir(
        "Claim.[^1]\n\n[^1]: Smith v. Jones, 123 F.3d 456 (9th Cir. 2020); "
        "Doe v. State, 456 F.3d 789 (9th Cir. 2021). Id. at 790."
    )
    result = _resolution(build_citation_graph(ir, mode="whitepages"), "id")
    assert result.resolved_authority_id is None
    assert result.human_review_required is True


def test_statutory_short_form_resolves_when_document_has_single_code():
    graph = _graph(
        "26 U.S.C. § 501 provides an exemption. Later, § 501 was construed narrowly."
    )
    result = _resolution(graph, "statutory_short")
    assert result.resolved_authority_id is not None
    assert result.resolution_method == "prior_full_statutory_authority"


def test_statutory_short_form_stays_ambiguous_across_two_codes_same_section():
    graph = _graph(
        "26 U.S.C. § 501 provides an exemption. "
        "12 C.F.R. § 501 covers something else. Later, § 501 was construed narrowly."
    )
    result = _resolution(graph, "statutory_short")
    assert result.resolved_authority_id is None
    assert "multiple_plausible_statutory_antecedents" in result.disqualifying_facts


def test_statutory_short_form_code_hint_disambiguates_two_codes_same_section():
    graph = _graph(
        "26 U.S.C. § 501 provides an exemption. "
        "12 C.F.R. § 501 covers something else. Later, U.S.C. § 501 was construed narrowly."
    )
    result = _resolution(graph, "statutory_short")
    assert result.resolved_authority_id is not None
    usc_authority = next(
        authority for authority in graph.authorities if authority.components.get("code") == "U.S.C."
    )
    assert result.resolved_authority_id == usc_authority.authority_id


def test_short_case_pincite_range_accepts_em_dash():
    graph = _graph(
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020). Smith, 123 F.3d at 460—465."
    )
    matches = [item for item in graph.occurrences if item.form == "short_case"]
    assert matches[0].components["pincite"] == "460—465"


def test_supra_note_pincite_range_accepts_hyphen_and_em_dash():
    hyphen = _graph(
        "Jane Author, Useful Article, 12 Example L. Rev. 100 (2020). "
        "Author, supra note 1, at 12-15."
    )
    hyphen_match = [item for item in hyphen.occurrences if item.form == "supra_note"][0]
    assert hyphen_match.citation_text.endswith("at 12-15")

    em_dash = _graph(
        "Jane Author, Useful Article, 12 Example L. Rev. 100 (2020). "
        "Author, supra note 1, at 12—15."
    )
    em_dash_match = [item for item in em_dash.occurrences if item.form == "supra_note"][0]
    assert em_dash_match.citation_text.endswith("at 12—15")


def test_supra_pincite_range_accepts_em_dash():
    graph = _graph(
        "Jane Author, Useful Article, 12 Example L. Rev. 100 (2020). "
        "Author, supra, at 12—15.",
        mode="whitepages",
    )
    supra_match = [item for item in graph.occurrences if item.form == "supra"][0]
    assert supra_match.citation_text.endswith("at 12—15")


def test_case_short_form_can_resolve_past_unrelated_citation():
    graph = _graph(
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020). "
        "See 42 U.S.C. § 1983. Smith, 123 F.3d at 460."
    )
    result = _resolution(graph, "short_case")
    assert result.resolved_authority_id is not None
    assert result.resolution_method == "prior_full_case_exact_components"


def test_valid_article_supra_and_invalid_case_supra():
    article = _graph(
        "Jane Author, Useful Article, 12 Example L. Rev. 100 (2020). "
        "Author, supra, at 110.",
        mode="whitepages",
    )
    assert _resolution(article, "supra").resolved_authority_id is not None

    case = _graph(
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020). Smith, supra, at 460.",
        mode="whitepages",
    )
    invalid = _resolution(case, "supra")
    assert invalid.resolved_authority_id is None
    assert "source_type_does_not_permit_supra" in invalid.disqualifying_facts


def test_supra_note_resolves_one_source_and_abstains_for_multiple_sources():
    one = parse_markdown_ir(
        "Claim.[^1]\n\nLater, Author, supra note 1, at 110.\n\n"
        "[^1]: Jane Author, Useful Article, 12 Example L. Rev. 100 (2020)."
    )
    one_result = _resolution(build_citation_graph(one, mode="whitepages"), "supra_note")
    assert one_result.resolved_authority_id is not None

    many = parse_markdown_ir(
        "Claim.[^1]\n\nLater, Author, supra note 1.\n\n"
        "[^1]: Jane Author, Useful Article, 12 Example L. Rev. 100 (2020); "
        "John Writer, Other Article, 13 Example L. Rev. 200 (2021)."
    )
    many_result = _resolution(build_citation_graph(many, mode="whitepages"), "supra_note")
    assert many_result.resolved_authority_id is None
    assert len(many_result.candidates) >= 2
    assert many_result.human_review_required is True


def test_supra_note_resolves_through_plain_text_ir_markdown_footnote():
    # review_document (not editable from tests) always parses documents with
    # parse_text_ir, never parse_markdown_ir, so this exact end-to-end path
    # -- markdown-style "[^1]:" footnotes fed through parse_text_ir -- is
    # what production actually exercises. A single permitted authority in
    # the referenced footnote must resolve.
    one = _graph(
        "Claim.[^1]\nLater, Author, supra note 1.\n\n"
        "[^1]: Jane Author, First Article, 12 Example L. Rev. 100 (2020).",
        mode="whitepages",
    )
    one_result = _resolution(one, "supra_note")
    assert one_result.resolved_authority_id is not None
    assert one_result.resolution_method == "single_permitted_authority_in_referenced_note"
    assert one_result.human_review_required is False

    # A footnote with two authorities must stay ambiguous rather than
    # silently picking one -- this is what corpus doc dev-supra-note-01
    # encodes (ambiguous_short_forms == 1).
    many = _graph(
        "Claim.[^1]\nLater, Author, supra note 1.\n\n"
        "[^1]: Jane Author, First Article, 12 Example L. Rev. 100 (2020); "
        "John Writer, Second Article, 13 Example L. Rev. 200 (2021).",
        mode="whitepages",
    )
    many_result = _resolution(many, "supra_note")
    assert many_result.resolved_authority_id is None
    assert "referenced_note_has_multiple_authorities" in many_result.disqualifying_facts
    assert many_result.human_review_required is True


def test_distant_repeated_source_resolves_only_from_prior_occurrences():
    ir = parse_markdown_ir(
        "First.[^1]\n\nMiddle.[^2]\n\nDisputed, Author, supra note 1.\n\n"
        "[^1]: Jane Author, Useful Article, 12 Example L. Rev. 100 (2020).\n\n"
        "[^2]: 42 U.S.C. § 1983."
    )
    result = _resolution(build_citation_graph(ir, mode="whitepages"), "supra_note")
    assert result.resolved_authority_id is not None


def test_later_full_citation_never_retroactively_validates_earlier_short_form():
    graph = _graph(
        "Smith, 123 F.3d at 460. "
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)."
    )
    result = _resolution(graph, "short_case")
    assert result.resolved_authority_id is None
    assert result.candidates == ()
    assert "no_legally_possible_prior_antecedent" in result.disqualifying_facts
    assert any(edge.edge_type == "later_consistency_match" for edge in graph.edges)


def test_public_graph_and_resolution_contracts_are_serializable():
    text = "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020). Id. at 460."
    graph = get_citation_graph(text)
    resolution = resolve_short_form(text)

    assert graph["version"] == "1.0"
    assert graph["authorities"]
    assert graph["occurrences"]
    assert resolution["schema_version"] == "1.0"
    assert resolution["resolutions"][0]["human_review_required"] is False


def test_hereinafter_definition_and_later_use_are_linked():
    graph = _graph(
        'Jane Author, Useful Article, 12 Example L. Rev. 100 (2020) '
        '(hereinafter "Useful Article"). Useful Article, at 110.'
    )
    result = _resolution(graph, "hereinafter")
    assert result.resolution_method == "prior_hereinafter_definition"
    assert result.resolved_authority_id is not None
    assert any(edge.edge_type == "hereinafter_to_antecedent" for edge in graph.edges)


def test_hereinafter_resolves_for_an_eyecite_recognized_case_citation():
    # "12 Example L. Rev. 100" above isn't a reporter eyecite's own matcher
    # recognizes, so extraction falls back to AutoCite's own regex, which
    # never exercises eyecite's full_span() -- that's the standard path for
    # any real case citation, so it needs its own coverage. Without trimming
    # the trailing hereinafter clause out of the citation's own span (see
    # extractors._trim_trailing_hereinafter), full_span() absorbs the
    # "(hereinafter ...)" parenthetical into the citation itself, so the
    # citation's end lands past where the hereinafter clause starts and the
    # alias is never registered.
    graph = _graph(
        'Smith v. Jones, 123 F.3d 456, 460 (9th Cir. 2020) '
        '(hereinafter "Smith Rule"). Later, the Smith Rule controls the outcome.'
    )
    result = _resolution(graph, "hereinafter")
    assert result.resolution_method == "prior_hereinafter_definition"
    assert result.resolved_authority_id is not None
    assert not result.disqualifying_facts


def test_id_resolution_follows_indigo_r15_3_prose_and_paragraph_semantics():
    # Indigo R15.3: Id. is barred by a preceding multi-source citation, not by
    # ordinary intervening prose. Prose that names another authority, or a
    # paragraph break, still requires human review.
    def last_resolution(text):
        graph = build_citation_graph(parse_text_ir(text))
        return graph.resolutions[-1]

    full = "Baxter v. Cole, 1044 F.3d 900 (7th Cir. 2015)."
    valid = last_resolution(f"{full} The court explained its reasoning at length. Id. at 905.")
    assert valid.resolved_authority_id is not None
    assert valid.human_review_required is False

    other_case = last_resolution(f"{full} Unlike Harmon v. Reyes, that case was narrow. Id. at 905.")
    assert other_case.resolved_authority_id is None
    assert "intervening_authority_reference" in other_case.disqualifying_facts

    paragraph = last_resolution(f"{full}\n\nA new paragraph begins here. Id. at 905.")
    assert paragraph.resolved_authority_id is None
    assert "intervening_paragraph_break" in paragraph.disqualifying_facts

    string_cite = last_resolution(
        f"{full[:-1]}; Doe v. Roe, 345 F.3d 1 (7th Cir. 2016). Id. at 905."
    )
    assert string_cite.resolved_authority_id is None
    assert "preceding_citation_group_has_multiple_authorities" in string_cite.disqualifying_facts


def test_year_then_proper_noun_prose_does_not_bar_id():
    # "In 2020 Congress amended the statute" names no authority; a year followed
    # by a capitalized word must not be mistaken for an intervening reporter
    # citation that would wrongly leave an unambiguous Id. unresolved.
    text = (
        "Smith v. Jones, 500 U.S. 100, 105 (1990). "
        "In 2020 Congress amended the statute. Id. at 106."
    )
    id_res = _graph(text).resolutions[-1]
    assert id_res.resolved_authority_id is not None
    assert "intervening_authority_reference" not in id_res.disqualifying_facts
