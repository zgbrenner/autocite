from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Callable, Sequence

from .citation_graph import CitationGraph
from .document_ir import DocumentIR
from .rule_families import SOURCE_FAMILY_COVERAGE


CORRECTION_LEVELS = {
    "safe_auto_fix",
    "suggested_fix",
    "review_required",
    "unsupported",
}


@dataclass(frozen=True)
class RuleSpec:
    issue_code: str
    bluepages_applicable: bool
    whitepages_applicable: bool
    source_types: tuple[str, ...]
    required_context: tuple[str, ...]
    required_facts: tuple[str, ...]
    deterministic_conditions: tuple[str, ...]
    severity: str
    automatic_correction_permitted: bool
    correction_level: str
    confidence: str
    original_rule_summary: str
    rule_family_reference: str
    explanation_template: str
    test_cases: tuple[str, ...]


@dataclass(frozen=True)
class RuleFinding:
    issue_code: str
    family: str
    severity: str
    correction_level: str
    confidence: str
    start: int
    end: int
    original: str
    suggestion: str | None
    explanation: str
    rule_profile: str
    rule_family_reference: str
    required_facts: tuple[str, ...]
    missing_facts: tuple[str, ...]
    provenance: str = "deterministic_logic"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedSignal:
    text: str
    normalized: str
    start: int
    end: int
    group: str
    provenance: str = "parsed_document_structure"


@dataclass(frozen=True)
class ParsedParenthetical:
    text: str
    start: int
    end: int
    parenthetical_type: str
    depth: int
    balanced: bool
    provenance: str = "parsed_document_structure"


def _spec(
    code: str,
    family: str,
    summary: str,
    *,
    source_types: tuple[str, ...] = ("all",),
    bluepages: bool = True,
    whitepages: bool = True,
    context: tuple[str, ...] = ("DocumentIR", "CitationGraph"),
    facts: tuple[str, ...] = (),
    conditions: tuple[str, ...] = ("exact structural or textual condition",),
    severity: str = "error",
    correction_level: str = "review_required",
    confidence: str = "high",
    tests: tuple[str, ...] = ("positive", "negative", "ambiguous"),
) -> RuleSpec:
    return RuleSpec(
        code,
        bluepages,
        whitepages,
        source_types,
        context,
        facts,
        conditions,
        severity,
        correction_level == "safe_auto_fix",
        correction_level,
        confidence,
        summary,
        family,
        "{explanation}",
        tests,
    )


