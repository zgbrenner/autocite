import pytest

from autocite_mcp.verifiers import CourtListenerVerifier


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return [
            {
                "citation": "576 US 644",
                "normalized_citations": ["576 U.S. 644"],
                "start_index": 0,
                "end_index": 10,
                "status": 200,
                "error_message": "",
                "clusters": [
                    {
                        "case_name": "Obergefell v. Hodges",
                        "absolute_url": "/opinion/280646/obergefell-v-hodges/",
                    }
                ],
            }
        ]


class FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return FakeResponse()


@pytest.mark.asyncio
async def test_verifier_normalizes_courtlistener_result():
    verifier = CourtListenerVerifier(token="secret", client_factory=lambda **_: FakeClient())
    result = await verifier.verify_text("576 US 644")
    assert result["available"] is True
    assert result["results"][0]["normalized_citations"] == ["576 U.S. 644"]
    assert result["results"][0]["case_names"] == ["Obergefell v. Hodges"]


@pytest.mark.asyncio
async def test_verifier_requires_token():
    result = await CourtListenerVerifier(token=None).verify_text("576 U.S. 644")
    assert result["available"] is False
    assert result["reason"] == "missing_token"


@pytest.mark.asyncio
async def test_verifier_rejects_none_text_with_valueerror_not_attributeerror():
    verifier = CourtListenerVerifier(token="secret", client_factory=lambda **_: FakeClient())
    with pytest.raises(ValueError, match="text must not be empty"):
        await verifier.verify_text(None)
