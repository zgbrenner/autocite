from autocite_mcp.evidence import (
    analyze_case_evidence,
    extract_nearby_quotes,
    extract_proposition,
    match_quote,
    rank_passages,
)


def test_extracts_proposition_before_citation():
    text = "The Constitution protects same-sex marriage. Obergefell v. Hodges, 576 U.S. 644, 675 (2015)."
    start = text.index("Obergefell")
    assert extract_proposition(text, start) == "The Constitution protects same-sex marriage."


def test_extracts_nearby_curly_quote():
    text = "The Court held that “the right to marry is fundamental.” 576 U.S. 644, 675 (2015)."
    start = text.index("576")
    assert extract_nearby_quotes(text, start) == ["the right to marry is fundamental."]


def test_quote_matching_exact_and_normalized():
    source = "The right to marry is fundamental under the Constitution."
    assert match_quote("The right to marry is fundamental", source)["status"] == "exact"
    normalized = match_quote("The  right to marry—is fundamental", source)
    assert normalized["status"] in {"normalized", "partial"}


def test_rank_passages_returns_transparent_scores():
    source = (
        "Standing requires an injury in fact. "
        "The right to marry is fundamental because it is inherent in individual autonomy. "
        "The judgment is affirmed."
    )
    ranked = rank_passages("The right to marry is fundamental", source, limit=2)
    assert ranked[0]["passage"].startswith("The right to marry")
    assert 0 <= ranked[0]["token_overlap"] <= 1
    assert 0 <= ranked[0]["sequence_similarity"] <= 1


def test_case_evidence_never_claims_legal_support():
    result = analyze_case_evidence(
        document_text='The Court said “the right to marry is fundamental.” 576 U.S. 644, 675 (2015).',
        citation_start=57,
        citation_text="576 U.S. 644, 675 (2015)",
        source_text="*675 The right to marry is fundamental under the Constitution.",
        pincite="675",
    )
    assert result["quotation"]["status"] in {"exact", "normalized", "partial"}
    assert result["pincite"]["status"] == "confirmed_by_page_marker"
    assert result["proposition"]["requires_legal_judgment"] is True
    assert result["proposition"]["conclusion"] == "not_determined"
