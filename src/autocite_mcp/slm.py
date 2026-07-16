from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


VALID_MODES = {"bluepages", "whitepages"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_SOURCE_TYPES = {
    "case",
    "statute",
    "regulation",
    "constitution",
    "journal_article",
    "book",
    "court_document",
    "internet",
    "short_form",
    "foreign_international_tribal",
    "ai_content",
    "archival",
    "unknown",
}
_REQUIRED_FIELDS = {
    "citation_text",
    "start",
    "end",
    "source_type",
    "mode",
    "issue_code",
    "explanation",
    "confidence",
    "proposed_citation",
    "missing_facts",
    "facts_used",
}
_NON_MATERIAL_WORDS = {
    "and",
    "at",
    "in",
    "no",
    "nos",
    "of",
    "p",
    "pp",
    "re",
    "see",
    "the",
}
_PROHIBITED_CLAIMS = (
    "good law",
    "controlling authority",
    "binding authority",
    "supports the proposition",
    "proves the proposition",
    "has positive treatment",
    "has no negative treatment",
)


def _require_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


@dataclass(frozen=True)
class SLMProposal:
    citation_text: str
    start: int
    end: int
    source_type: str
    mode: str
    issue_code: str
    explanation: str
    confidence: str
    proposed_citation: str | None
    missing_facts: tuple[str, ...]
    facts_used: dict[str, str]

    @classmethod
    def from_json(cls, raw: str) -> "SLMProposal":
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("SLM output must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("SLM output must be a JSON object")
        return cls.from_mapping(payload)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SLMProposal":
        missing = sorted(_REQUIRED_FIELDS - set(payload))
        if missing:
            raise ValueError(f"SLM proposal is missing fields: {', '.join(missing)}")

        start = payload["start"]
        end = payload["end"]
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            raise ValueError("start must be a non-negative integer")
        if isinstance(end, bool) or not isinstance(end, int) or end <= start:
            raise ValueError("end must be an integer greater than start")

        mode = _require_string(payload, "mode").strip().lower()
        if mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(VALID_MODES)}")
        confidence = _require_string(payload, "confidence").strip().lower()
        if confidence not in VALID_CONFIDENCE:
            raise ValueError(f"confidence must be one of {sorted(VALID_CONFIDENCE)}")
        source_type = _require_string(payload, "source_type").strip().lower()
        if source_type not in VALID_SOURCE_TYPES:
            raise ValueError("unsupported source_type")

        proposed = payload["proposed_citation"]
        if proposed is not None and not isinstance(proposed, str):
            raise ValueError("proposed_citation must be a string or null")
        if isinstance(proposed, str) and not proposed.strip():
            proposed = None

        missing_facts = payload["missing_facts"]
        if not isinstance(missing_facts, list) or not all(
            isinstance(item, str) and item.strip() for item in missing_facts
        ):
            raise ValueError("missing_facts must be a list of non-empty strings")
        facts_used = payload["facts_used"]
        if not isinstance(facts_used, dict):
            raise ValueError("facts_used must be an object")
        normalized_facts: dict[str, str] = {}
        for key, value in facts_used.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("facts_used keys must be non-empty strings")
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                raise ValueError("facts_used values must be strings or numbers")
            normalized_facts[key] = str(value)

        return cls(
            citation_text=_require_string(payload, "citation_text"),
            start=start,
            end=end,
            source_type=source_type,
            mode=mode,
            issue_code=_require_string(payload, "issue_code").strip().upper(),
            explanation=_require_string(payload, "explanation").strip(),
            confidence=confidence,
            proposed_citation=proposed,
            missing_facts=tuple(item.strip() for item in missing_facts),
            facts_used=normalized_facts,
        )


@dataclass(frozen=True)
class ProposalValidation:
    proposal: SLMProposal
    valid: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ProposalApplication:
    text: str
    applied: tuple[SLMProposal, ...]
    skipped: tuple[ProposalValidation, ...]


def _material_tokens(value: str) -> set[str]:
    normalized = value.casefold().replace(".", "")
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalized)
        if token not in _NON_MATERIAL_WORDS
    }


def validate_proposal(
    proposal: SLMProposal,
    text: str,
    *,
    expected_mode: str,
    expected_source_type: str | None = None,
) -> ProposalValidation:
    reasons: list[str] = []
    if proposal.mode != expected_mode:
        reasons.append("mode_mismatch")
    if expected_source_type and proposal.source_type != expected_source_type:
        reasons.append("source_type_mismatch")
    if proposal.end > len(text) or text[proposal.start : proposal.end] != proposal.citation_text:
        reasons.append("source_span_mismatch")

    explanation = proposal.explanation.casefold()
    if any(claim in explanation for claim in _PROHIBITED_CLAIMS):
        reasons.append("prohibited_legal_claim")

    if proposal.proposed_citation is not None:
        original_tokens = _material_tokens(proposal.citation_text)
        proposed_tokens = _material_tokens(proposal.proposed_citation)
        if proposed_tokens - original_tokens:
            reasons.append("unsupported_material_facts")

    return ProposalValidation(proposal, not reasons, tuple(reasons))


def apply_validated_proposals(
    text: str,
    proposals: Sequence[ProposalValidation],
) -> ProposalApplication:
    eligible = sorted(
        (
            result
            for result in proposals
            if result.valid
            and result.proposal.confidence == "high"
            and result.proposal.proposed_citation is not None
        ),
        key=lambda item: (item.proposal.start, item.proposal.end),
        reverse=True,
    )
    skipped = [
        result
        for result in proposals
        if not result.valid
        or result.proposal.confidence != "high"
        or result.proposal.proposed_citation is None
    ]
    accepted: list[ProposalValidation] = []
    intervals: list[tuple[int, int]] = []
    for result in eligible:
        span = (result.proposal.start, result.proposal.end)
        if any(span[0] < existing[1] and existing[0] < span[1] for existing in intervals):
            skipped.append(
                ProposalValidation(
                    result.proposal,
                    False,
                    result.reasons + ("overlapping_edit",),
                )
            )
            continue
        accepted.append(result)
        intervals.append(span)

    updated = text
    for result in accepted:
        proposal = result.proposal
        updated = (
            updated[: proposal.start]
            + str(proposal.proposed_citation)
            + updated[proposal.end :]
        )
    applied = tuple(
        result.proposal for result in sorted(accepted, key=lambda item: item.proposal.start)
    )
    return ProposalApplication(updated, applied, tuple(skipped))
