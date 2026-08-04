from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from eyecite import get_citations, resolve_citations
from eyecite.models import (
    FullCaseCitation,
    FullJournalCitation,
    FullLawCitation,
    IdCitation,
    ReferenceCitation,
    ShortCaseCitation,
    SupraCitation,
)

from .models import CitationMatch


def _text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _metadata(citation: Any, name: str) -> str | None:
    return _text(getattr(getattr(citation, "metadata", None), name, None))


def _with_present(**values: Any) -> dict[str, str]:
    return {
        key: normalized
        for key, value in values.items()
        if (normalized := _text(value)) is not None
    }


def _resource_map(citations: list[Any]) -> dict[int, str]:
    try:
        resolved = resolve_citations(citations)
    except (AttributeError, TypeError, ValueError):
        return {}

    ordered_groups = sorted(
        resolved.values(),
        key=lambda group: min(item.full_span()[0] for item in group),
    )
    mapping: dict[int, str] = {}
    for index, group in enumerate(ordered_groups, start=1):
        resource_id = f"resource-{index}"
        for citation in group:
            mapping[id(citation)] = resource_id
    return mapping


# eyecite's full_span() greedily absorbs *any* parenthetical immediately
# following a full citation, including a trailing "(hereinafter ...)"
# alias definition -- but that definition is always a separate clause, never
# part of the citation itself (unlike, e.g., a legitimate "(en banc)"
# parenthetical, which full_span() also absorbs and which genuinely is part
# of the citation -- there's no way to distinguish the two cases in general,
# so this only trims the unambiguous hereinafter case). Left untrimmed, the
# citation's own end swallows the hereinafter clause, so citation_graph.py's
# alias-registration overlap check (which requires the citation to end
# before the hereinafter clause starts) can never succeed, and the standard
# "Full Citation (hereinafter "Alias")" pattern silently fails to resolve.
_TRAILING_HEREINAFTER = re.compile(r"\s*\(hereinafter\s+[“\"][^”\"]+[”\"]\)\s*$", re.I)


def _trim_trailing_hereinafter(text: str, start: int, end: int) -> int:
    match = _TRAILING_HEREINAFTER.search(text, start, end)
    return match.start() if match else end


def _case_match(text: str, citation: FullCaseCitation, resource_id: str | None) -> CitationMatch:
    start, end = citation.full_span()
    end = _trim_trailing_hereinafter(text, start, end)
    core_start, _ = citation.span()
    case_name = text[start:core_start].strip().rstrip(",").strip()
    groups = citation.groups
    full_text = text[start:end]
    year = _metadata(citation, "year")
    if year and year not in full_text:
        # eyecite can leak a neighboring citation's year metadata onto this
        # one (observed when a preceding citation has a page-range plus
        # pincite, e.g. "215-423, 340"). Trust the year only when it's
        # actually present in this citation's own text -- never report a
        # fact this citation doesn't itself contain.
        year = None
    if case_name.startswith("("):
        # A citation embedded inside a sentence parenthetical, e.g.
        # California's in-line "(Case v. Case (Year) Vol Rep Page.)" form --
        # the enclosing parenthetical isn't part of the case name.
        case_name = case_name[1:].lstrip()
    if year and case_name.endswith(f"({year})"):
        case_name = case_name[: -(len(year) + 2)].strip()
    court = None
    if year:
        parenthetical = re.search(r"\((?P<body>[^()]*)\)$", full_text)
        if parenthetical:
            body = parenthetical.group("body").strip()
            if body.endswith(year):
                candidate = body[: -len(year)].strip()
                # A bare "(YYYY)" parenthetical leaves nothing before the
                # year -- no court, correctly excluded by the `candidate`
                # truthiness check below. A full "Month Day, YYYY)" date
                # (seen in less-formal citations) leaves e.g. "June 24,"
                # before the year, which is a date fragment, not a court.
                if candidate and not re.fullmatch(r"[A-Z][a-z]+ \d{1,2},", candidate):
                    court = candidate
    components = _with_present(
        case_name=case_name,
        volume=groups.get("volume"),
        reporter=groups.get("reporter"),
        first_page=groups.get("page"),
        pincite=_metadata(citation, "pin_cite"),
        year=year,
        court=court,
        resolved_to=resource_id,
    )
    return CitationMatch("case", text[start:end], start, end, components)


