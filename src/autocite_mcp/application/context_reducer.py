from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceRange:
    start: int
    end: int
    reason: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError("Invalid source range")


@dataclass(frozen=True, slots=True)
class ReductionMetrics:
    original_characters: int
    reduced_characters: int
    savings_ratio: float
    bypassed: bool
    bypass_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReducedContext:
    text: str
    source_hash: str
    selected_ranges: list[SourceRange]
    protected_ranges: list[SourceRange]
    metrics: ReductionMetrics
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source_hash": self.source_hash,
            "selected_ranges": [asdict(item) for item in self.selected_ranges],
            "protected_ranges": [asdict(item) for item in self.protected_ranges],
            "metrics": self.metrics.to_dict(),
            "metadata": self.metadata,
        }

    def reconstruct_selected_text(self, original: str) -> str:
        expected = sha256(original.encode("utf-8")).hexdigest()
        if expected != self.source_hash:
            raise ValueError("The supplied original does not match this reduction")
        return _join_ranges(original, self.selected_ranges)


class ContextReducer(ABC):
    @abstractmethod
    def reduce(
        self,
        text: str,
        *,
        focus_spans: list[tuple[int, int]] | None = None,
        max_characters: int | None = None,
    ) -> ReducedContext:
        raise NotImplementedError


class NoopContextReducer(ContextReducer):
    def reduce(
        self,
        text: str,
        *,
        focus_spans: list[tuple[int, int]] | None = None,
        max_characters: int | None = None,
    ) -> ReducedContext:
        source_range = SourceRange(0, len(text), "no_reduction")
        return ReducedContext(
            text=text,
            source_hash=sha256(text.encode("utf-8")).hexdigest(),
            selected_ranges=[source_range],
            protected_ranges=[],
            metrics=ReductionMetrics(
                original_characters=len(text),
                reduced_characters=len(text),
                savings_ratio=0.0,
                bypassed=True,
                bypass_reason="disabled",
            ),
            metadata={"strategy": "none"},
        )


