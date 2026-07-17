from __future__ import annotations

import os
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Protocol, Sequence

_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_QUOTE_RE = re.compile(r"[\"“](.{8,500}?)[\"”]", re.DOTALL)


def normalize_text(value: str) -> str:
    """Normalize text for transparent, non-semantic comparison."""
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("—", "-").replace("–", "-")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _comparison_text(value: str) -> str:
    value = normalize_text(value).lower()
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def extract_proposition(text: str, citation_start: int, *, max_chars: int = 600) -> str:
    """Return the nearest complete proposition before a citation."""
    before = text[max(0, citation_start - max_chars) : citation_start].strip()
    if not before:
        return ""
    sentences = [part.strip() for part in _SENTENCE_RE.split(before) if part.strip()]
    if not sentences:
        return before
    return sentences[-1]


def extract_nearby_quotes(text: str, citation_start: int, *, max_chars: int = 800) -> list[str]:
    """Extract quoted language appearing shortly before a citation."""
    before = text[max(0, citation_start - max_chars) : citation_start]
    matches = [normalize_text(match.group(1)) for match in _QUOTE_RE.finditer(before)]
    return matches[-3:]


def match_quote(quote: str, source_text: str) -> dict[str, Any]:
    """Compare quoted language with source text without making a legal conclusion."""
    if not quote.strip():
        return {"status": "not_supplied", "score": 0.0, "matched_excerpt": ""}
    normalized_quote = normalize_text(quote)
    normalized_source = normalize_text(source_text)
    if normalized_quote in normalized_source:
        start = normalized_source.index(normalized_quote)
        return {
            "status": "exact",
            "score": 1.0,
            "matched_excerpt": normalized_source[max(0, start - 80) : start + len(normalized_quote) + 80],
        }

    comparison_quote = _comparison_text(quote)
    comparison_source = _comparison_text(source_text)
    if comparison_quote and comparison_quote in comparison_source:
        start = comparison_source.index(comparison_quote)
        return {
            "status": "normalized",
            "score": 0.98,
            "matched_excerpt": comparison_source[max(0, start - 80) : start + len(comparison_quote) + 80],
        }

    windows = _passage_windows(source_text, target_words=max(12, len(comparison_quote.split()) + 8))
    best: tuple[float, str] = (0.0, "")
    for passage in windows:
        score = SequenceMatcher(None, comparison_quote, _comparison_text(passage)).ratio()
        if score > best[0]:
            best = (score, passage)
    status = "partial" if best[0] >= 0.55 else "absent"
    return {
        "status": status,
        "score": round(best[0], 4),
        "matched_excerpt": best[1] if status == "partial" else "",
    }


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in _WORD_RE.findall(value) if len(token) > 2}


def _passage_windows(source_text: str, *, target_words: int = 70) -> list[str]:
    sentences = [normalize_text(item) for item in _SENTENCE_RE.split(source_text) if item.strip()]
    if not sentences:
        return [normalize_text(source_text)] if source_text.strip() else []
    windows: list[str] = []
    for index in range(len(sentences)):
        selected: list[str] = []
        words = 0
        for sentence in sentences[index : index + 3]:
            selected.append(sentence)
            words += len(sentence.split())
            if words >= target_words:
                break
        windows.append(" ".join(selected))
    return windows


_LEXICAL_METHOD = "token_jaccard_65_percent_plus_sequence_match_35_percent"
_TOKEN_OVERLAP_WEIGHT = 0.65
_SEQUENCE_SIMILARITY_WEIGHT = 0.35

_HYBRID_METHOD = "hybrid_lexical_50_percent_plus_local_embedding_cosine_50_percent"
_HYBRID_LEXICAL_WEIGHT = 0.5
_HYBRID_EMBEDDING_WEIGHT = 0.5


class PassageScorer(Protocol):
    """Scores candidate passages against a proposition.

    Every scorer must stamp each returned passage with the "scorer" key that actually
    produced its "combined_score", so callers never mistake a fallback for a semantic run.
    """

    name: str

    def score(self, proposition: str, passages: Sequence[str]) -> list[dict[str, Any]]: ...


