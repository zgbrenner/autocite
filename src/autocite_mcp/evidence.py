from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

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


def rank_passages(proposition: str, source_text: str, *, limit: int = 3) -> list[dict[str, Any]]:
    """Rank candidate passages using disclosed lexical metrics."""
    proposition_norm = _comparison_text(proposition)
    proposition_tokens = _tokens(proposition)
    ranked: list[dict[str, Any]] = []
    for passage in _passage_windows(source_text):
        passage_tokens = _tokens(passage)
        union = proposition_tokens | passage_tokens
        overlap = len(proposition_tokens & passage_tokens) / len(union) if union else 0.0
        similarity = SequenceMatcher(None, proposition_norm, _comparison_text(passage)).ratio()
        combined = (overlap * 0.65) + (similarity * 0.35)
        ranked.append(
            {
                "passage": passage,
                "token_overlap": round(overlap, 4),
                "sequence_similarity": round(similarity, 4),
                "combined_score": round(combined, 4),
                "method": "token_jaccard_65_percent_plus_sequence_match_35_percent",
            }
        )
    ranked.sort(key=lambda item: item["combined_score"], reverse=True)
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


def analyze_case_evidence(
    *,
    document_text: str,
    citation_start: int,
    citation_text: str,
    source_text: str,
    pincite: str | None = None,
    include_source_text: bool = False,
) -> dict[str, Any]:
    """Prepare source evidence for a host model or human reviewer."""
    proposition = extract_proposition(document_text, citation_start)
    quotes = extract_nearby_quotes(document_text, citation_start)
    quote_results = [match_quote(quote, source_text) | {"quote": quote} for quote in quotes]
    quote_result = (
        max(quote_results, key=lambda item: item["score"])
        if quote_results
        else {"status": "not_supplied", "score": 0.0, "matched_excerpt": "", "quote": ""}
    )
    passages = rank_passages(proposition, source_text)
    result: dict[str, Any] = {
        "citation": citation_text,
        "quotation": quote_result,
        "pincite": _pincite_result(pincite, source_text, passages),
        "proposition": {
            "text": proposition,
            "candidate_passages": passages,
            "conclusion": "not_determined",
            "requires_legal_judgment": True,
            "warning": "Lexical similarity ranks evidence for review; it does not determine legal support, scope, validity, or controlling weight.",
        },
        "provenance": {
            "quotation": "source_verified_when_exact_or_normalized",
            "pincite": "source_verified_only_when_explicit_marker_present",
            "proposition": "lexical_candidate_ranking_only",
        },
    }
    if include_source_text:
        result["source_excerpt"] = normalize_text(source_text)[:12_000]
    return result
