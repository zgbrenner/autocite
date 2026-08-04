from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

import httpx


COURTLISTENER_CITATION_LOOKUP_URL = (
    "https://www.courtlistener.com/api/rest/v4/citation-lookup/"
)


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class AuthorityMatch:
    citation: str
    normalized_citations: tuple[str, ...]
    start_index: int | None
    end_index: int | None
    status: VerificationStatus
    cluster_count: int
    clusters: tuple[Mapping[str, Any], ...]
    error_message: str = ""

    @property
    def verified(self) -> bool:
        return self.status is VerificationStatus.VERIFIED

    def as_dict(self) -> dict[str, Any]:
        return {
            "citation": self.citation,
            "normalized_citations": list(self.normalized_citations),
            "start_index": self.start_index,
            "end_index": self.end_index,
            "status": self.status.value,
            "verified": self.verified,
            "cluster_count": self.cluster_count,
            "clusters": [dict(cluster) for cluster in self.clusters],
            "error_message": self.error_message,
        }


class AuthorityVerificationError(RuntimeError):
    """Raised when strict authority verification cannot be completed."""


class CourtListenerAuthorityVerifier:
    """Verify case citations using CourtListener's citation lookup API.

    The client is intentionally small and dependency-injected so desktop, CLI,
    MCP, and tests can share identical behavior. Network failures are represented
    as ``unavailable`` results by default. Callers that need fail-closed behavior
    can pass ``strict=True``.
    """

    def __init__(
        self,
        *,
        api_token: str | None = None,
        client: httpx.AsyncClient | None = None,
        endpoint: str = COURTLISTENER_CITATION_LOOKUP_URL,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._api_token = api_token
        self._client = client
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "AutoCite authority verifier",
        }
        if self._api_token:
            headers["Authorization"] = f"Token {self._api_token}"
        return headers

    @staticmethod
    def _normalize_result(raw: Mapping[str, Any]) -> AuthorityMatch:
        citation = str(raw.get("citation") or "")
        normalized_raw = raw.get("normalized_citations")
        normalized = (
            tuple(str(value) for value in normalized_raw)
            if isinstance(normalized_raw, Sequence)
            and not isinstance(normalized_raw, (str, bytes))
            else ()
        )
        clusters_raw = raw.get("clusters")
        clusters = (
            tuple(
                cluster
                for cluster in clusters_raw
                if isinstance(cluster, Mapping)
            )
            if isinstance(clusters_raw, Sequence)
            and not isinstance(clusters_raw, (str, bytes))
            else ()
        )
        api_status = raw.get("status")
        error_message = str(raw.get("error_message") or "")
        if api_status == 200 and len(clusters) == 1:
            status = VerificationStatus.VERIFIED
        elif api_status == 200 and len(clusters) > 1:
            status = VerificationStatus.AMBIGUOUS
        elif api_status == 404 or not clusters:
            status = VerificationStatus.NOT_FOUND
        else:
            status = VerificationStatus.UNAVAILABLE
        return AuthorityMatch(
            citation=citation,
            normalized_citations=normalized,
            start_index=(
                int(raw["start_index"])
                if isinstance(raw.get("start_index"), int)
                else None
            ),
            end_index=(
                int(raw["end_index"])
                if isinstance(raw.get("end_index"), int)
                else None
            ),
            status=status,
            cluster_count=len(clusters),
            clusters=clusters,
            error_message=error_message,
        )

    @staticmethod
    def _unavailable_result(text: str, message: str) -> AuthorityMatch:
        return AuthorityMatch(
            citation=text,
            normalized_citations=(),
            start_index=None,
            end_index=None,
            status=VerificationStatus.UNAVAILABLE,
            cluster_count=0,
            clusters=(),
            error_message=message,
        )

    async def verify_text(
        self,
        text: str,
        *,
        strict: bool = False,
    ) -> tuple[AuthorityMatch, ...]:
        if not text.strip():
            return ()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
        )
        try:
            response = await client.post(
                self._endpoint,
                headers=self._headers(),
                data={"text": text},
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("CourtListener returned a non-list payload")
            return tuple(
                self._normalize_result(item)
                for item in payload
                if isinstance(item, Mapping)
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            if strict:
                raise AuthorityVerificationError(
                    f"authority verification failed: {exc}"
                ) from exc
            return (self._unavailable_result(text, str(exc)),)
        finally:
            if owns_client:
                await client.aclose()

    async def verify_citation(
        self,
        *,
        volume: str | int,
        reporter: str,
        page: str | int,
        strict: bool = False,
    ) -> tuple[AuthorityMatch, ...]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
        )
        citation = f"{volume} {reporter} {page}"
        try:
            response = await client.post(
                self._endpoint,
                headers=self._headers(),
                data={
                    "volume": str(volume),
                    "reporter": reporter,
                    "page": str(page),
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("CourtListener returned a non-list payload")
            return tuple(
                self._normalize_result(item)
                for item in payload
                if isinstance(item, Mapping)
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            if strict:
                raise AuthorityVerificationError(
                    f"authority verification failed: {exc}"
                ) from exc
            return (self._unavailable_result(citation, str(exc)),)
        finally:
            if owns_client:
                await client.aclose()
