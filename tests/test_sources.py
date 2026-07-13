import pytest

from autocite_mcp.sources import CourtListenerSourceClient, html_to_text


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("GET", "https://example.test")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse(
            [
                {
                    "citation": "576 U.S. 644",
                    "normalized_citations": ["576 U.S. 644"],
                    "status": 200,
                    "start_index": 0,
                    "end_index": 12,
                    "clusters": [
                        {
                            "id": 2812209,
                            "case_name": "Obergefell v. Hodges",
                            "absolute_url": "/opinion/2812209/obergefell-v-hodges/",
                            "date_filed": "2015-06-26",
                            "citation_count": 1000,
                            "sub_opinions": [
                                "https://www.courtlistener.com/api/rest/v4/opinions/1/"
                            ],
                        }
                    ],
                }
            ]
        )

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse(
            {
                "id": 1,
                "type": "010combined",
                "html_with_citations": "<p><b>*675</b> The right to marry is fundamental.</p>",
                "plain_text": "fallback",
            }
        )


@pytest.mark.asyncio
async def test_lookup_and_fetch_returns_bounded_authority_text():
    client = CourtListenerSourceClient(token="token", client_factory=FakeAsyncClient)
    result = await client.lookup_and_fetch("576 U.S. 644")
    assert result["available"] is True
    authority = result["authorities"][0]
    assert authority["case_name"] == "Obergefell v. Hodges"
    assert authority["source_url"].startswith("https://www.courtlistener.com/opinion/")
    assert "The right to marry is fundamental" in authority["source_text"]
    assert authority["later_citation_metadata"]["classification"] == "not_a_citator"


@pytest.mark.asyncio
async def test_lookup_requires_token():
    result = await CourtListenerSourceClient(token="").lookup_and_fetch("576 U.S. 644")
    assert result["available"] is False
    assert result["reason"] == "missing_token"


def test_html_to_text_strips_markup_and_scripts():
    text = html_to_text("<script>ignore()</script><p>Hello&nbsp;<b>world</b></p>")
    assert text == "Hello world"
