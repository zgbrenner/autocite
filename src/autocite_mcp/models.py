from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CitationMatch:
    source_type: str
    text: str
    start: int
    end: int
    components: dict[str, str]


@dataclass(frozen=True)
class CitationIssue:
    code: str
    severity: str
    message: str
    rule: str
    start: int
    end: int
    original: str
    suggestion: str | None = None
    confidence: str = "medium"
