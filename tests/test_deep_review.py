import pytest

from autocite_mcp.deep_review import DeepReviewer
from autocite_mcp.tools import review_document


class FakeSourceClient:
    def __init__(self):
        self.calls = 0

    async def lookup_and_fetch(self, text):
        self.calls += 1
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
                    "source_text": "*675 The right to marry is fundamental under the Constitution.",
                    "later_citation_metadata": {
                        "citation_count": 1000,
                        "classification": "not_a_citator",
                    },
                }
            ],
        }


@pytest.mark.asyncio
async def test_deep_reviewer_builds_evidence_records():
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
    assert result["available"] is True
    assert result["cases"][0]["authority"]["case_name"] == "Obergefell v. Hodges"
    assert result["cases"][0]["evidence"]["proposition"]["requires_legal_judgment"] is True


@pytest.mark.asyncio
async def test_primary_workflow_does_not_call_network_by_default(monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("network should not be called")

    monkeypatch.setattr("autocite_mcp.deep_review.DeepReviewer.review", forbidden)
    result = await review_document("See 42 USC §1983.")
    assert result["corrected_text"] == "See 42 U.S.C. § 1983."
    assert result["deep_review_results"]["reason"] == "not_requested"