RULE_SPECS: dict[str, RuleSpec] = {
    "ID_AMBIGUOUS_ANTECEDENT": _spec(
        "ID_AMBIGUOUS_ANTECEDENT",
        "short forms: Id.",
        "Id. must refer unambiguously to the immediately preceding authority.",
        source_types=("short_form",),
        facts=("immediately preceding authority", "citation group membership"),
        conditions=("citation graph leaves Id. unresolved",),
    ),
    "SHORT_CASE_UNRESOLVED": _spec(
        "SHORT_CASE_UNRESOLVED",
        "short forms: cases",
        "A shortened case citation needs a prior unambiguous full case citation.",
        source_types=("case",),
        facts=("case name", "volume", "reporter", "prior full citation"),
        conditions=("no unique exact prior case identity",),
    ),
    "STATUTORY_SHORT_UNRESOLVED": _spec(
        "STATUTORY_SHORT_UNRESOLVED",
        "short forms: statutes and regulations",
        "A statutory or regulatory short form needs a compatible prior authority.",
        source_types=("statute", "regulation"),
        facts=("code", "section", "jurisdiction", "prior full citation"),
        conditions=("no unique compatible prior statutory authority",),
    ),
    "SUPRA_SOURCE_TYPE_PROHIBITED": _spec(
        "SUPRA_SOURCE_TYPE_PROHIBITED",
        "supra and hereinafter",
        "Cases and statutes do not use supra as a short form.",
        source_types=("case", "statute", "regulation", "short_form"),
        facts=("source type", "prior full citation"),
        conditions=("matching prior authority has a prohibited source type",),
    ),
    "SUPRA_AMBIGUOUS_ANTECEDENT": _spec(
        "SUPRA_AMBIGUOUS_ANTECEDENT",
        "supra and hereinafter",
        "Supra and supra note must identify one permissible prior authority.",
        source_types=("short_form",),
        facts=("label", "note number", "prior full citations"),
        conditions=("zero or multiple permissible prior authorities",),
    ),
    "HEREINAFTER_UNRESOLVED": _spec(
        "HEREINAFTER_UNRESOLVED",
        "supra and hereinafter",
        "A hereinafter short form must follow an exact prior definition.",
        source_types=("short_form",),
        facts=("defined alias", "prior definition"),
        conditions=("no exact prior hereinafter definition",),
    ),
    "SIGNAL_PUNCTUATION": _spec(
        "SIGNAL_PUNCTUATION",
        "signals",
        "Citation signals use conventional spelling and punctuation.",
        source_types=("all",),
        context=("citation-adjacent text",),
        facts=("signal text",),
        conditions=("recognized signal has mechanically incorrect punctuation",),
        correction_level="safe_auto_fix",
    ),
    "SIGNAL_PARENTHETICAL_REVIEW": _spec(
        "SIGNAL_PARENTHETICAL_REVIEW",
        "signals",
        "Some signals ordinarily call for an explanatory parenthetical review.",
        source_types=("all",),
        facts=("signal", "citation group", "parenthetical presence"),
        conditions=("cf. or but cf. group lacks an explanatory parenthetical",),
        severity="warning",
        confidence="medium",
    ),
    "PARENTHETICAL_SYNTAX": _spec(
        "PARENTHETICAL_SYNTAX",
        "parentheticals",
        "Citation parentheticals must be balanced and positioned after the authority.",
        source_types=("all",),
        facts=("citation span", "adjacent parentheses"),
        conditions=("unbalanced citation-adjacent parentheses",),
        correction_level="suggested_fix",
    ),
    "CITATION_GROUP_SEPARATOR": _spec(
        "CITATION_GROUP_SEPARATOR",
        "citation groups and ordering",
        "Separate authorities in a citation group with mechanically valid punctuation.",
        source_types=("all",),
        facts=("adjacent citation spans", "separator text"),
        conditions=("multiple authorities are joined only by a comma",),
        correction_level="suggested_fix",
    ),
    "QUOTATION_PINCITE_REQUIRED": _spec(
        "QUOTATION_PINCITE_REQUIRED",
        "pincites and quotations",
        "A direct quotation should identify the exact cited page or location.",
        source_types=("case", "journal_article", "book"),
        facts=("quotation", "citation", "pincite"),
        conditions=("direct quotation precedes an authority lacking a pincite",),
    ),
    "PROPOSITION_PINCITE_REVIEW": _spec(
        "PROPOSITION_PINCITE_REVIEW",
        "pincites and quotations",
        "A source-specific proposition may require a pinpoint citation.",
        source_types=("case", "journal_article", "book"),
        facts=("citation", "pincite"),
        conditions=("full authority lacks a parsed pincite",),
        severity="info",
        confidence="low",
    ),
    "WHITEPAGES_ARCHIVE_REVIEW": _spec(
        "WHITEPAGES_ARCHIVE_REVIEW",
        "internet sources",
        "Academic internet citations should be reviewed for durable location information.",
        source_types=("internet",),
        bluepages=False,
        facts=("URL", "nearby archive marker"),
        conditions=("Whitepages URL lacks nearby archive or on-file statement",),
        severity="warning",
        confidence="medium",
    ),
}


def _finding(
    code: str,
    mode: str,
    start: int,
    end: int,
    original: str,
    explanation: str,
    *,
    suggestion: str | None = None,
    missing_facts: Sequence[str] = (),
) -> RuleFinding:
    spec = RULE_SPECS[code]
    return RuleFinding(
        code,
        spec.rule_family_reference,
        spec.severity,
        spec.correction_level,
        spec.confidence,
        start,
        end,
        original,
        suggestion,
        explanation,
        mode,
        spec.rule_family_reference,
        spec.required_facts,
        tuple(missing_facts),
    )


def _short_form_findings(
    ir: DocumentIR, graph: CitationGraph, mode: str
) -> list[RuleFinding]:
    occurrences = {item.occurrence_id: item for item in graph.occurrences}
    findings: list[RuleFinding] = []
    code_by_form = {
        "id": "ID_AMBIGUOUS_ANTECEDENT",
        "short_case": "SHORT_CASE_UNRESOLVED",
        "statutory_short": "STATUTORY_SHORT_UNRESOLVED",
        "supra": "SUPRA_AMBIGUOUS_ANTECEDENT",
        "supra_note": "SUPRA_AMBIGUOUS_ANTECEDENT",
        "hereinafter": "HEREINAFTER_UNRESOLVED",
    }
    for result in graph.resolutions:
        if result.resolved_authority_id is not None:
            continue
        occurrence = occurrences[result.occurrence_id]
        code = code_by_form[result.form]
        if "source_type_does_not_permit_supra" in result.disqualifying_facts:
            code = "SUPRA_SOURCE_TYPE_PROHIBITED"
        findings.append(
            _finding(
                code,
                mode,
                occurrence.start,
                occurrence.end,
                occurrence.citation_text,
                "; ".join(result.disqualifying_facts)
                or "The antecedent is unresolved.",
                missing_facts=result.disqualifying_facts,
            )
        )
    return findings


