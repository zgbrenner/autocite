import pytest

from autocite_mcp.evidence import (
    HybridPassageScorer,
    LexicalPassageScorer,
    analyze_case_evidence,
    extract_nearby_quotes,
    extract_proposition,
    match_quote,
    rank_passages,
    resolve_default_passage_scorer,
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
    # Default path is unchanged: the lexical scorer, disclosed provenance, no fallback noise.
    assert result["proposition"]["scorer"] == "lexical"
    assert result["provenance"]["proposition"] == "lexical_candidate_ranking_only"


_SAMPLE_SOURCE = (
    "Standing requires an injury in fact. "
    "The right to marry is fundamental because it is inherent in individual autonomy. "
    "The judgment is affirmed."
)


class _FakeEmbeddingBackend:
    """Deterministic stand-in for a sentence-transformers bi-encoder; needs no torch/model."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def encode(self, texts):
        self.calls.append(list(texts))
        # Deterministic 2D "embedding": presence of two marker words. No external dependency.
        return [
            [1.0 if "marry" in text.lower() else 0.0, 1.0 if "affirmed" in text.lower() else 0.0]
            for text in texts
        ]


class _RaisingEmbeddingBackend:
    """Simulates an unavailable local embedding model (missing dependency or uncached model)."""

    def encode(self, texts):
        raise RuntimeError("model not cached locally")


def test_default_lexical_scorer_is_unchanged():
    ranked = rank_passages("The right to marry is fundamental", _SAMPLE_SOURCE, limit=2)
    assert ranked[0]["passage"].startswith("The right to marry")
    assert ranked[0]["scorer"] == "lexical"
    assert ranked[0]["method"] == "token_jaccard_65_percent_plus_sequence_match_35_percent"
    assert ranked[0]["combined_score"] == ranked[0]["lexical_score"]
    assert "embedding_similarity" not in ranked[0]
    assert ranked[0]["combined_score"] == pytest.approx(
        ranked[0]["token_overlap"] * 0.65 + ranked[0]["sequence_similarity"] * 0.35, abs=1e-3
    )


def test_hybrid_scorer_blends_injected_fake_embedding_backend():
    backend = _FakeEmbeddingBackend()
    scorer = HybridPassageScorer(embedding_backend=backend)
    ranked = rank_passages("The right to marry is fundamental", _SAMPLE_SOURCE, limit=3, scorer=scorer)
    assert ranked
    for item in ranked:
        assert item["scorer"] == "hybrid_local_embedding"
        assert item["method"] == "hybrid_lexical_50_percent_plus_local_embedding_cosine_50_percent"
        assert item["combined_score"] == pytest.approx(
            item["lexical_score"] * 0.5 + item["embedding_similarity"] * 0.5, abs=1e-6
        )
    # The marriage passage scores highest on both the lexical and the fake embedding signal.
    assert "marry" in ranked[0]["passage"].lower()
    # The backend is invoked once, with the proposition first and then every passage window.
    assert len(backend.calls) == 1
    assert backend.calls[0][0] == "The right to marry is fundamental"


def test_hybrid_scorer_falls_back_to_lexical_when_backend_raises():
    scorer = HybridPassageScorer(embedding_backend=_RaisingEmbeddingBackend())
    ranked = rank_passages("The right to marry is fundamental", _SAMPLE_SOURCE, scorer=scorer)
    assert ranked
    for item in ranked:
        assert item["scorer"] == "lexical_fallback_hybrid_unavailable"
        assert item["method"] == "token_jaccard_65_percent_plus_sequence_match_35_percent"
        assert item["combined_score"] == item["lexical_score"]
        assert "model not cached locally" in item["fallback_reason"]


def test_hybrid_scorer_never_raises_even_when_backend_is_broken():
    scorer = HybridPassageScorer(embedding_backend=_RaisingEmbeddingBackend())
    # This must not raise -- graceful degradation is mandatory.
    rank_passages("anything", _SAMPLE_SOURCE, scorer=scorer)


def test_resolve_default_passage_scorer_reads_env_var(monkeypatch):
    monkeypatch.delenv("AUTOCITE_PASSAGE_SCORER", raising=False)
    assert isinstance(resolve_default_passage_scorer(), LexicalPassageScorer)

    monkeypatch.setenv("AUTOCITE_PASSAGE_SCORER", "hybrid")
    scorer = resolve_default_passage_scorer()
    assert isinstance(scorer, HybridPassageScorer)

    monkeypatch.setenv("AUTOCITE_PASSAGE_SCORER", "LEXICAL")
    assert isinstance(resolve_default_passage_scorer(), LexicalPassageScorer)

    monkeypatch.setenv("AUTOCITE_PASSAGE_SCORER", "not-a-real-choice")
    with pytest.raises(ValueError, match="AUTOCITE_PASSAGE_SCORER"):
        resolve_default_passage_scorer()


def test_case_evidence_reports_hybrid_scorer_and_provenance():
    scorer = HybridPassageScorer(embedding_backend=_FakeEmbeddingBackend())
    result = analyze_case_evidence(
        document_text='The Court said “the right to marry is fundamental.” 576 U.S. 644, 675 (2015).',
        citation_start=57,
        citation_text="576 U.S. 644, 675 (2015)",
        source_text="*675 The right to marry is fundamental under the Constitution.",
        pincite="675",
        passage_scorer=scorer,
    )
    assert result["proposition"]["scorer"] == "hybrid_local_embedding"
    assert result["provenance"]["proposition"] == "hybrid_lexical_and_local_embedding_candidate_ranking"
    assert result["proposition"]["candidate_passages"][0]["scorer"] == "hybrid_local_embedding"
    assert result["proposition"]["requires_legal_judgment"] is True
    assert result["proposition"]["conclusion"] == "not_determined"


def test_case_evidence_reports_lexical_fallback_when_hybrid_backend_unavailable():
    scorer = HybridPassageScorer(embedding_backend=_RaisingEmbeddingBackend())
    result = analyze_case_evidence(
        document_text='The Court said “the right to marry is fundamental.” 576 U.S. 644, 675 (2015).',
        citation_start=57,
        citation_text="576 U.S. 644, 675 (2015)",
        source_text="*675 The right to marry is fundamental under the Constitution.",
        pincite="675",
        passage_scorer=scorer,
    )
    assert result["proposition"]["scorer"] == "lexical_fallback_hybrid_unavailable"
    assert result["provenance"]["proposition"] == "lexical_candidate_ranking_only_hybrid_scorer_unavailable_fallback"
    assert result["proposition"]["candidate_passages"][0]["fallback_reason"]
