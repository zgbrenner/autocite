from __future__ import annotations

from typing import Any

from .evidence import analyze_case_evidence
from .sources import CourtListenerSourceClient


class DeepReviewer:
    """Compose primary-authority retrieval with deterministic evidence analysis."""

    def __init__(self, source_client: CourtListenerSourceClient | None = None) -> None:
        self.source_client = source_client or CourtListenerSourceClient()

    async def review(
        self,
        text: str,
        citations: list[dict[str, Any]],
        *,
        include_source_text: bool = False,
    ) -> dict[str, Any]:
        case_citations = [item for item in citations if item.get("source_type") == "case"]
        if not case_citations:
            return {
                "available": True,
                "provider": "CourtListener",
                "cases": [],
                "message": "No full case citations were detected for source retrieval.",
            }

        retrieval = await self.source_client.lookup_and_fetch(text)
        if not retrieval.get("available"):
            return {
                **retrieval,
                "cases": [],
            }

        authorities = list(retrieval.get("authorities") or [])
        results: list[dict[str, Any]] = []
        unused = list(range(len(authorities)))
        for citation in case_citations:
            authority_index = self._match_authority(citation, authorities, unused)
            if authority_index is None:
                results.append(
                    {
                        "citation": citation,
                        "authority": None,
                        "evidence": None,
                        "status": "authority_not_aligned",
                    }
                )
                continue
            if authority_index in unused:
                unused.remove(authority_index)
            authority = dict(authorities[authority_index])
            source_text = str(authority.pop("source_text", ""))
            evidence = analyze_case_evidence(
                document_text=text,
                citation_start=int(citation.get("start") or 0),
                citation_text=str(citation.get("text") or ""),
                source_text=source_text,
                pincite=(citation.get("components") or {}).get("pincite"),
                include_source_text=include_source_text,
            )
            results.append(
                {
                    "citation": citation,
                    "authority": authority,
                    "evidence": evidence,
                    "status": "evidence_prepared",
                }
            )

        return {
            "available": True,
            "provider": retrieval.get("provider", "CourtListener"),
            "cases": results,
            "confidence_legend": {
                "deterministic": "Formatting or exact text comparison performed by code.",
                "source_verified": "The retrieved source directly contains the stated metadata, quotation, or page marker.",
                "model_inference_required": "The host model or a human must assess legal meaning, scope, and support.",
                "unresolved": "The source was missing, ambiguous, or lacked reliable markers.",
            },
            "limitations": retrieval.get("limitations") or [],
        }

    @staticmethod
    def _match_authority(
        citation: dict[str, Any],
        authorities: list[dict[str, Any]],
        unused: list[int],
    ) -> int | None:
        citation_text = str(citation.get("text") or "").lower()
        for index in unused:
            authority = authorities[index]
            variants = [authority.get("citation"), *(authority.get("normalized_citations") or [])]
            if any(str(variant).lower() in citation_text for variant in variants if variant):
                return index
        return unused[0] if unused else None
