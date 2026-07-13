from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Pattern

from .extractors import extract_eyecite_citations, overlaps
from .models import CitationIssue, CitationMatch
from .rules import RULE_CATALOG, rule_reference, validate_mode


CASE_PATTERN = re.compile(
    r"(?P<case_name>[A-Z][^;\n]{1,100}?\s+v\.\s+[A-Z][^,;\n]{1,100}?),\s*"
    r"(?P<volume>\d{1,4})\s+(?P<reporter>[A-Za-z][A-Za-z.\d ]{0,18}?)\s+"
    r"(?P<first_page>\d{1,6})(?:,\s*(?P<pincite>\d{1,6}(?:[-–]\d{1,6})?))?\s*"
    r"\((?P<court_year>[^)]*\d{4})\)"
)
REPORTER_PATTERN = re.compile(
    r"\b(?P<volume>\d{1,4})\s+(?P<reporter>U\.?\s*S\.?|S\.?\s*Ct\.?|"
    r"F\.?\s*(?:Supp\.?\s*(?:2d|3d)?|2d|3d)|L\.?\s*Ed\.?\s*(?:2d)?)\s+"
    r"(?P<page>\d{1,6})\b",
    re.IGNORECASE,
)
STATUTE_PATTERN = re.compile(
    r"\b(?P<title>\d+)\s+(?P<code>U\.?\s*S\.?\s*C\.?)\s*"
    r"(?P<symbol>§{1,2})\s*(?P<section>[\w.\-()]+)",
    re.IGNORECASE,
)
REGULATION_PATTERN = re.compile(
    r"\b(?P<title>\d+)\s+(?P<code>C\.?\s*F\.?\s*R\.?)\s*"
    r"(?P<symbol>§{1,2})\s*(?P<section>[\w.\-()]+)",
    re.IGNORECASE,
)
CONSTITUTION_PATTERN = re.compile(
    r"\bU\.S\. Const\.\s+(?P<subdivision>(?:art\.|amend\.)\s+[IVXLCDM\d]+(?:,\s*§\s*\d+)?)",
    re.IGNORECASE,
)
SHORT_FORM_PATTERN = re.compile(r"\b(?P<form>id\.?|supra|hereinafter)\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s<>\])}]+")
JOURNAL_PATTERN = re.compile(
    r"\b(?P<volume>\d{1,3})\s+(?P<journal>[A-Z][A-Za-z.&'\- ]+L\.?\s*J\.?|"
    r"[A-Z][A-Za-z.&'\- ]+L\.?\s*Rev\.?)\s+(?P<page>\d{1,5})\b"
)


def _canonical_reporter(reporter: str) -> str:
    key = re.sub(r"[.\s]", "", reporter).upper()
    return {
        "US": "U.S.",
        "SCT": "S. Ct.",
        "F2D": "F.2d",
        "F3D": "F.3d",
        "FSUPP": "F. Supp.",
        "FSUPP2D": "F. Supp. 2d",
        "FSUPP3D": "F. Supp. 3d",
        "LED": "L. Ed.",
        "LED2D": "L. Ed. 2d",
    }.get(key, re.sub(r"\s+", " ", reporter.strip()))


def _issue(
    code: str,
    mode: str,
    start: int,
    end: int,
    original: str,
    *,
    message: str | None = None,
    suggestion: str | None = None,
    confidence: str = "medium",
) -> CitationIssue:
    metadata = RULE_CATALOG[code]
    return CitationIssue(
        code=code,
        severity=str(metadata["severity"]),
        message=message or str(metadata["description"]),
        rule=rule_reference(code, mode),
        start=start,
        end=end,
        original=original,
        suggestion=suggestion,
        confidence=confidence,
    )


