from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from .document_ir import CitationLocation, DocumentIR, locate_citations
from .engine import CitationEngine


CASE_FULL = re.compile(
    r"(?P<name>[A-Z][^;\n]{1,100}?\s+v\.\s+[A-Z][^,;\n]{1,100}?),\s*"
    r"(?P<volume>\d{1,4})\s+(?P<reporter>[A-Za-z.\d ]+?)\s+(?P<page>\d{1,6})",
)
SHORT_CASE = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z0-9.&' -]{1,50}),\s*"
    r"(?P<volume>\d{1,4})\s+(?P<reporter>U\.S\.|F\.(?:2d|3d|Supp\.?(?: 2d| 3d)?))\s+"
    r"at\s+(?P<pincite>\d{1,6}(?:[-–—]\d{1,6})?)\b"
)
ID_FORM = re.compile(r"\bId\.(?:\s+at\s+\d{1,6}(?:[-–—]\d{1,6})?)?", re.I)
SUPRA_NOTE = re.compile(
    r"\b(?P<label>[A-Z][A-Za-z0-9.&' -]{0,60}?),\s+supra\s+note\s+(?P<note>\d+)"
    r"(?:,\s*at\s+\d{1,6}(?:[-–—]\d{1,6})?)?",
    re.I,
)
SUPRA = re.compile(
    r"\b(?P<label>[A-Z][A-Za-z0-9.&' -]{0,60}?),\s+supra(?:,\s*at\s+\d{1,6}(?:[-–—]\d{1,6})?)?",
    re.I,
)
STATUTORY_SHORT = re.compile(
    r"(?:(?P<code>U\.?\s*S\.?\s*C\.?|C\.?\s*F\.?\s*R\.?)\s+)?"
    r"(?<![A-Za-z.\d])§{1,2}\s*(?P<section>[\w.()\-]+)",
    re.IGNORECASE,
)
HEREINAFTER_DEF = re.compile(r"\(hereinafter\s+[“\"](?P<alias>[^”\"]+)[”\"]\)", re.I)
ARTICLE_CONTEXT = re.compile(
    r"(?P<author>[A-Z][A-Za-z.' -]+),\s*(?P<title>[^,]{2,100}),\s*$"
)
PERMITTED_SUPRA_TYPES = {
    "journal_article",
    "book",
    "court_document",
    "administrative",
    "internet",
    "archival",
    "foreign_international_tribal",
    "ai_content",
    "unknown",
}


@dataclass(frozen=True)
class AuthorityNode:
    authority_id: str
    source_type: str
    identity_key: tuple[str, ...]
    display_name: str
    components: Mapping[str, str]
    identity_confidence: str
    provenance: str = "deterministic_logic"


@dataclass(frozen=True)
class OccurrenceNode:
    occurrence_id: str
    citation_text: str
    start: int
    end: int
    source_type: str
    form: str
    document_order: int
    location: CitationLocation
    components: Mapping[str, str]
    authority_id: str | None = None


@dataclass(frozen=True)
class CitationEdge:
    edge_type: str
    source_id: str
    target_id: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    provenance: str = "parsed_document_structure"


@dataclass(frozen=True)
class AntecedentCandidate:
    authority_id: str
    occurrence_id: str
    score: int
    supporting_facts: tuple[str, ...]
    disqualifying_facts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolutionResult:
    occurrence_id: str
    form: str
    resolved_authority_id: str | None
    resolution_method: str
    candidates: tuple[AntecedentCandidate, ...]
    confidence: str
    disqualifying_facts: tuple[str, ...]
    rule_profile: str
    human_review_required: bool
    provenance: str


@dataclass(frozen=True)
class CitationGraph:
    authorities: tuple[AuthorityNode, ...]
    occurrences: tuple[OccurrenceNode, ...]
    edges: tuple[CitationEdge, ...]
    resolutions: tuple[ResolutionResult, ...]
    mode: str
    version: str = "1.0"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _RawOccurrence:
    text: str
    start: int
    end: int
    source_type: str
    form: str
    location: CitationLocation
    components: dict[str, str]
    logical_key: tuple[int, int, int]


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _reporter(value: Any) -> str:
    return re.sub(r"[.\s]", "", str(value or "")).upper()


