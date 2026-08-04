from __future__ import annotations

import httpx
import pytest

from autocite_mcp.authority_verification import (
    AuthorityVerificationError,
    CourtListenerAuthorityVerifier,
    VerificationStatus,
)


@pytest.mark.asyncio
async def test_verify_text_normalizes_verified_and_ambiguous_results():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Token secret"
        body = (await request.aread()).decode()
        assert "text=" in body
        return httpx.Response(
            200,
            json=[
                {
                    "citation": "576 U.S. 644",
                    "normalized_citations": ["576 U.S. 644"],
                    "start_index": 10,
                    "end_index": 22,
                    "status": 200,
                    "error_message": "",
                    "clusters": [{"id": 1, "case_name": "Obergefell"}],
                },
                {
                    "citation": "1 F.3d 2",
                    "normalized_citations": ["1 F.3d 2"],
                    "start_index": 30,
                    "end_index": 38,
                    "status": 200,
                    "error_message": "",
                    "clusters": [{"id": 2}, {"id": 3}],
                },
            ],
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        verifier = CourtListenerAuthorityVerifier(
            api_token="secret",
            client=client,
        )
        results = await verifier.verify_text(
            "See 576 U.S. 644 and 1 F.3d 2."
        )

    assert results[0].status is VerificationStatus.VERIFIED
    assert results[0].verified is True
    assert results[0].cluster_count == 1
    assert results[0].as_dict()["normalized_citations"] == ["576 U.S. 644"]
    assert results[1].status is VerificationStatus.AMBIGUOUS
    assert results[1].verified is False
    assert results[1].cluster_count == 2


@pytest.mark.asyncio
async def test_verify_citation_posts_structured_components():
    async def handler(request: httpx.Request) -> httpx.Response:
        body = (await request.aread()).decode()
        assert "volume=410" in body
        assert "reporter=U.S." in body
        assert "page=113" in body
        return httpx.Response(
            200,
            json=[
                {
                    "citation": "410 U.S. 113",
                    "normalized_citations": ["410 U.S. 113"],
                    "status": 200,
                    "clusters": [{"id": 4}],
                }
            ],
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        results = await CourtListenerAuthorityVerifier(
            client=client
        ).verify_citation(volume=410, reporter="U.S.", page=113)

    assert len(results) == 1
    assert results[0].citation == "410 U.S. 113"
    assert results[0].status is VerificationStatus.VERIFIED


@pytest.mark.asyncio
async def test_not_found_result_is_distinct_from_service_failure():
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "citation": "999 F.9th 999",
                    "normalized_citations": ["999 F.9th 999"],
                    "status": 404,
                    "error_message": "Citation not found",
                    "clusters": [],
                }
            ],
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        results = await CourtListenerAuthorityVerifier(
            client=client
        ).verify_text("999 F.9th 999")

    assert results[0].status is VerificationStatus.NOT_FOUND
    assert results[0].error_message == "Citation not found"


@pytest.mark.asyncio
async def test_network_failure_returns_unavailable_by_default():
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        results = await CourtListenerAuthorityVerifier(
            client=client
        ).verify_text("576 U.S. 644")

    assert results[0].status is VerificationStatus.UNAVAILABLE
    assert results[0].citation == "576 U.S. 644"
    assert "offline" in results[0].error_message


@pytest.mark.asyncio
async def test_strict_mode_fails_closed_on_network_error():
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        verifier = CourtListenerAuthorityVerifier(client=client)
        with pytest.raises(AuthorityVerificationError, match="offline"):
            await verifier.verify_text("576 U.S. 644", strict=True)


@pytest.mark.asyncio
async def test_empty_text_skips_network_request():
    called = False

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        results = await CourtListenerAuthorityVerifier(
            client=client
        ).verify_text("  \n")

    assert results == ()
    assert called is False
