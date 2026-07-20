from __future__ import annotations

import bisect
import heapq
import re
from dataclasses import asdict
from typing import Any, Pattern

from .extractors import extract_eyecite_citations
from .models import CitationIssue, CitationMatch
from .rules import RULE_CATALOG, rule_reference, validate_mode

# Source types that can serve as the antecedent of an "id"/"Id." short form.
_SUBSTANTIVE_SOURCE_TYPES = frozenset(
    {"case", "statute", "regulation", "constitution", "journal_article"}
)
# How far before a bare "Id." a real authority may sit and still be its
# antecedent. Mirrors the window used by the SHORT_FORM_ORPHAN_ID check below.
_ID_ANTECEDENT_WINDOW = 500


CASE_PATTERN = re.compile(
    r"(?P<case_name>[A-Z][^;\n]{1,100}?\s+v\.\s+[A-Z][^,;\n]{1,100}?),\s*"
    r"(?P<volume>\d{1,4})\s+(?P<reporter>[A-Za-z][A-Za-z.\d ]{0,18}?)\s+"
    r"(?P<first_page>\d{1,6})(?:,\s*(?P<pincite>\d{1,6}(?:[-–]\d{1,6})?))?\s*"
    r"\((?P<court_year>[^)]*\d{4})\)"
)
# Reporter tokens tolerate spaces on *either* side of their periods so a
# mis-spaced abbreviation ("U . S .", "F . Supp . 2d") is still recognized and
# normalized. _canonical_reporter strips both periods and spaces, so any spacing
# variant collapses to the same canonical form. Internal spacing is bounded
# (never more than a stray space or two in a real abbreviation) so the pattern
# cannot backtrack super-linearly on a run of whitespace.
REPORTER_PATTERN = re.compile(
    r"\b(?P<volume>\d{1,4})\s+(?P<reporter>U\s{0,2}\.?\s{0,2}S\s{0,2}\.?|"
    r"S\s{0,2}\.?\s{0,2}Ct\s{0,2}\.?|"
    r"F\s{0,2}\.?\s{0,2}(?:Supp\s{0,2}\.?\s{0,2}(?:2d|3d)?|2d|3d)|F\s{0,2}\.|"
    r"L\s{0,2}\.?\s{0,2}Ed\s{0,2}\.?\s{0,2}(?:2d)?)\s+"
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
SHORT_FORM_PATTERN = re.compile(r"\b(?P<form>supra|hereinafter)\b", re.IGNORECASE)
ID_PATTERN = re.compile(r"(?<!\w)(?P<form>id)\.?(?!\w)", re.IGNORECASE)
ID_TOKEN_PATTERN = re.compile(r"id\.?", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s<>\])}]+")
JOURNAL_PATTERN = re.compile(
    r"\b(?P<volume>\d{1,3})\s+(?P<journal>[A-Z][A-Za-z.&'\- ]+L\.?\s*J\.?|"
    r"[A-Z][A-Za-z.&'\- ]+L\.?\s*Rev\.?)\s+(?P<page>\d{1,5})\b"
)


def _looks_like_id_citation(
    text: str,
    start: int,
    end: int,
    has_prior_citation: bool,
    *,
    has_pincite: bool = False,
) -> bool:
    """Require "id."/"Id." to appear in an actual citation context.

    The bare English word "id" (an identifier, the Freudian id, a shorthand for
    "identification") is never a citation short form. "id." counts as a citation
    short form when it is:

    * followed by a pincite (e.g. "id. at 5" or "id., at 100"), or
    * preceded by a citation signal (e.g. "See id."), or
    * placed at the start of a citation sentence and either written in
      citation-shaped "Id."/"id." form (a trailing period) or preceded, within a
      bounded window, by a real authority it can refer back to.

    The trailing-period distinction matters in two directions. A period-less
    sentence-initial "Id"/"id" with no antecedent is ordinary prose (e.g. "The
    id, ego, and superego ... Id represents primitive instinct.") and must never
    be rewritten to "Id." -- that would silently insert a period into
    non-citation text. But a period-terminated "Id." with no antecedent is a
    genuinely orphaned short form (a real B4/Rule 4 defect), so it is still
    recognized here and left for the orphan check to flag rather than dropped.
    """
    after = text[end : end + 40]
    if has_pincite or re.match(r"\s*,?\s*at\s+\d", after, re.IGNORECASE):
        return True
    before = text[max(0, start - 60) : start]
    if re.search(
        r"\b(?:see also|see generally|but see|but cf\.?|see|cf\.?|accord|compare|e\.g\.)\s*$",
        before,
        re.IGNORECASE,
    ):
        return True
    at_citation_boundary = (not before.strip()) or bool(
        re.search(r"[.!?][\"'”)\]]?\s*$", before)
    )
    if not at_citation_boundary:
        return False
    if text[start:end].rstrip().endswith("."):
        return True
    return has_prior_citation