class DeterministicLegalContextReducer(ContextReducer):
    """Conservative paragraph selection for bounded legal review tasks.

    The reducer never rewrites or summarizes text.  It selects exact source
    ranges and returns an auditable map back to the original.  Citation-like
    strings, cross-reference terms, headings, quoted passages, and supplied
    focus spans become protected anchors.  Adjacent paragraphs are included
    to retain propositions and antecedents.
    """

    _PROTECTED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "case_citation",
            re.compile(
                r"\b\d{1,4}\s+(?:U\.S\.|S\.\s*Ct\.|L\.\s*Ed\.\s*2d|"
                r"F\.\s?(?:2d|3d|4th)|F\.\s*Supp\.\s?(?:2d|3d)?|"
                r"P\.\s?(?:2d|3d)|N\.E\.\s?(?:2d|3d)|S\.E\.\s?(?:2d)?|"
                r"So\.\s?(?:2d|3d)|N\.W\.\s?(?:2d)?|A\.\s?(?:2d|3d)|"
                r"Cal\.\s?(?:2d|3d|4th|5th|App\.)?)\s+\d{1,6}\b",
                re.IGNORECASE,
            ),
        ),
        (
            "statute_or_regulation",
            re.compile(
                r"\b\d+\s+(?:U\.S\.C\.|C\.F\.R\.|Cal\.\s+[A-Za-z. ]+\s+Code)"
                r"\s*§{1,2}\s*[\w.()\-–]+",
                re.IGNORECASE,
            ),
        ),
        (
            "short_form",
            re.compile(
                r"\b(?:Id\.|Ibid\.|supra|infra|hereinafter|see\s+also|cf\.)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "court_and_year",
            re.compile(
                r"\((?:[A-Z][A-Za-z. ]+\s+)?(?:Cir\.|Ct\.|App\.|"
                r"Sup\.\s*Ct\.)?\s*\d{4}\)"
            ),
        ),
        (
            "page_marker",
            re.compile(r"(?<!\w)(?:at\s+)?\*?\d{1,6}(?:[–-]\d{1,6})?(?!\w)"),
        ),
        (
            "quotation",
            re.compile(r"[“\"](?:[^”\"\n]|\n(?!\n)){8,}[”\"]"),
        ),
        (
            "footnote_marker",
            re.compile(r"(?m)^(?:\[\^?\d+\]|\d+\.)\s+"),
        ),
    )

    _HEADING_PATTERN = re.compile(
        r"(?m)^(?:#{1,6}\s+.+|[IVXLC]+\.\s+.+|[A-Z]\.\s+.+|"
        r"[A-Z][A-Z0-9 ,:'()\-]{5,})$"
    )

    def __init__(
        self,
        *,
        neighbor_paragraphs: int = 1,
        default_max_characters: int = 12_000,
        minimum_savings_ratio: float = 0.12,
    ) -> None:
        self.neighbor_paragraphs = max(0, neighbor_paragraphs)
        self.default_max_characters = max(1_000, default_max_characters)
        self.minimum_savings_ratio = max(0.0, min(minimum_savings_ratio, 0.95))

    def reduce(
        self,
        text: str,
        *,
        focus_spans: list[tuple[int, int]] | None = None,
        max_characters: int | None = None,
    ) -> ReducedContext:
        source_hash = sha256(text.encode("utf-8")).hexdigest()
        if not text:
            return ReducedContext(
                text="",
                source_hash=source_hash,
                selected_ranges=[],
                protected_ranges=[],
                metrics=ReductionMetrics(0, 0, 0.0, True, "empty_input"),
                metadata={"strategy": "deterministic_legal"},
            )

        budget = max(1_000, max_characters or self.default_max_characters)
        paragraphs = _paragraph_ranges(text)
        protected = self._find_protected_ranges(text, focus_spans or [])

        if len(text) <= budget:
            complete = SourceRange(0, len(text), "within_budget")
            return ReducedContext(
                text=text,
                source_hash=source_hash,
                selected_ranges=[complete],
                protected_ranges=protected,
                metrics=ReductionMetrics(
                    len(text), len(text), 0.0, True, "within_budget"
                ),
                metadata={
                    "strategy": "deterministic_legal",
                    "budget": budget,
                    "paragraph_count": len(paragraphs),
                },
            )

        selected_indices: set[int] = set()
        protected_indices: set[int] = set()
        for protected_range in protected:
            for index, paragraph in enumerate(paragraphs):
                if _overlaps(paragraph, protected_range):
                    protected_indices.add(index)
                    start = max(0, index - self.neighbor_paragraphs)
                    stop = min(len(paragraphs), index + self.neighbor_paragraphs + 1)
                    selected_indices.update(range(start, stop))

        # If no legal anchors were detected, retain the opening and closing
        # paragraphs rather than attempting an unconstrained summary.
        if not selected_indices:
            selected_indices.update(range(min(3, len(paragraphs))))
            if len(paragraphs) > 3:
                selected_indices.add(len(paragraphs) - 1)

        selected_indices = self._fit_budget(
            text,
            paragraphs,
            selected_indices,
            protected_indices,
            budget,
        )
        selected_ranges = _merge_ranges(
            [
                SourceRange(
                    paragraphs[index].start,
                    paragraphs[index].end,
                    "protected_context"
                    if index in protected_indices
                    else "neighbor_context",
                )
                for index in sorted(selected_indices)
            ]
        )
        reduced_text = _join_ranges(text, selected_ranges)
        savings = 1.0 - (len(reduced_text) / len(text))

        if savings < self.minimum_savings_ratio:
            complete = SourceRange(0, len(text), "negligible_savings")
            return ReducedContext(
                text=text,
                source_hash=source_hash,
                selected_ranges=[complete],
                protected_ranges=protected,
                metrics=ReductionMetrics(
                    len(text),
                    len(text),
                    0.0,
                    True,
                    "negligible_savings",
                ),
                metadata={
                    "strategy": "deterministic_legal",
                    "budget": budget,
                    "candidate_savings_ratio": round(savings, 6),
                },
            )

        return ReducedContext(
            text=reduced_text,
            source_hash=source_hash,
            selected_ranges=selected_ranges,
            protected_ranges=protected,
            metrics=ReductionMetrics(
                original_characters=len(text),
                reduced_characters=len(reduced_text),
                savings_ratio=round(savings, 6),
                bypassed=False,
            ),
            metadata={
                "strategy": "deterministic_legal",
                "budget": budget,
                "paragraph_count": len(paragraphs),
                "selected_paragraph_count": len(selected_indices),
                "reversible": True,
            },
        )

    def _find_protected_ranges(
        self, text: str, focus_spans: list[tuple[int, int]]
    ) -> list[SourceRange]:
        ranges: list[SourceRange] = []
        for start, end in focus_spans:
            bounded_start = max(0, min(int(start), len(text)))
            bounded_end = max(bounded_start, min(int(end), len(text)))
            if bounded_start != bounded_end:
                ranges.append(SourceRange(bounded_start, bounded_end, "explicit_focus"))

        for reason, pattern in self._PROTECTED_PATTERNS:
            ranges.extend(
                SourceRange(match.start(), match.end(), reason)
                for match in pattern.finditer(text)
            )
        ranges.extend(
            SourceRange(match.start(), match.end(), "heading")
            for match in self._HEADING_PATTERN.finditer(text)
        )
        return _merge_ranges(ranges, preserve_reasons=True)

    @staticmethod
    def _fit_budget(
        text: str,
        paragraphs: list[SourceRange],
        selected: set[int],
        protected: set[int],
        budget: int,
    ) -> set[int]:
        def selected_length(indices: set[int]) -> int:
            if not indices:
                return 0
            ranges = _merge_ranges(
                [
                    SourceRange(paragraphs[index].start, paragraphs[index].end, "budget")
                    for index in sorted(indices)
                ]
            )
            return len(_join_ranges(text, ranges))

        if selected_length(selected) <= budget:
            return selected

        # Remove the farthest nonprotected neighbors first. Protected anchor
        # paragraphs are never discarded, even when they exceed the budget.
        anchor_indices = protected or selected
        removable = [index for index in selected if index not in protected]
        removable.sort(
            key=lambda index: min(abs(index - anchor) for anchor in anchor_indices),
            reverse=True,
        )
        result = set(selected)
        for index in removable:
            if selected_length(result) <= budget:
                break
            result.remove(index)
        return result