def _authority_id(source_type: str, key: Sequence[str]) -> str:
    digest = hashlib.sha256((source_type + "\x1f" + "\x1f".join(key)).encode()).hexdigest()[:16]
    return f"authority:{source_type}:{digest}"


def _location(ir: DocumentIR, start: int, end: int) -> CitationLocation:
    block = ir.block_at(start)
    contained = bool(block and end <= block.absolute_end)
    return CitationLocation(
        block_id=block.block_id if contained and block else None,
        block_kind=block.kind if contained and block else None,
        absolute_start=start,
        absolute_end=end,
        block_local_start=start - block.absolute_start if contained and block else None,
        block_local_end=end - block.absolute_start if contained and block else None,
        note_id=block.note_id if contained and block else None,
        note_number=block.note_number if contained and block else None,
        page_number=block.page_number if contained and block else None,
        reconstruction_confidence=block.reconstruction_confidence if contained and block else "low",
        provenance="parsed_document_structure" if contained else "unresolved_ambiguity",
    )


def _logical_key(ir: DocumentIR, location: CitationLocation, start: int) -> tuple[int, int, int]:
    if location.note_id:
        references = [
            block
            for block in ir.blocks
            if block.kind in {"footnote_reference", "endnote_reference"}
            and block.note_id == location.note_id
        ]
        if references:
            local = location.block_local_start or 0
            return (min(item.absolute_start for item in references), 1, local)
    return (start, 0, 0)


def _raw_occurrences(ir: DocumentIR) -> list[_RawOccurrence]:
    raw: list[_RawOccurrence] = []
    for citation in locate_citations(ir, CitationEngine()):
        if citation.source_type == "short_form":
            continue
        components = {key: str(value) for key, value in citation.components.items()}
        raw.append(
            _RawOccurrence(
                citation.text,
                citation.start,
                citation.end,
                citation.source_type,
                "full",
                citation.location,
                components,
                _logical_key(ir, citation.location, citation.start),
            )
        )

    custom: list[tuple[re.Pattern[str], str, str]] = [
        (SUPRA_NOTE, "short_form", "supra_note"),
        (SHORT_CASE, "case", "short_case"),
        (ID_FORM, "short_form", "id"),
        (SUPRA, "short_form", "supra"),
    ]
    occupied = [(item.start, item.end) for item in raw]
    for pattern, source_type, form in custom:
        for match in pattern.finditer(ir.text):
            if any(match.start() < end and start < match.end() for start, end in occupied):
                continue
            location = _location(ir, match.start(), match.end())
            components = {key: value for key, value in match.groupdict().items() if value}
            raw.append(
                _RawOccurrence(
                    match.group(0),
                    match.start(),
                    match.end(),
                    source_type,
                    form,
                    location,
                    components,
                    _logical_key(ir, location, match.start()),
                )
            )
            occupied.append(match.span())

    full_statute_sections = {
        _normalize(item.components.get("section"))
        for item in raw
        if item.source_type in {"statute", "regulation"} and item.form == "full"
    }
    for match in STATUTORY_SHORT.finditer(ir.text):
        if any(match.start() < end and start < match.end() for start, end in occupied):
            continue
        section = _normalize(match.group("section"))
        if section not in full_statute_sections:
            continue
        location = _location(ir, match.start(), match.end())
        components = {"section": match.group("section")}
        if match.group("code"):
            components["code"] = match.group("code")
        raw.append(
            _RawOccurrence(
                match.group(0),
                match.start(),
                match.end(),
                "statute",
                "statutory_short",
                location,
                components,
                _logical_key(ir, location, match.start()),
            )
        )
    for definition in HEREINAFTER_DEF.finditer(ir.text):
        alias = definition.group("alias")
        alias_pattern = re.compile(rf"\b{re.escape(alias)}\b")
        for match in alias_pattern.finditer(ir.text, definition.end()):
            if any(match.start() < end and start < match.end() for start, end in occupied):
                continue
            location = _location(ir, match.start(), match.end())
            raw.append(
                _RawOccurrence(
                    match.group(0),
                    match.start(),
                    match.end(),
                    "short_form",
                    "hereinafter",
                    location,
                    {"alias": alias},
                    _logical_key(ir, location, match.start()),
                )
            )
            occupied.append(match.span())
    return sorted(raw, key=lambda item: (item.logical_key, item.start, item.end))