def _union(sorted_spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Collapse start-sorted spans into a non-overlapping coverage union.

    eyecite can return spans that nest or overlap (e.g. a full case citation
    that contains a short reference), so the raw accepted spans are not
    guaranteed disjoint. Merging them into a coverage union lets the fallback
    overlap test stay a simple linear sweep while preserving the original
    "reject any fallback match that overlaps any accepted match" semantics.
    """
    merged: list[tuple[int, int]] = []
    for start, end in sorted_spans:
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def _canonical_reporter(reporter: str) -> str:
    key = re.sub(r"[.\s]", "", reporter).upper()
    return {
        "US": "U.S.",
        "SCT": "S. Ct.",
        "F": "F.",
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
        correction_level=(
            "safe_auto_fix"
            if metadata.get("autofix") and suggestion is not None and confidence == "high"
            else "review_required"
        ),
    )


class CitationEngine:
    """Conservative legal citation analyzer and mechanical fixer."""

    def extract(self, text: str) -> list[CitationMatch]:
        matches = list(extract_eyecite_citations(text))
        # ``intervals`` and ``substantive_ends`` are kept sorted so overlap and
        # antecedent checks are O(log n) instead of a linear scan of every
        # already-accepted match. Each fallback spec is applied as one ordered
        # batch (regex finditer yields non-overlapping matches in start order),
        # so the whole extraction is O(n log n) rather than the previous
        # O(n^2), which let a citation-dense document hang the server.
        intervals: list[tuple[int, int]] = _union(
            sorted((item.start, item.end) for item in matches)
        )
        substantive_ends: list[int] = sorted(
            item.end for item in matches if item.source_type in _SUBSTANTIVE_SOURCE_TYPES
        )

        def _has_prior_citation(position: int) -> bool:
            lo = bisect.bisect_left(substantive_ends, position - _ID_ANTECEDENT_WINDOW)
            hi = bisect.bisect_right(substantive_ends, position)
            return hi > lo

        specs: list[tuple[str, Pattern[str]]] = [
            ("case", CASE_PATTERN),
            ("statute", STATUTE_PATTERN),
            ("regulation", REGULATION_PATTERN),
            ("constitution", CONSTITUTION_PATTERN),
            ("journal_article", JOURNAL_PATTERN),
            ("short_form", SHORT_FORM_PATTERN),
            ("short_form", ID_PATTERN),
            ("internet", URL_PATTERN),
        ]
        for source_type, pattern in specs:
            new_matches: list[CitationMatch] = []
            new_intervals: list[tuple[int, int]] = []
            pointer = 0
            for match in pattern.finditer(text):
                start, end = match.span()
                # Advance past accepted intervals that end at/before this match,
                # then reject the match if the next accepted interval overlaps it.
                while pointer < len(intervals) and intervals[pointer][1] <= start:
                    pointer += 1
                if pointer < len(intervals) and intervals[pointer][0] < end:
                    continue
                if pattern is ID_PATTERN and not _looks_like_id_citation(
                    text, start, end, _has_prior_citation(start)
                ):
                    continue
                if source_type == "internet":
                    raw = match.group(0).rstrip(".,;:")
                    end = start + len(raw)
                else:
                    raw = match.group(0)
                components = {
                    key: value
                    for key, value in match.groupdict().items()
                    if value is not None
                }
                new_matches.append(CitationMatch(source_type, raw, start, end, components))
                new_intervals.append((start, end))
            if new_matches:
                matches.extend(new_matches)
                intervals = _union(list(heapq.merge(intervals, new_intervals)))
                if source_type in _SUBSTANTIVE_SOURCE_TYPES:
                    substantive_ends = list(
                        heapq.merge(substantive_ends, [span[1] for span in new_intervals])
                    )

        # eyecite emits IdCitation objects without the citation-context gate the
        # fallback ID_PATTERN passes through, so a bare English "id." (e.g.
        # "enter your password id.") could slip in as a short-form citation.
        # Drop eyecite-provided bare "id" short forms that lack citation context.
        kept: list[CitationMatch] = []
        for item in matches:
            if (
                item.source_type == "short_form"
                and item.components.get("parser") == "eyecite"
                and (item.components.get("form") or "").lower().rstrip(".") == "id"
                and not _looks_like_id_citation(
                    text,
                    item.start,
                    item.end,
                    _has_prior_citation(item.start),
                    has_pincite=bool(item.components.get("pincite")),
                )
            ):
                continue
            kept.append(item)
        kept.sort(key=lambda item: (item.start, item.end))
        return kept

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
            if issue["suggestion"] is not None
            and issue["confidence"] == "high"
            and issue["correction_level"] == "safe_auto_fix"
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

        for citation in citations:
            if citation.source_type != "short_form":
                continue
            form = citation.components.get("form", citation.text).lower().rstrip(".")
            if form != "id":
                continue
            token = ID_TOKEN_PATTERN.match(citation.text)
            if token is None or token.group(0) == "Id.":
                continue
            issues.append(
                _issue(
                    "SHORT_FORM_CAPITALIZATION",
                    mode,
                    citation.start + token.start(),
                    citation.start + token.end(),
                    token.group(0),
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
