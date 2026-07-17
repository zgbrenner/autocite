import pytest

from autocite_mcp.deep_review import DeepReviewer
from autocite_mcp.evidence import HybridPassageScorer
from autocite_mcp.tools import review_document


class _FakeEmbeddingBackend:
    """Deterministic stand-in for a local bi-encoder; no sentence-transformers/torch needed."""

    def encode(self, texts):
        return [[1.0 if "marry" in text.lower() else 0.0] for text in texts]


class FakeSourceClient:
    def __init__(self):
        self.calls = 0

    async def lookup_and_fetch(self, text):
        self.calls += 1
        analysis_text = (
            "Unrelated procedural background. " * 600
            + "*675 The right to marry is fundamental under the Constitution."
        )
        return {
            "available": True,
            "provider": "CourtListener",
            "authorities": [
                {
                    "citation": "576 U.S. 644",
                    "normalized_citations": ["576 U.S. 644"],
                    "status": 200,
                    "case_name": "Obergefell v. Hodges",
                    "source_url": "https://www.courtlistener.com/opinion/2812209/obergefell-v-hodges/",
                    "analysis_text": analysis_text,
                    "source_text": analysis_text[:12_000],
                    "source_text_truncated": True,
                    "later_citation_metadata": {
                        "citation_count": 1000,
                        "classification": "not_a_citator",
                    },
                }
            ],
        }


@pytest.mark.asyncio
async def test_deep_reviewer_builds_evidence_records_from_full_opinion():
    text = 'The Court stated “the right to marry is fundamental.” Obergefell v. Hodges, 576 U.S. 644, 675 (2015).'
    citations = [
        {
            "source_type": "case",
            "text": "Obergefell v. Hodges, 576 U.S. 644, 675 (2015)",
            "start": text.index("Obergefell"),
            "end": len(text) - 1,
            "components": {"pincite": "675"},
        }
    ]
    result = await DeepReviewer(source_client=FakeSourceClient()).review(text, citations)
    case = result["cases"][0]
    assert result["available"] is True
    assert case["authority"]["case_name"] == "Obergefell v. Hodges"
    assert "analysis_text" not in case["authority"]
    assert case["evidence"]["quotation"]["status"] in {"exact", "normalized"}
    assert case["evidence"]["pincite"]["status"] == "confirmed_by_page_marker"
    assert case["evidence"]["proposition"]["requires_legal_judgment"] is True
    # Default passage ranking is unchanged: deterministic lexical scoring, no injected scorer.
    assert case["evidence"]["proposition"]["scorer"] == "lexical"


@pytest.mark.asyncio
async def test_deep_reviewer_accepts_injected_hybrid_passage_scorer_for_tests():
    text = 'The Court stated “the right to marry is fundamental.” Obergefell v. Hodges, 576 U.S. 644, 675 (2015).'
    citations = [
        {
            "source_type": "case",
            "text": "Obergefell v. Hodges, 576 U.S. 644, 675 (2015)",
            "start": text.index("Obergefell"),
            "end": len(text) - 1,
            "components": {"pincite": "675"},
        }
    ]
    scorer = HybridPassageScorer(embedding_backend=_FakeEmbeddingBackend())
    reviewer = DeepReviewer(source_client=FakeSourceClient(), passage_scorer=scorer)
    result = await reviewer.review(text, citations)
    evidence = result["cases"][0]["evidence"]
    assert evidence["proposition"]["scorer"] == "hybrid_local_embedding"
    assert evidence["proposition"]["candidate_passages"][0]["scorer"] == "hybrid_local_embedding"
    assert evidence["proposition"]["requires_legal_judgment"] is True


@pytest.mark.asyncio
async def test_deep_reviewer_falls_back_to_lexical_when_hybrid_backend_is_broken():
    class RaisingBackend:
        def encode(self, texts):
            raise RuntimeError("no locally cached model")

    text = 'The Court stated “the right to marry is fundamental.” Obergefell v. Hodges, 576 U.S. 644, 675 (2015).'
    citations = [
        {
            "source_type": "case",
            "text": "Obergefell v. Hodges, 576 U.S. 644, 675 (2015)",
            "start": text.index("Obergefell"),
            "end": len(text) - 1,
            "components": {"pincite": "675"},
        }
    ]
    scorer = HybridPassageScorer(embedding_backend=RaisingBackend())
    reviewer = DeepReviewer(source_client=FakeSourceClient(), passage_scorer=scorer)
    result = await reviewer.review(text, citations)
    evidence = result["cases"][0]["evidence"]
    assert evidence["proposition"]["scorer"] == "lexical_fallback_hybrid_unavailable"
    assert evidence["proposition"]["candidate_passages"][0]["fallback_reason"]


@pytest.mark.asyncio
async def test_primary_workflow_does_not_call_network_by_default(monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("network should not be called")

    monkeypatch.setattr("autocite_mcp.deep_review.DeepReviewer.review", forbidden)
    result = await review_document("See 42 USC §1983.")
    assert result["corrected_text"] == "See 42 U.S.C. § 1983."
    assert result["deep_review_results"]["reason"] == "not_requested"
