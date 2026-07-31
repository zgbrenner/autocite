from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ContextSpan:
    start: int
    end: int
    text: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReducedCitationContext:
    text: str
    spans: tuple[ContextSpan, ...]
    protected_spans: tuple[ContextSpan, ...]
    input_chars: int
    output_chars: int
    compression_ratio: float
    bypassed: bool
    original_sha256: str
    reducer: str = "deterministic_legal_context_v1"

    @property
    def saved_chars(self) -> int:
        return self.input_chars - self.output_chars

    def as_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "spans": [span.as_dict() for span in self.spans],
            "protected_spans": [span.as_dict() for span in self.protected_spans],
            "input_chars": self.input_chars,
            "output_chars": self.output_chars,
            "saved_chars": self.saved_chars,
            "compression_ratio": self.compression_ratio,
            "bypassed": self.bypassed,
            "original_sha256": self.original_sha256,
            "reducer": self.reducer,
        }


class ContextReducer(Protocol):
    def reduce(
        self,
        text: str,
        *,
        focus_start: int,
        focus_end: int,
    ) -> ReducedCitationContext: ...


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for match in re.finditer(r"\n[ \t]*\n", text):
        start, end = cursor, match.start()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            spans.append((start, end))
        cursor = match.end()
    start, end = cursor, len(text)
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start < end:
        spans.append((start, end))
    return spans


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
    return merged


class DeterministicLegalContextReducer:
    """Select bounded, traceable context without rewriting legal text."""

    def __init__(
        self,
        *,
        max_chars: int = 2_400,
        minimum_savings_ratio: float = 0.12,
        adjacent_paragraphs: int = 1,
    ) -> None:
        if max_chars < 128:
            raise ValueError("max_chars must be at least 128")
        if not 0 <= minimum_savings_ratio < 1:
            raise ValueError("minimum_savings_ratio must be between 0 and 1")
        if adjacent_paragraphs < 0 or adjacent_paragraphs > 4:
            raise ValueError("adjacent_paragraphs must be between 0 and 4")
        self.max_chars = max_chars
        self.minimum_savings_ratio = minimum_savings_ratio
        self.adjacent_paragraphs = adjacent_paragraphs

    @staticmethod
    def _bypass(
        text: str,
        *,
        focus_start: int,
        focus_end: int,
        original_sha256: str,
    ) -> ReducedCitationContext:
        whole = ContextSpan(0, len(text), text, "bypass_full_document")
        protected = ContextSpan(
            focus_start,
            focus_end,
            text[focus_start:focus_end],
            "exact_focus",
        )
        return ReducedCitationContext(
            text=text,
            spans=(whole,),
            protected_spans=(protected,),
            input_chars=len(text),
            output_chars=len(text),
            compression_ratio=1.0,
            bypassed=True,
            original_sha256=original_sha256,
        )

    def reduce(
        self,
        text: str,
        *,
        focus_start: int,
        focus_end: int,
    ) -> ReducedCitationContext:
        if (
            focus_start < 0
            or focus_end <= focus_start
            or focus_end > len(text)
        ):
            raise ValueError("focus range must identify text inside the document")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if len(text) <= self.max_chars:
            return self._bypass(
                text,
                focus_start=focus_start,
                focus_end=focus_end,
                original_sha256=digest,
            )

        paragraphs = _paragraph_spans(text)
        focus_index = next(
            (
                index
                for index, (start, end) in enumerate(paragraphs)
                if start < focus_end and end > focus_start
            ),
            None,
        )
        if focus_index is None:
            candidate_ranges = [(focus_start, focus_end)]
        else:
            lower = max(0, focus_index - self.adjacent_paragraphs)
            upper = min(
                len(paragraphs),
                focus_index + self.adjacent_paragraphs + 1,
            )
            candidate_ranges = paragraphs[lower:upper]

        merged = _merge_ranges(candidate_ranges)
        separator = "\n\n[… omitted, available from original …]\n\n"
        selected_length = sum(end - start for start, end in merged)
        selected_length += len(separator) * max(0, len(merged) - 1)

        if selected_length > self.max_chars:
            focus_paragraph = (
                paragraphs[focus_index]
                if focus_index is not None
                else (focus_start, focus_end)
            )
            paragraph_start, paragraph_end = focus_paragraph
            focus_length = focus_end - focus_start
            remaining = max(0, self.max_chars - focus_length)
            before = min(focus_start - paragraph_start, remaining // 2)
            after = min(paragraph_end - focus_end, remaining - before)
            unused = remaining - before - after
            if unused:
                grow_before = min(
                    focus_start - paragraph_start - before,
                    unused,
                )
                before += grow_before
                unused -= grow_before
                after += min(paragraph_end - focus_end - after, unused)
            merged = [(focus_start - before, focus_end + after)]

        spans = tuple(
            ContextSpan(
                start,
                end,
                text[start:end],
                "selected_paragraph_context",
            )
            for start, end in merged
        )
        reduced_text = separator.join(span.text for span in spans)
        output_chars = len(reduced_text)
        ratio = output_chars / len(text) if text else 1.0
        savings_ratio = 1.0 - ratio
        if savings_ratio < self.minimum_savings_ratio:
            return self._bypass(
                text,
                focus_start=focus_start,
                focus_end=focus_end,
                original_sha256=digest,
            )

        protected = ContextSpan(
            focus_start,
            focus_end,
            text[focus_start:focus_end],
            "exact_focus",
        )
        return ReducedCitationContext(
            text=reduced_text,
            spans=spans,
            protected_spans=(protected,),
            input_chars=len(text),
            output_chars=output_chars,
            compression_ratio=ratio,
            bypassed=False,
            original_sha256=digest,
        )