SIGNAL_PATTERN = re.compile(
    r"(?<!\w)(?P<signal>compare|with|see also|see generally|see|cf\.?|accord|but see|but cf\.?|contra)\s+",
    re.I,
)

# A bare court/year (or year-only) parenthetical is ordinary citation metadata,
# e.g. "(9th Cir. 2000)" or "(2000)" -- not the explanatory parenthetical that
# Bluebook practice expects after cf./but cf. It is short and ends in a year
# with no substantive explanatory prose before it.
_COURT_YEAR_PARENTHETICAL = re.compile(
    r"^[A-Za-z.\d'&,\- ]{0,40}\b(?:1[6-9]|20)\d{2}[a-z]?$"
)


def _is_court_or_year_metadata(content: str) -> bool:
    """True when a parenthetical is just court/year citation metadata.

    It ends in a year and carries only court/reporter/ordinal tokens. A real
    explanatory parenthetical that merely happens to end in a year (e.g.
    "discussing the statute as amended in 2000") contains an ordinary lowercase
    word and is therefore not treated as metadata.
    """
    if not _COURT_YEAR_PARENTHETICAL.match(content):
        return False
    return not re.search(r"[a-z]{4,}", content)


def _has_explanatory_parenthetical(window: str) -> bool:
    """Return True when ``window`` contains a genuine explanatory parenthetical.

    A citation's own court/year parenthetical does not satisfy the
    explanatory-parenthetical expectation for a cf./but cf. signal, so those are
    skipped; any other parenthetical that carries alphabetic content counts.
    """
    for match in re.finditer(r"\(([^)]*)\)", window):
        content = match.group(1).strip()
        if not re.search(r"[A-Za-z]", content):
            continue
        if _is_court_or_year_metadata(content):
            continue
        return True
    return False


def parse_signals(text: str) -> tuple[ParsedSignal, ...]:
    parsed: list[ParsedSignal] = []
    for match in SIGNAL_PATTERN.finditer(text):
        raw = match.group("signal")
        normalized = raw.casefold().rstrip(".")
        group = (
            "comparative"
            if normalized in {"compare", "with"}
            else "contrary"
            if normalized in {"but see", "but cf", "contra"}
            else "supportive"
        )
        parsed.append(
            ParsedSignal(raw, normalized, match.start("signal"), match.end("signal"), group)
        )
    return tuple(parsed)


def parse_parentheticals(text: str) -> tuple[ParsedParenthetical, ...]:
    stack: list[tuple[int, int]] = []
    parsed: list[ParsedParenthetical] = []
    for index, character in enumerate(text):
        if character == "(":
            stack.append((index, len(stack)))
        elif character == ")" and stack:
            start, depth = stack.pop()
            value = text[start : index + 1]
            body = value[1:-1].strip().casefold()
            kind = "explanatory"
            if any(term in body for term in ("quoting", "alteration", "omission")):
                kind = "quotation_or_alteration"
            elif any(term in body for term in ("aff'd", "rev'd", "appeal", "history")):
                kind = "procedural_or_subsequent_history"
            elif any(term in body for term in ("en banc", "plurality", "per curiam")):
                kind = "weight_of_authority"
            parsed.append(ParsedParenthetical(value, start, index + 1, kind, depth, True))
    parsed.extend(
        ParsedParenthetical(text[start:], start, len(text), "unknown", depth, False)
        for start, depth in stack
    )
    return tuple(sorted(parsed, key=lambda item: (item.start, item.end)))


def _signal_findings(ir: DocumentIR, graph: CitationGraph, mode: str) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    for parsed in parse_signals(ir.text):
        signal = parsed.text
        lowered = parsed.normalized
        if lowered in {"cf", "but cf"} and not signal.endswith("."):
            corrected = "Cf." if lowered == "cf" else "But cf."
            findings.append(
                _finding(
                    "SIGNAL_PUNCTUATION",
                    mode,
                    parsed.start,
                    parsed.end,
                    signal,
                    "The recognized signal is missing its terminal period.",
                    suggestion=corrected,
                )
            )
        if lowered.rstrip(".") in {"cf", "but cf"}:
            following = ir.text[parsed.end : parsed.end + 240]
            if not _has_explanatory_parenthetical(following):
                findings.append(
                    _finding(
                        "SIGNAL_PARENTHETICAL_REVIEW",
                        mode,
                        parsed.start,
                        parsed.end,
                        signal,
                        "Review whether this signal group needs an explanatory parenthetical; AutoCite does not decide substantive signal fit.",
                    )
                )
    return findings


