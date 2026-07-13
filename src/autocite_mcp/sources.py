from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Any

import httpx
from bs4 import BeautifulSoup

COURTLISTENER_BASE = "https://www.courtlistener.com"
COURTLISTENER_LOOKUP = f"{COURTLISTENER_BASE}/api/rest/v4/citation-lookup/"
MAX_LOOKUP_TEXT = 64_000
MAX_INTERNAL_OPINION_CHARS = 200_000
MAX_EXPOSED_SOURCE_CHARS = 12_000


def html_to_text(value: str) -> str:
    """Convert retrieved opinion HTML into compact plain text."""
    soup = BeautifulSoup(value or "", "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


class CourtListenerSourceClient:
    """Retrieve matched U.S. case authority and bounded opinion text."""

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout: float = 30.0,
        client_factory: Callable[..., Any] = httpx.AsyncClient,
    ) -> None:
        self.token = token if token is not None else os.getenv("COURTLISTENER_TOKEN")
        self.timeout = timeout
        self.client_factory = client_factory

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self.token}",
            "Accept": "application/json",
            "User-Agent": "autocite-mcp/0.3",
        }

    async def lookup_and_fetch(self, text: str) -> dict[str, Any]:
        if not self.token:
            return {
                "available": False,
                "reason": "missing_token",
                "message": "Set COURTLISTENER_TOKEN to retrieve primary case authority.",
                "authorities": [],
            }
        if not text.strip():
            raise ValueError("text must not be empty")
        if len(text) > MAX_LOOKUP_TEXT:
            raise ValueError("CourtListener citation lookup accepts at most 64,000 characters")

        try:
            async with self.client_factory(timeout=self.timeout) as client:
                response = await client.post(
                    COURTLISTENER_LOOKUP,
                    headers=self.headers,
                    data={"text": text},
                )
                response.raise_for_status()
                lookup_payload = response.json()
                authorities: list[dict[str, Any]] = []
                for lookup in lookup_payload:
                    clusters = lookup.get("clusters") or []
                    if not clusters:
                        authorities.append(self._unmatched_record(lookup))
                        continue
                    for cluster in clusters:
                        cluster = await self._ensure_cluster(client, cluster)
                        opinions = await self._fetch_opinions(client, cluster)
                        source_text = self._combine_opinion_text(opinions)
                        authorities.append(
                            self._authority_record(lookup, cluster, opinions, source_text)
                        )
        except httpx.HTTPStatusError as exc:
            return {
                "available": False,
                "reason": "http_error",
                "message": f"CourtListener returned HTTP {exc.response.status_code}",
                "authorities": [],
            }
        except httpx.HTTPError as exc:
            return {
                "available": False,
                "reason": "network_error",
                "message": str(exc),
                "authorities": [],
            }

        return {
            "available": True,
            "provider": "CourtListener",
            "authorities": authorities,
            "limitations": [
                "CourtListener retrieval does not establish good-law status or proposition support.",
                "Later-citation counts are not treatment analysis and are not a citator.",
            ],
        }

    async def _ensure_cluster(self, client: Any, cluster: dict[str, Any]) -> dict[str, Any]:
        if cluster.get("sub_opinions"):
            return cluster
        resource_uri = cluster.get("resource_uri")
        cluster_id = cluster.get("id")
        url = resource_uri or (
            f"{COURTLISTENER_BASE}/api/rest/v4/clusters/{cluster_id}/"
            if cluster_id
            else None
        )
        if not url:
            return cluster
        response = await client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    async def _fetch_opinions(self, client: Any, cluster: dict[str, Any]) -> list[dict[str, Any]]:
        opinions: list[dict[str, Any]] = []
        for url in (cluster.get("sub_opinions") or [])[:5]:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            opinions.append(response.json())
        opinions.sort(key=lambda item: str(item.get("type") or "999"))
        return opinions

    @staticmethod
    def _opinion_text(opinion: dict[str, Any]) -> str:
        for field in (
            "html_with_citations",
            "html_columbia",
            "html_lawbox",
            "html_anon_2020",
            "html",
        ):
            value = opinion.get(field)
            if value:
                return html_to_text(str(value))
        return re.sub(r"\s+", " ", str(opinion.get("plain_text") or "")).strip()

    def _combine_opinion_text(self, opinions: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        remaining = MAX_INTERNAL_OPINION_CHARS
        for opinion in opinions:
            text = self._opinion_text(opinion)
            if not text:
                continue
            text = text[:remaining]
            parts.append(text)
            remaining -= len(text)
            if remaining <= 0:
                break
        return "\n\n".join(parts)[:MAX_EXPOSED_SOURCE_CHARS]

    def _authority_record(
        self,
        lookup: dict[str, Any],
        cluster: dict[str, Any],
        opinions: list[dict[str, Any]],
        source_text: str,
    ) -> dict[str, Any]:
        return {
            "citation": lookup.get("citation"),
            "normalized_citations": lookup.get("normalized_citations") or [],
            "status": lookup.get("status"),
            "ambiguous": lookup.get("status") == 300,
            "start_index": lookup.get("start_index"),
            "end_index": lookup.get("end_index"),
            "cluster_id": cluster.get("id"),
            "case_name": cluster.get("case_name") or cluster.get("case_name_full") or "",
            "date_filed": cluster.get("date_filed"),
            "source_url": self._absolute_url(str(cluster.get("absolute_url") or "")),
            "opinion_ids": [item.get("id") for item in opinions if item.get("id") is not None],
            "source_text": source_text,
            "source_text_truncated": len(source_text) >= MAX_EXPOSED_SOURCE_CHARS,
            "later_citation_metadata": {
                "citation_count": cluster.get("citation_count"),
                "classification": "not_a_citator",
                "warning": "A count of later citations does not reveal positive, negative, or precedential treatment.",
            },
        }

    def _unmatched_record(self, lookup: dict[str, Any]) -> dict[str, Any]:
        return {
            "citation": lookup.get("citation"),
            "normalized_citations": lookup.get("normalized_citations") or [],
            "status": lookup.get("status"),
            "ambiguous": lookup.get("status") == 300,
            "start_index": lookup.get("start_index"),
            "end_index": lookup.get("end_index"),
            "case_name": "",
            "source_url": "",
            "source_text": "",
            "error_message": lookup.get("error_message") or "Citation was not matched to a CourtListener authority.",
            "later_citation_metadata": {
                "citation_count": None,
                "classification": "not_a_citator",
            },
        }

    @staticmethod
    def _absolute_url(url: str) -> str:
        if not url:
            return ""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{COURTLISTENER_BASE}{url if url.startswith('/') else '/' + url}"