def _article_components(ir: DocumentIR, item: _RawOccurrence) -> dict[str, str]:
    values = dict(item.components)
    block = ir.block_at(item.start)
    if not block:
        return values
    local = item.start - block.absolute_start
    prefix = block.text[max(0, local - 180) : local]
    match = ARTICLE_CONTEXT.search(prefix)
    if match:
        values["author"] = match.group("author").strip()
        values["title"] = match.group("title").strip()
    after = block.text[item.end - block.absolute_start : item.end - block.absolute_start + 30]
    year = re.search(r"\((\d{4})\)", after)
    if year:
        values["year"] = year.group(1)
    return values


def _identity(ir: DocumentIR, item: _RawOccurrence, unique: int) -> tuple[tuple[str, ...], dict[str, str], str, str]:
    components = dict(item.components)
    confidence = "high"
    display = item.text
    if item.source_type == "case":
        match = CASE_FULL.search(item.text)
        if match:
            components.update(match.groupdict())
        name = components.get("case_name") or components.get("name") or components.get("plaintiff")
        volume = components.get("volume", "")
        reporter = components.get("reporter", "")
        page = components.get("first_page") or components.get("page", "")
        key = (_normalize(name), _normalize(volume), _reporter(reporter), _normalize(page))
        display = str(name or item.text)
    elif item.source_type in {"statute", "regulation"}:
        key = (
            _normalize(components.get("jurisdiction", "us")),
            _normalize(components.get("code")),
            _normalize(components.get("title")),
            _normalize(components.get("section")),
            _normalize(components.get("edition")),
        )
    elif item.source_type == "journal_article":
        components = _article_components(ir, item)
        key = tuple(
            _normalize(components.get(name))
            for name in ("author", "title", "journal", "volume", "page", "year")
        )
        display = components.get("title") or components.get("author") or item.text
    elif item.source_type == "internet":
        key = (_normalize(components.get("url") or item.text), _normalize(components.get("title")), _normalize(components.get("author")))
    else:
        key = tuple(_normalize(components.get(name)) for name in sorted(components))
        if not any(key):
            key = (_normalize(item.text), str(unique))
            confidence = "low"
    if not any(key):
        key = (_normalize(item.text), str(unique))
        confidence = "low"
    return key, components, display, confidence


def _group_before(ir: DocumentIR, occurrences: Sequence[OccurrenceNode], index: int) -> list[OccurrenceNode]:
    previous = occurrences[index - 1]
    group = [previous]
    cursor = index - 1
    while cursor > 0:
        earlier = occurrences[cursor - 1]
        if earlier.form != "full" or earlier.location.note_id != previous.location.note_id:
            break
        gap = ir.text[earlier.end : group[0].start]
        if re.search(r"\.\s+[A-Z]", gap) or re.search(r"[A-Za-z]{3,}", gap):
            break
        group.insert(0, earlier)
        cursor -= 1
    return group


def _candidate(node: AuthorityNode, occurrence: OccurrenceNode, score: int, *facts: str) -> AntecedentCandidate:
    return AntecedentCandidate(node.authority_id, occurrence.occurrence_id, score, tuple(facts))