def _lexical_component_scores(proposition: str, passages: Sequence[str]) -> list[dict[str, Any]]:
    proposition_norm = _comparison_text(proposition)
    proposition_tokens = _tokens(proposition)
    scored: list[dict[str, Any]] = []
    for passage in passages:
        passage_tokens = _tokens(passage)
        union = proposition_tokens | passage_tokens
        overlap = len(proposition_tokens & passage_tokens) / len(union) if union else 0.0
        similarity = SequenceMatcher(None, proposition_norm, _comparison_text(passage)).ratio()
        lexical_score = (overlap * _TOKEN_OVERLAP_WEIGHT) + (similarity * _SEQUENCE_SIMILARITY_WEIGHT)
        scored.append(
            {
                "passage": passage,
                "token_overlap": round(overlap, 4),
                "sequence_similarity": round(similarity, 4),
                "lexical_score": round(lexical_score, 4),
            }
        )
    return scored


class LexicalPassageScorer:
    """Deterministic passage scorer: 65% token-set overlap + 35% sequence similarity.

    This is the default, always-available scorer described in docs/SOURCE_REVIEW.md. It has
    no external dependencies and never fails.
    """

    name = "lexical"

    def score(self, proposition: str, passages: Sequence[str]) -> list[dict[str, Any]]:
        scored = _lexical_component_scores(proposition, passages)
        for item in scored:
            item["combined_score"] = item["lexical_score"]
            item["method"] = _LEXICAL_METHOD
            item["scorer"] = self.name
        return scored


class HybridPassageScorer:
    """Blends the deterministic lexical score with local-embedding cosine similarity.

    The embedding backend defaults to a lazily loaded, offline-only local sentence-transformers
    bi-encoder (same lazy-load/offline-only pattern and default model as
    ``retrieval.LocalEmbeddingRuleRetriever``). It can also be swapped for any object exposing an
    ``encode(texts) -> Sequence[Sequence[float]]`` method, which tests use to inject a small
    deterministic fake instead of pulling in sentence-transformers/torch.

    Graceful degradation is mandatory here: if the backend is unavailable or raises for any
    reason (missing optional dependency, missing/uncached model, or any other runtime error),
    this scorer falls back to the plain lexical score instead of raising. The fallback is never
    silent -- every affected passage is stamped with ``scorer="lexical_fallback_hybrid_unavailable"``
    and a ``fallback_reason`` explaining why.
    """

    name = "hybrid"

    def __init__(
        self,
        embedding_backend: Any | None = None,
        *,
        model_path: str = "BAAI/bge-small-en-v1.5",
        offline_only: bool = True,
    ) -> None:
        if embedding_backend is not None:
            self._backend = embedding_backend
        else:
            from .retrieval import LocalPassageEmbeddingBackend

            self._backend = LocalPassageEmbeddingBackend(model_path, offline_only=offline_only)

    def score(self, proposition: str, passages: Sequence[str]) -> list[dict[str, Any]]:
        scored = _lexical_component_scores(proposition, passages)
        if not scored:
            return scored
        try:
            vectors = self._backend.encode([proposition, *passages])
        except Exception as exc:  # noqa: BLE001 - any backend failure must degrade, never raise
            for item in scored:
                item["combined_score"] = item["lexical_score"]
                item["method"] = _LEXICAL_METHOD
                item["scorer"] = "lexical_fallback_hybrid_unavailable"
                item["fallback_reason"] = f"{type(exc).__name__}: {exc}"
            return scored
        query_vector = vectors[0]
        for index, item in enumerate(scored, start=1):
            embedding_similarity = float(sum(a * b for a, b in zip(query_vector, vectors[index])))
            item["embedding_similarity"] = round(embedding_similarity, 4)
            item["combined_score"] = round(
                (item["lexical_score"] * _HYBRID_LEXICAL_WEIGHT)
                + (embedding_similarity * _HYBRID_EMBEDDING_WEIGHT),
                4,
            )
            item["method"] = _HYBRID_METHOD
            item["scorer"] = "hybrid_local_embedding"
        return scored


def resolve_default_passage_scorer() -> PassageScorer:
    """Select the passage scorer from AUTOCITE_PASSAGE_SCORER (defaults to "lexical").

    Accepted values are "lexical" (default) and "hybrid". This only selects and constructs the
    scorer object -- construction never loads a model, so choosing "hybrid" is cheap even when
    sentence-transformers is not installed; the optional dependency is only touched, and the
    fallback path only triggered, the first time a passage is actually scored.
    """
    choice = os.getenv("AUTOCITE_PASSAGE_SCORER", "lexical").strip().lower()
    if choice == "hybrid":
        return HybridPassageScorer()
    if choice not in {"", "lexical"}:
        raise ValueError(f"AUTOCITE_PASSAGE_SCORER must be 'lexical' or 'hybrid', got {choice!r}")
    return LexicalPassageScorer()