# eyecite's law-citation matcher builds the "section" group from a run of
# digits (optionally dotted, e.g. "1604.11") but stops as soon as it meets a
# digit immediately fused to a letter, e.g. the "10b" in "240.10b-5" or the
# "78j" in "78j(b)". When that happens it still returns a FullLawCitation --
# just truncated at the last fully-digit segment -- so the truncated span
# claims the region and the engine's own fallback regex (which would have
# captured the whole thing) never runs there, because CitationEngine.extract
# skips any fallback match that overlaps an already-claimed span.
#
# This pattern only fires directly after the digits eyecite already matched,
# and only extends when the character right after the dot is itself a digit.
# A sentence-ending period is always followed by whitespace/end-of-string,
# never by a digit, so it can never be absorbed by this extension.
_LAW_SECTION_CONTINUATION = re.compile(r"\.\d[\w]*(?:-[\w]+)*")


def _law_match(text: str, citation: FullLawCitation, resource_id: str | None) -> CitationMatch:
    start, end = citation.full_span()
    groups = citation.groups
    section = groups.get("section")
    continuation = _LAW_SECTION_CONTINUATION.match(text, end)
    if continuation:
        end = continuation.end()
        section = (section or "") + continuation.group(0)
    end = _trim_trailing_hereinafter(text, start, end)
    reporter = _text(groups.get("reporter")) or ""
    compact_reporter = re.sub(r"[.\s]", "", reporter).upper()
    source_type = "regulation" if compact_reporter == "CFR" else "statute"
    title = groups.get("title") or (groups.get("chapter") if source_type == "regulation" else None)
    components = _with_present(
        title=title,
        code=reporter,
        chapter=groups.get("chapter"),
        section=section,
        publisher=_metadata(citation, "publisher"),
        year=_metadata(citation, "year"),
        resolved_to=resource_id,
    )
    return CitationMatch(source_type, text[start:end], start, end, components)


def _journal_match(
    text: str, citation: FullJournalCitation, resource_id: str | None
) -> CitationMatch:
    start, end = citation.full_span()
    end = _trim_trailing_hereinafter(text, start, end)
    groups = citation.groups
    components = _with_present(
        volume=groups.get("volume"),
        journal=groups.get("reporter"),
        page=groups.get("page"),
        pincite=_metadata(citation, "pin_cite"),
        year=_metadata(citation, "year"),
        resolved_to=resource_id,
    )
    return CitationMatch("journal_article", text[start:end], start, end, components)


def _short_form_match(text: str, citation: Any, resource_id: str | None) -> CitationMatch:
    start, end = citation.full_span()
    if isinstance(citation, IdCitation):
        form = "id"
    elif isinstance(citation, SupraCitation):
        form = "supra"
    elif isinstance(citation, ShortCaseCitation):
        form = "short_case"
    else:
        form = "reference"
    components = _with_present(
        form=form,
        pincite=_metadata(citation, "pin_cite"),
        antecedent_guess=_metadata(citation, "antecedent_guess"),
        resolved_to=resource_id,
        parser="eyecite",
    )
    return CitationMatch("short_form", text[start:end], start, end, components)


def extract_eyecite_citations(text: str) -> list[CitationMatch]:
    """Extract recognized legal citations using Free Law Project's eyecite parser."""
    raw = list(get_citations(text))
    resources = _resource_map(raw)
    matches: list[CitationMatch] = []
    short_types = (IdCitation, SupraCitation, ShortCaseCitation, ReferenceCitation)

    for citation in raw:
        resource_id = resources.get(id(citation))
        if isinstance(citation, FullCaseCitation):
            matches.append(_case_match(text, citation, resource_id))
        elif isinstance(citation, FullLawCitation):
            matches.append(_law_match(text, citation, resource_id))
        elif isinstance(citation, FullJournalCitation):
            matches.append(_journal_match(text, citation, resource_id))
        elif isinstance(citation, short_types):
            matches.append(_short_form_match(text, citation, resource_id))

    return sorted(matches, key=lambda item: (item.start, item.end))


def overlaps(span: tuple[int, int], existing: Iterable[CitationMatch]) -> bool:
    start, end = span
    return any(start < item.end and end > item.start for item in existing)