def build_citation_graph(ir: DocumentIR, *, mode: str = "bluepages") -> CitationGraph:
    if mode not in {"bluepages", "whitepages"}:
        raise ValueError("mode must be bluepages or whitepages")
    raw = _raw_occurrences(ir)
    authorities_by_key: dict[tuple[str, tuple[str, ...]], AuthorityNode] = {}
    occurrence_nodes: list[OccurrenceNode] = []
    authority_by_id: dict[str, AuthorityNode] = {}
    edges: list[CitationEdge] = []
    full_by_authority: dict[str, list[OccurrenceNode]] = {}
    for index, item in enumerate(raw):
        authority_id: str | None = None
        components = dict(item.components)
        if item.form == "full":
            key, components, display, identity_confidence = _identity(ir, item, index)
            lookup = (item.source_type, key)
            authority = authorities_by_key.get(lookup)
            if authority is None:
                authority = AuthorityNode(
                    _authority_id(item.source_type, key),
                    item.source_type,
                    key,
                    display,
                    components,
                    identity_confidence,
                )
                authorities_by_key[lookup] = authority
                authority_by_id[authority.authority_id] = authority
            authority_id = authority.authority_id
        occurrence = OccurrenceNode(
            f"occurrence:{index:04d}",
            item.text,
            item.start,
            item.end,
            item.source_type,
            item.form,
            index,
            item.location,
            components,
            authority_id,
        )
        occurrence_nodes.append(occurrence)
        if authority_id:
            edges.append(CitationEdge("full_citation_to_authority", occurrence.occurrence_id, authority_id))
            previous = full_by_authority.setdefault(authority_id, [])
            if previous:
                edges.append(CitationEdge("prior_occurrence", occurrence.occurrence_id, previous[-1].occurrence_id))
                edges.append(CitationEdge("later_occurrence", previous[-1].occurrence_id, occurrence.occurrence_id))
            previous.append(occurrence)
        if index:
            edges.append(CitationEdge("immediately_preceding_occurrence", occurrence.occurrence_id, occurrence_nodes[index - 1].occurrence_id))

    for left_index, left in enumerate(occurrence_nodes):
        for right in occurrence_nodes[left_index + 1 :]:
            if left.location.note_id and left.location.note_id == right.location.note_id:
                edges.append(CitationEdge("same_footnote", left.occurrence_id, right.occurrence_id, {"note_id": left.location.note_id}))
            gap = ir.text[left.end : right.start]
            if ";" in gap and not re.search(r"\.\s+[A-Z]", gap):
                edges.append(CitationEdge("same_citation_sentence", left.occurrence_id, right.occurrence_id))
                edges.append(CitationEdge("same_citation_clause", left.occurrence_id, right.occurrence_id))
        prefix = ir.text[max(0, left.start - 24) : left.start]
        signal = re.search(r"\b(see also|see|cf\.|accord|but see|contra)\s*$", prefix, re.I)
        if signal:
            edges.append(CitationEdge("signal_linked_to_citation_group", left.occurrence_id, left.occurrence_id, {"signal": signal.group(1)}))
        if re.search(r"[“\"][^”\"]+[”\"]\s*$", ir.text[max(0, left.start - 180) : left.start]):
            edges.append(CitationEdge("quotation_linked_to_authority", left.occurrence_id, left.authority_id or left.occurrence_id))
        suffix = ir.text[left.end : left.end + 180]
        if re.match(r"\s*\([^)]{2,160}\)", suffix):
            edges.append(CitationEdge("parenthetical_linked_to_authority", left.occurrence_id, left.authority_id or left.occurrence_id))

    resolutions: list[ResolutionResult] = []
    aliases: dict[str, str] = {}
    for match in HEREINAFTER_DEF.finditer(ir.text):
        prior = [item for item in occurrence_nodes if item.form == "full" and item.end <= match.start()]
        if prior and prior[-1].authority_id:
            aliases[_normalize(match.group("alias"))] = prior[-1].authority_id
            edges.append(CitationEdge("hereinafter_definition", prior[-1].occurrence_id, prior[-1].authority_id, {"alias": match.group("alias")}))

    # Running map of each occurrence's *effective* authority, kept up to date
    # in document order. Full citations start pre-populated; short forms are
    # added as they resolve, so a later "Id." can chain through a prior
    # "Id." (or other short form) rather than only ever looking at full
    # citations.
    resolved_authority_by_occurrence: dict[str, str] = {
        occurrence.occurrence_id: occurrence.authority_id
        for occurrence in occurrence_nodes
        if occurrence.authority_id
    }

    for index, occurrence in enumerate(occurrence_nodes):
        if occurrence.form == "full":
            continue
        candidates: list[AntecedentCandidate] = []
        disqualifying: list[str] = []
        resolved: str | None = None
        method = "unresolved"
        confidence = "low"
        if occurrence.form == "id":
            if index == 0:
                disqualifying.append("no_immediately_preceding_authority")
            else:
                group = _group_before(ir, occurrence_nodes, index)
                prior = occurrence_nodes[index - 1]
                prior_authority_id = prior.authority_id or resolved_authority_by_occurrence.get(
                    prior.occurrence_id
                )
                if prior_authority_id:
                    candidates.append(_candidate(authority_by_id[prior_authority_id], prior, 100, "immediately_preceding_authority"))
                gap = ir.text[prior.end : occurrence.start]
                if ";" in gap:
                    disqualifying.append("intervening_citation_clause")
                if len([item for item in group if item.authority_id]) > 1:
                    disqualifying.append("preceding_citation_group_has_multiple_authorities")
                if re.search(r"[A-Za-z]{3,}", gap):
                    disqualifying.append("intervening_non_citation_material")
                if prior_authority_id is None:
                    disqualifying.append("no_immediately_preceding_authority")
                if not disqualifying and prior_authority_id:
                    resolved = prior_authority_id
                    method = "immediately_preceding_single_authority"
                    confidence = "high"
        elif occurrence.form == "short_case":
            label = _normalize(occurrence.components.get("name")).split()[0]
            volume = _normalize(occurrence.components.get("volume"))
            reporter = _reporter(occurrence.components.get("reporter"))
            prior_cases = [item for item in occurrence_nodes[:index] if item.form == "full" and item.source_type == "case" and item.authority_id]
            for prior in reversed(prior_cases):
                node = authority_by_id[prior.authority_id]
                node_name = _normalize(node.components.get("case_name") or node.components.get("name") or node.display_name)
                node_volume = _normalize(node.components.get("volume"))
                node_reporter = _reporter(node.components.get("reporter"))
                if label and node_name.startswith(label) and volume == node_volume and reporter == node_reporter:
                    candidates.append(_candidate(node, prior, 100, "shortened_name_match", "volume_match", "reporter_match"))
            unique = {item.authority_id for item in candidates}
            if len(unique) == 1:
                resolved = next(iter(unique))
                method = "prior_full_case_exact_components"
                confidence = "high"
            elif not candidates:
                disqualifying.append("no_legally_possible_prior_antecedent")
                later_cases = [item for item in occurrence_nodes[index + 1 :] if item.form == "full" and item.source_type == "case" and item.authority_id]
                for later in later_cases:
                    node = authority_by_id[later.authority_id]
                    node_name = _normalize(node.components.get("case_name") or node.components.get("name") or node.display_name)
                    if label and node_name.startswith(label) and volume == _normalize(node.components.get("volume")) and reporter == _reporter(node.components.get("reporter")):
                        edges.append(CitationEdge("later_consistency_match", occurrence.occurrence_id, later.occurrence_id, {"not_validating": True}))
            else:
                disqualifying.append("multiple_plausible_prior_cases")
        elif occurrence.form == "statutory_short":
            section = _normalize(occurrence.components.get("section"))
            code_hint = _reporter(occurrence.components.get("code")) if occurrence.components.get("code") else ""
            prior_sources = [item for item in occurrence_nodes[:index] if item.form == "full" and item.source_type in {"statute", "regulation"} and item.authority_id]
            for prior in reversed(prior_sources):
                node = authority_by_id[prior.authority_id]
                if _normalize(node.components.get("section")) != section:
                    continue
                if code_hint and _reporter(node.components.get("code")) != code_hint:
                    continue
                facts = ("section_match", "code_match") if code_hint else ("section_match",)
                candidates.append(_candidate(node, prior, 90, *facts))
            unique = {item.authority_id for item in candidates}
            if len(unique) == 1:
                resolved = next(iter(unique))
                method = "prior_full_statutory_authority"
                confidence = "high"
            elif not candidates:
                disqualifying.append("no_legally_possible_prior_antecedent")
            else:
                disqualifying.append("multiple_plausible_statutory_antecedents")
        elif occurrence.form == "supra_note":
            note = occurrence.components.get("note", "")
            referenced = [
                item
                for item in occurrence_nodes[:index]
                if item.form == "full"
                and item.location.note_number == note
                and item.authority_id
            ]
            for prior in referenced:
                node = authority_by_id[prior.authority_id]
                if node.source_type in PERMITTED_SUPRA_TYPES:
                    candidates.append(_candidate(node, prior, 100, "referenced_note", "source_type_permits_supra"))
                else:
                    disqualifying.append("source_type_does_not_permit_supra")
            unique = {item.authority_id for item in candidates}
            if len(unique) == 1:
                resolved = next(iter(unique))
                method = "single_permitted_authority_in_referenced_note"
                confidence = "high"
            elif not candidates:
                disqualifying.append("referenced_note_has_no_permitted_authority")
            else:
                disqualifying.append("referenced_note_has_multiple_authorities")
        elif occurrence.form == "supra":
            label = _normalize(occurrence.components.get("label"))
            prohibited_match = False
            for prior in reversed(occurrence_nodes[:index]):
                if prior.form != "full" or not prior.authority_id:
                    continue
                node = authority_by_id[prior.authority_id]
                searchable = _normalize(" ".join([node.display_name, node.components.get("author", ""), node.components.get("title", "")]))
                if label and label.split()[-1] not in searchable:
                    continue
                if node.source_type not in PERMITTED_SUPRA_TYPES:
                    prohibited_match = True
                    continue
                candidates.append(_candidate(node, prior, 80, "label_match", "prior_full_citation"))
            unique = {item.authority_id for item in candidates}
            if len(unique) == 1:
                resolved = next(iter(unique))
                method = "prior_full_supra_permitted_authority"
                confidence = "medium"
            elif prohibited_match and not candidates:
                disqualifying.append("source_type_does_not_permit_supra")
            elif not candidates:
                disqualifying.append("no_legally_possible_prior_antecedent")
            else:
                disqualifying.append("multiple_plausible_supra_antecedents")
        elif occurrence.form == "hereinafter":
            alias = _normalize(occurrence.components.get("alias"))
            target = aliases.get(alias)
            if target:
                resolved = target
                method = "prior_hereinafter_definition"
                confidence = "high"
                prior = next(
                    item
                    for item in reversed(occurrence_nodes[:index])
                    if item.authority_id == target
                )
                candidates.append(
                    _candidate(
                        authority_by_id[target],
                        prior,
                        100,
                        "exact_defined_alias",
                    )
                )
            else:
                disqualifying.append("no_prior_hereinafter_definition")
        if resolved:
            edges.append(CitationEdge(f"{occurrence.form}_to_antecedent", occurrence.occurrence_id, resolved, {"method": method}, "deterministic_logic"))
            resolved_authority_by_occurrence[occurrence.occurrence_id] = resolved
        resolutions.append(
            ResolutionResult(
                occurrence.occurrence_id,
                occurrence.form,
                resolved,
                method,
                tuple(candidates),
                confidence,
                tuple(dict.fromkeys(disqualifying)),
                mode,
                resolved is None,
                "deterministic_logic" if resolved else "unresolved_ambiguity",
            )
        )
    return CitationGraph(
        tuple(authorities_by_key.values()),
        tuple(occurrence_nodes),
        tuple(edges),
        tuple(resolutions),
        mode,
    )
