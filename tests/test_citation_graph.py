from __future__ import annotations

from autocite_mcp.citation_graph import build_citation_graph
from autocite_mcp.document_ir import parse_markdown_ir, parse_text_ir
from autocite_mcp.tools import get_citation_graph, resolve_short_form


def _graph(text: str, mode: str = "bluepages"):
    return build_citation_graph(parse_text_ir(text), mode=mode)


def _resolution(graph, form: str, index: int = 0):
    matches = [result for result in graph.resolutions if result.form == form]
    return matches[index]


def test_valid_id_resolves_immediately_preceding_single_authority():
    graph = _graph("Smith v. Jones, 123 F.3d 456, 460 (9th Cir. 2020). Id. at 461.")
    result = _resolution(graph, "id")
    assert result.resolved_authority_id is not None
    assert result.resolution_method == "immediately_preceding_single_authority"
    assert result.confidence == "high"
    assert result.human_review_required is False


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
