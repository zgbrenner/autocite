from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import httpx

COURTLISTENER_ENDPOINT = "https://www.courtlistener.com/api/rest/v4/citation-lookup/"
COURTLISTENER_BASE = "https://www.courtlistener.com"


class CourtListenerVerifier:
    """Optional verifier for U.S. case citations using CourtListener's v4 API."""

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout: float = 30.0,
        client_factory: Callable[..., Any] = httpx.AsyncClient,
    ) -> None:
        self.token = token or os.getenv("COURTLISTENER_TOKEN")
        self.timeout = timeout
        self.client_factory = client_factory

    async def verify_text(self, text: str) -> dict[str, Any]:
        if not self.token:
            return {
                "available": False,
                "reason": "missing_token",
                "message": "Set COURTLISTENER_TOKEN to verify case citations.",
                "results": [],
            }
        if not text.strip():
            raise ValueError("text must not be empty")
        if len(text) > 64_000:
            raise ValueError("CourtListener citation lookup accepts at most 64,000 characters")

        headers = {
            "Authorization": f"Token {self.token}",
            "Accept": "application/json",
            "User-Agent": "autocite-mcp/0.1",
        }
        try:
            async with self.client_factory(timeout=self.timeout) as client:
                response = await client.post(
                    COURTLISTENER_ENDPOINT,
                    headers=headers,
                    data={"text": text},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            return {
                "available": False,
                "reason": "http_error",
                "message": f"CourtListener returned HTTP {exc.response.status_code}",
                "results": [],
            }
        except httpx.HTTPError as exc:
            return {
                "available": False,
                "reason": "network_error",
                "message": str(exc),
                "results": [],
            }

        results: list[dict[str, Any]] = []
        for item in payload:
            clusters = item.get("clusters") or []
            case_names = sorted(
                {
                    str(cluster.get("case_name"))
                    for cluster in clusters
                    if cluster.get("case_name")
                }
            )
            urls = sorted(
                {
                    self._absolute_url(str(cluster.get("absolute_url")))
                    for cluster in clusters
                    if cluster.get("absolute_url")
                }
            )
            results.append(
                {
                    "citation": item.get("citation"),
                    "normalized_citations": item.get("normalized_citations") or [],
                    "start_index": item.get("start_index"),
                    "end_index": item.get("end_index"),
                    "status": item.get("status"),
                    "verified": item.get("status") == 200,
                    "ambiguous": item.get("status") == 300,
                    "error_message": item.get("error_message") or "",
                    "case_names": case_names,
                    "urls": urls,
                }
            )
        return {"available": True, "provider": "CourtListener", "results": results}

    @staticmethod
    def _absolute_url(url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{COURTLISTENER_BASE}{url if url.startswith('/') else '/' + url}"