class CitationEngine:
    """Conservative legal citation analyzer and mechanical fixer."""

    def extract(self, text: str) -> list[CitationMatch]:
        matches = extract_eyecite_citations(text)
        specs: list[tuple[str, Pattern[str]]] = [
            ("case", CASE_PATTERN),
            ("statute", STATUTE_PATTERN),
            ("regulation", REGULATION_PATTERN),
            ("constitution", CONSTITUTION_PATTERN),
            ("journal_article", JOURNAL_PATTERN),
            ("short_form", SHORT_FORM_PATTERN),
            ("internet", URL_PATTERN),
        ]
        for source_type, pattern in specs:
            for match in pattern.finditer(text):
                start, end = match.span()
                if overlaps((start, end), matches):
                    continue
                if source_type == "internet":
                    raw = match.group(0)
                    trimmed = raw.rstrip(".,;:")
                    end = start + len(trimmed)
                    raw = trimmed
                else:
                    raw = match.group(0)
                components = {
                    key: value
                    for key, value in match.groupdict().items()
                    if value is not None
                }
                matches.append(CitationMatch(source_type, raw, start, end, components))
        matches.sort(key=lambda item: (item.start, item.end))
        return matches

    def analyze(self, text: str, *, mode: str = "bluepages") -> dict[str, Any]:
        normalized_mode = validate_mode(mode)
        citations = self.extract(text)
        issues = self._lint(text, citations, normalized_mode)
        counts: dict[str, int] = {}
        for citation in citations:
            counts[citation.source_type] = counts.get(citation.source_type, 0) + 1
        return {
            "mode": normalized_mode,
            "citations": [asdict(item) for item in citations],
            "issues": [asdict(item) for item in issues],
            "summary": {
                "citation_count": len(citations),
                "issue_count": len(issues),
                "autofixable_count": sum(
                    1 for item in issues if item.suggestion and item.confidence == "high"
                ),
                "by_source_type": counts,
                "by_severity": {
                    severity: sum(1 for item in issues if item.severity == severity)
                    for severity in ("error", "warning", "info")
                },
            },
            "limitations": [
                "Formatting checks do not verify that quoted propositions are supported by the cited source.",
                "Missing source facts are never inferred.",
                "Case existence is checked only when CourtListener verification is separately requested.",
            ],
        }

    def fix(self, text: str, *, mode: str = "bluepages") -> dict[str, Any]:
        report = self.analyze(text, mode=mode)
        candidates = [
            issue
            for issue in report["issues"]
            if issue["suggestion"] is not None and issue["confidence"] == "high"
        ]
        candidates.sort(key=lambda item: (item["start"], item["end"]), reverse=True)
        fixed = text
        applied: list[dict[str, Any]] = []
        rightmost_start = len(text) + 1
        for issue in candidates:
            if issue["end"] > rightmost_start:
                continue
            fixed = fixed[: issue["start"]] + issue["suggestion"] + fixed[issue["end"] :]
            rightmost_start = issue["start"]
            applied.append(issue)
        applied.reverse()
        post_report = self.analyze(fixed, mode=mode)
        return {
            "mode": report["mode"],
            "original_text": text,
            "fixed_text": fixed,
            "applied_edits": applied,
            "remaining_issues": post_report["issues"],
            "summary": {
                "applied_edit_count": len(applied),
                "remaining_issue_count": len(post_report["issues"]),
            },
        }

    def _lint(
        self, text: str, citations: list[CitationMatch], mode: str
    ) -> list[CitationIssue]:
        issues: list[CitationIssue] = []

        for match in REPORTER_PATTERN.finditer(text):
            reporter = match.group("reporter")
            canonical = _canonical_reporter(reporter)
            original = match.group(0)
            suggestion = f"{match.group('volume')} {canonical} {match.group('page')}"
            if original != suggestion:
                issues.append(
                    _issue(
                        "REPORTER_ABBREVIATION",
                        mode,
                        *match.span(),
                        original,
                        suggestion=suggestion,
                        confidence="high",
                    )
                )

        for pattern, code, canonical_code in (
            (STATUTE_PATTERN, "STATUTE_CODE_ABBREVIATION", "U.S.C."),
            (REGULATION_PATTERN, "REGULATION_CODE_ABBREVIATION", "C.F.R."),
        ):
            for match in pattern.finditer(text):
                suggestion = (
                    f"{match.group('title')} {canonical_code} {match.group('symbol')} "
                    f"{match.group('section')}"
                )
                if match.group(0) != suggestion:
                    issues.append(
                        _issue(
                            code,
                            mode,
                            *match.span(),
                            match.group(0),
                            suggestion=suggestion,
                            confidence="high",
                        )
                    )

        for match in re.finditer(r"(?<!\w)id\.?(?!\w)", text, re.IGNORECASE):
            if match.group(0) != "Id.":
                issues.append(
                    _issue(
                        "SHORT_FORM_CAPITALIZATION",
                        mode,
                        *match.span(),
                        match.group(0),
                        suggestion="Id.",
                        confidence="high",
                    )
                )

        substantive = [
            item
            for item in citations
            if item.source_type not in {"short_form", "internet"}
        ]
        for citation in citations:
            if citation.source_type == "short_form":
                form = citation.components.get("form", citation.text).lower().rstrip(".")
                resolved_to = citation.components.get("resolved_to")
                if form == "id":
                    if citation.components.get("parser") == "eyecite":
                        orphaned = not resolved_to
                    else:
                        prior = [item for item in substantive if item.end < citation.start]
                        orphaned = not prior or citation.start - prior[-1].end > 500
                    if orphaned:
                        issues.append(
                            _issue(
                                "SHORT_FORM_ORPHAN_ID",
                                mode,
                                citation.start,
                                citation.end,
                                citation.text,
                                confidence="high",
                            )
                        )
                elif form in {"supra", "short_case", "reference"} and not resolved_to:
                    issues.append(
                        _issue(
                            "SHORT_FORM_UNRESOLVED",
                            mode,
                            citation.start,
                            citation.end,
                            citation.text,
                            confidence="high",
                        )
                    )
            if citation.source_type == "case" and not citation.components.get("pincite"):
                issues.append(
                    _issue(
                        "CASE_PINCITE_REVIEW",
                        mode,
                        citation.start,
                        citation.end,
                        citation.text,
                        confidence="low",
                    )
                )
            if citation.source_type == "internet" and mode == "whitepages":
                nearby = text[max(0, citation.start - 120) : min(len(text), citation.end + 160)]
                if "perma.cc" not in nearby.lower() and "on file with author" not in nearby.lower():
                    issues.append(
                        _issue(
                            "INTERNET_ARCHIVE_REVIEW",
                            mode,
                            citation.start,
                            citation.end,
                            citation.text,
                            confidence="medium",
                        )
                    )

        unique: dict[tuple[str, int, int, str | None], CitationIssue] = {}
        for item in issues:
            unique[(item.code, item.start, item.end, item.suggestion)] = item
        return sorted(unique.values(), key=lambda item: (item.start, item.end, item.code))