def rank_passages(
    proposition: str,
    source_text: str,
    *,
    limit: int = 3,
    scorer: PassageScorer | None = None,
) -> list[dict[str, Any]]:
    """Rank candidate passages using the configured scorer (lexical by default).

    Pass ``scorer`` explicitly to inject a specific scorer (used by tests and by
    ``DeepReviewer``); otherwise the scorer is resolved from ``AUTOCITE_PASSAGE_SCORER``.
    Results are deterministic: scores come from fixed weights and ties keep the stable,
    document-order position of the passage window they came from.
    """
    resolved_scorer = scorer or resolve_default_passage_scorer()
    windows = _passage_windows(source_text)
    scored = resolved_scorer.score(proposition, windows)
    ranked = sorted(scored, key=lambda item: -item["combined_score"])
    return ranked[: max(0, limit)]


def _pincite_result(pincite: str | None, source_text: str, passages: list[dict[str, Any]]) -> dict[str, Any]:
    if not pincite:
        return {
            "status": "not_supplied",
            "pincite": None,
            "message": "No pincite was supplied for independent review.",
        }
    escaped = re.escape(str(pincite).strip())
    marker = re.compile(rf"(?:\*|\bPage\s+|\[){escaped}(?:\]|\b)", re.IGNORECASE)
    if marker.search(source_text):
        return {
            "status": "confirmed_by_page_marker",
            "pincite": str(pincite),
            "message": "The retrieved source text contains an explicit marker for this page.",
        }
    if passages and passages[0]["combined_score"] >= 0.18:
        return {
            "status": "passage_found_page_unverified",
            "pincite": str(pincite),
            "message": "A potentially relevant passage was found, but the retrieved text lacks a reliable page marker.",
        }
    return {
        "status": "unverifiable",
        "pincite": str(pincite),
        "message": "The retrieved text did not provide a reliable page marker or a strong candidate passage.",
    }


_PROPOSITION_PROVENANCE_BY_SCORER = {
    "lexical": "lexical_candidate_ranking_only",
    "hybrid_local_embedding": "hybrid_lexical_and_local_embedding_candidate_ranking",
    "lexical_fallback_hybrid_unavailable": "lexical_candidate_ranking_only_hybrid_scorer_unavailable_fallback",
}


def analyze_case_evidence(
    *,
    document_text: str,
    citation_start: int,
    citation_text: str,
    source_text: str,
    pincite: str | None = None,
    include_source_text: bool = False,
    passage_scorer: PassageScorer | None = None,
) -> dict[str, Any]:
    """Prepare source evidence for a host model or human reviewer.

    ``passage_scorer`` is injected explicitly by callers such as ``DeepReviewer``; when omitted
    it is resolved from ``AUTOCITE_PASSAGE_SCORER`` (lexical by default).
    """
    proposition = extract_proposition(document_text, citation_start)
    quotes = extract_nearby_quotes(document_text, citation_start)
    quote_results = [match_quote(quote, source_text) | {"quote": quote} for quote in quotes]
    quote_result = (
        max(quote_results, key=lambda item: item["score"])
        if quote_results
        else {"status": "not_supplied", "score": 0.0, "matched_excerpt": "", "quote": ""}
    )
    resolved_scorer = passage_scorer or resolve_default_passage_scorer()
    passages = rank_passages(proposition, source_text, scorer=resolved_scorer)
    scorer_used = passages[0]["scorer"] if passages else resolved_scorer.name
    result: dict[str, Any] = {
        "citation": citation_text,
        "quotation": quote_result,
        "pincite": _pincite_result(pincite, source_text, passages),
        "proposition": {
            "text": proposition,
            "candidate_passages": passages,
            "scorer": scorer_used,
            "conclusion": "not_determined",
            "requires_legal_judgment": True,
            "warning": "Passage ranking (lexical, or lexical blended with local-embedding similarity) ranks evidence for review; it does not determine legal support, scope, validity, or controlling weight.",
        },
        "provenance": {
            "quotation": "source_verified_when_exact_or_normalized",
            "pincite": "source_verified_only_when_explicit_marker_present",
            "proposition": _PROPOSITION_PROVENANCE_BY_SCORER.get(scorer_used, "lexical_candidate_ranking_only"),
        },
    }
    if include_source_text:
        result["source_excerpt"] = normalize_text(source_text)[:12_000]
    return result
