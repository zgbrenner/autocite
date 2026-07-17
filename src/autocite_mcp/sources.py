from __future__ import annotations

import asyncio
import copy
import hashlib
import os
import re
import time
from collections.abc import Callable
from typing import Any

import httpx
from bs4 import BeautifulSoup

from . import __version__

COURTLISTENER_BASE = "https://www.courtlistener.com"
COURTLISTENER_LOOKUP = f"{COURTLISTENER_BASE}/api/rest/v4/citation-lookup/"
MAX_LOOKUP_TEXT = 64_000
MAX_INTERNAL_OPINION_CHARS = 200_000
MAX_EXPOSED_SOURCE_CHARS = 12_000
MAX_OPINIONS_PER_CLUSTER = 5
MAX_CLUSTER_FETCHES = 40

# CourtListener free-tier quotas are limited; retry transient failures politely
# and reuse recent lookups so re-running a review does not double-spend quota.
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
MAX_REQUEST_RETRIES = 2
MAX_RETRY_AFTER_SECONDS = 30.0
LOOKUP_CACHE_MAX_ENTRIES = 32

_lookup_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _lookup_cache_ttl() -> float:
    raw = os.getenv("AUTOCITE_SOURCE_CACHE_TTL", "3600")
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 3600.0


def clear_lookup_cache() -> None:
    _lookup_cache.clear()


def _cache_get(key: str) -> dict[str, Any] | None:
    entry = _lookup_cache.get(key)
    if not entry:
        return None
    stored_at, payload = entry
    if time.monotonic() - stored_at > _lookup_cache_ttl():
        _lookup_cache.pop(key, None)
        return None
    return copy.deepcopy(payload)


def _cache_put(key: str, payload: dict[str, Any]) -> None:
    if _lookup_cache_ttl() <= 0:
        return
    if len(_lookup_cache) >= LOOKUP_CACHE_MAX_ENTRIES:
        oldest = min(_lookup_cache, key=lambda item: _lookup_cache[item][0])
        _lookup_cache.pop(oldest, None)
    _lookup_cache[key] = (time.monotonic(), copy.deepcopy(payload))


def _validated_courtlistener_url(url: str) -> str | None:
    """Allow follow-up GETs only against CourtListener itself.

    Cluster and opinion URLs come from API response payloads; the bearer token in
    self.headers must never be sent to any other host.
    """
    from urllib.parse import urlparse

    parsed = urlparse(str(url or ""))
    if parsed.scheme != "https":
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in {"www.courtlistener.com", "courtlistener.com"}:
        return None
    return url


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
            "User-Agent": f"autocite-mcp/{__version__}",
        }

    @staticmethod
    async def _request_with_backoff(send: Callable[[], Any]) -> Any:
        """Await a request, retrying rate limits and transient upstream errors."""
        delay = 1.0
        for attempt in range(MAX_REQUEST_RETRIES + 1):
            response = await send()
            if response.status_code not in RETRYABLE_STATUS_CODES or attempt == MAX_REQUEST_RETRIES:
                response.raise_for_status()
                return response
            retry_after = getattr(response, "headers", {}).get("retry-after")
            wait = delay
            if retry_after:
                try:
                    wait = min(float(retry_after), MAX_RETRY_AFTER_SECONDS)
                except ValueError:
                    pass
            await asyncio.sleep(wait)
            delay = min(delay * 2, MAX_RETRY_AFTER_SECONDS)
        raise AssertionError("unreachable")

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

        cache_key = hashlib.sha256(f"{self.token}\x00{text}".encode()).hexdigest()
        cached = _cache_get(cache_key)
        if cached is not None:
            return {**cached, "served_from_cache": True}

        try:
            async with self.client_factory(timeout=self.timeout) as client:
                response = await self._request_with_backoff(
                    lambda: client.post(
                        COURTLISTENER_LOOKUP,
                        headers=self.headers,
                        data={"text": text},
                    )
                )
                lookup_payload = response.json()
                authorities: list[dict[str, Any]] = []
                cluster_budget = MAX_CLUSTER_FETCHES
                for lookup in lookup_payload:
                    clusters = lookup.get("clusters") or []
                    if not clusters:
                        authorities.append(self._unmatched_record(lookup))
                        continue
                    for cluster in clusters:
                        if cluster_budget <= 0:
                            record = self._unmatched_record(lookup)
                            record["error_message"] = (
                                "Cluster retrieval budget exhausted for this review; "
                                "re-run deep review on a smaller portion of the document."
                            )
                            authorities.append(record)
                            continue
                        cluster_budget -= 1
                        cluster = await self._ensure_cluster(client, cluster)
                        opinions = await self._fetch_opinions(client, cluster)
                        analysis_text = self._combine_opinion_text(opinions)
                        authorities.append(
                            self._authority_record(
                                lookup,
                                cluster,
                                opinions,
                                analysis_text,
                            )
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

        result = {
            "available": True,
            "provider": "CourtListener",
            "authorities": authorities,
            "limitations": [
                "CourtListener retrieval does not establish good-law status or proposition support.",
                "Later-citation counts are not treatment analysis and are not a citator.",
            ],
        }
        _cache_put(cache_key, result)
        return result

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
        url = _validated_courtlistener_url(url)
        if not url:
            return cluster
        response = await self._request_with_backoff(lambda: client.get(url, headers=self.headers))
        return response.json()

    async def _fetch_opinions(self, client: Any, cluster: dict[str, Any]) -> list[dict[str, Any]]:
        opinions: list[dict[str, Any]] = []
        for url in (cluster.get("sub_opinions") or [])[:MAX_OPINIONS_PER_CLUSTER]:
            url = _validated_courtlistener_url(url)
            if not url:
                continue
            response = await self._request_with_backoff(
                lambda url=url: client.get(url, headers=self.headers)
            )
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
        return "\n\n".join(parts)[:MAX_INTERNAL_OPINION_CHARS]

    def _authority_record(
        self,
        lookup: dict[str, Any],
        cluster: dict[str, Any],
        opinions: list[dict[str, Any]],
        analysis_text: str,
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
            "analysis_text": analysis_text,
            "source_text": analysis_text[:MAX_EXPOSED_SOURCE_CHARS],
            "source_text_truncated": len(analysis_text) > MAX_EXPOSED_SOURCE_CHARS,
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
            "analysis_text": "",
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