def _citation_context_findings(
    ir: DocumentIR, graph: CitationGraph, mode: str
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    full = [item for item in graph.occurrences if item.form == "full"]
    for occurrence in full:
        components = occurrence.components
        if occurrence.source_type in {"case", "journal_article", "book"} and not components.get("pincite"):
            prefix = ir.text[max(0, occurrence.start - 260) : occurrence.start]
            quote_match = re.search(
                r"[“\"](?P<quoted>[^”\"]{2,220})[”\"](?:\s+[^.;]{0,30})?\s*$", prefix
            )
            # A single scare-quoted word (a defined term such as "employer") is
            # not a direct quotation of the cited authority. Only multi-word
            # quoted language is treated as a quotation that demands a pincite;
            # otherwise fall back to the softer proposition-pincite review rather
            # than asserting a quotation that may not exist.
            is_direct_quotation = bool(
                quote_match and " " in quote_match.group("quoted").strip()
            )
            code = (
                "QUOTATION_PINCITE_REQUIRED"
                if is_direct_quotation
                else "PROPOSITION_PINCITE_REVIEW"
            )
            explanation = (
                "A direct quotation precedes this authority, but no pinpoint location was parsed."
                if is_direct_quotation
                else "Review whether this proposition requires a pinpoint citation."
            )
            findings.append(
                _finding(
                    code,
                    mode,
                    occurrence.start,
                    occurrence.end,
                    occurrence.citation_text,
                    explanation,
                    missing_facts=("pincite",),
                )
            )
    for left, right in zip(full, full[1:]):
        gap = ir.text[left.end : right.start]
        if re.fullmatch(r"\s*,\s*", gap):
            findings.append(
                _finding(
                    "CITATION_GROUP_SEPARATOR",
                    mode,
                    left.end,
                    right.start,
                    gap,
                    "Two recognized authorities are separated only by a comma.",
                    suggestion="; ",
                )
            )
    parentheticals = parse_parentheticals(ir.text)
    for occurrence in graph.occurrences:
        suffix = ir.text[occurrence.end : occurrence.end + 180]
        stripped = suffix.lstrip()
        if not stripped.startswith("("):
            continue
        paren_start = occurrence.end + (len(suffix) - len(stripped))
        # Use the real stack-based parenthetical parse (which is not bounded
        # to a fixed window) to decide whether the parenthetical is actually
        # balanced, rather than counting "(" / ")" within a truncated slice
        # (which false-positives on long-but-balanced parentheticals).
        parenthetical = next(
            (item for item in parentheticals if item.start == paren_start), None
        )
        if parenthetical is not None and not parenthetical.balanced:
            findings.append(
                _finding(
                    "PARENTHETICAL_SYNTAX",
                    mode,
                    occurrence.end,
                    parenthetical.end,
                    ir.text[occurrence.end : parenthetical.end],
                    "The citation-adjacent parenthetical appears unbalanced.",
                )
            )
    return findings


def _internet_findings(ir: DocumentIR, graph: CitationGraph, mode: str) -> list[RuleFinding]:
    if mode != "whitepages":
        return []
    findings: list[RuleFinding] = []
    for occurrence in graph.occurrences:
        if occurrence.source_type != "internet":
            continue
        nearby = ir.text[max(0, occurrence.start - 120) : occurrence.end + 180].casefold()
        if "perma.cc" not in nearby and "on file with author" not in nearby:
            findings.append(
                _finding(
                    "WHITEPAGES_ARCHIVE_REVIEW",
                    mode,
                    occurrence.start,
                    occurrence.end,
                    occurrence.citation_text,
                    "No nearby durable archive marker or on-file statement was found.",
                )
            )
    return findings


FAMILY_EVALUATORS: tuple[
    Callable[[DocumentIR, CitationGraph, str], list[RuleFinding]], ...
] = (
    _short_form_findings,
    _signal_findings,
    _citation_context_findings,
    _internet_findings,
)


def evaluate_document_rules(
    ir: DocumentIR, graph: CitationGraph, *, mode: str
) -> list[RuleFinding]:
    if mode not in {"bluepages", "whitepages"}:
        raise ValueError("mode must be bluepages or whitepages")
    findings: list[RuleFinding] = []
    for evaluator in FAMILY_EVALUATORS:
        findings.extend(evaluator(ir, graph, mode))
    applicable = {
        code
        for code, spec in RULE_SPECS.items()
        if (
            spec.bluepages_applicable
            if mode == "bluepages"
            else spec.whitepages_applicable
        )
    }
    unique: dict[tuple[str, int, int], RuleFinding] = {}
    for finding in findings:
        if finding.issue_code in applicable:
            unique[(finding.issue_code, finding.start, finding.end)] = finding
    return sorted(unique.values(), key=lambda item: (item.start, item.end, item.issue_code))


def rule_coverage_matrix() -> dict[str, dict[str, Any]]:
    return {
        family: {
            "status": status,
            "implemented_rules": list(rules),
            "claim": "tested subset only; not complete Bluebook compliance",
        }
        for family, (status, rules) in SOURCE_FAMILY_COVERAGE.items()
    }