def _paragraph_ranges(text: str) -> list[SourceRange]:
    ranges: list[SourceRange] = []
    cursor = 0
    for match in re.finditer(r"\n\s*\n+", text):
        end = match.end()
        if end > cursor:
            ranges.append(SourceRange(cursor, end, "paragraph"))
        cursor = end
    if cursor < len(text):
        ranges.append(SourceRange(cursor, len(text), "paragraph"))
    if not ranges:
        ranges.append(SourceRange(0, len(text), "paragraph"))
    return ranges


def _overlaps(left: SourceRange, right: SourceRange) -> bool:
    return left.start < right.end and right.start < left.end


def _merge_ranges(
    ranges: list[SourceRange], *, preserve_reasons: bool = False
) -> list[SourceRange]:
    if not ranges:
        return []
    ordered = sorted(ranges, key=lambda item: (item.start, item.end))
    merged: list[SourceRange] = [ordered[0]]
    for current in ordered[1:]:
        previous = merged[-1]
        if current.start <= previous.end:
            reasons = {previous.reason, current.reason}
            reason = "+".join(sorted(reasons)) if preserve_reasons else previous.reason
            merged[-1] = SourceRange(
                previous.start,
                max(previous.end, current.end),
                reason,
            )
        else:
            merged.append(current)
    return merged


def _join_ranges(text: str, ranges: list[SourceRange]) -> str:
    if not ranges:
        return ""
    chunks: list[str] = []
    previous_end: int | None = None
    for item in ranges:
        if previous_end is not None and item.start > previous_end:
            chunks.append("\n\n[… exact source omitted by context reducer …]\n\n")
        chunks.append(text[item.start : item.end])
        previous_end = item.end
    return "".join(chunks)
