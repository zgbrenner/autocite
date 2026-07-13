from __future__ import annotations

import re
from typing import Any

from .engine import CitationEngine
from .formatters import generate_citation, supported_source_types
from .rules import RULE_CATALOG, rule_reference, validate_mode
from .verifiers import CourtListenerVerifier

_ENGINE = CitationEngine()


def check_citations(
    text: str,
    *,
    mode: str = "bluepages",
    apply_safe_fixes: bool = False,
) -> dict[str, Any]:
    """Analyze a block of legal writing and optionally apply only high-confidence fixes."""
    if not text.strip():
        raise ValueError("text must not be empty")
    return (
        _ENGINE.fix(text, mode=mode)
        if apply_safe_fixes
        else _ENGINE.analyze(text, mode=mode)
    )


def check_single_citation(
    citation: str,
    *,
    mode: str = "bluepages",
) -> dict[str, Any]:
    """Analyze exactly one citation and return a focused result."""
    report = _ENGINE.analyze(citation, mode=mode)
    substantive = [
        item
        for item in report["citations"]
        if item["source_type"] not in {"short_form", "internet"}
    ]
    if len(substantive) != 1:
        raise ValueError("Input must contain exactly one recognized citation")
    fixed = _ENGINE.fix(citation, mode=mode)
    return {
        "mode": report["mode"],
        "citation": substantive[0],
        "issues": report["issues"],
        "suggested_citation": fixed["fixed_text"],
        "remaining_issues": fixed["remaining_issues"],
    }


def convert_citation(
    citation: str,
    *,
    target_mode: str,
    output_style: str = "plain",
) -> dict[str, Any]:
    """Convert a recognized citation using only facts present in the input."""
    mode = validate_mode(target_mode)
    report = _ENGINE.analyze(citation, mode=mode)
    substantive = [
        item
        for item in report["citations"]
        if item["source_type"] not in {"short_form", "internet"}
    ]
    if len(substantive) != 1:
        raise ValueError("Input must contain exactly one recognized citation")
    item = substantive[0]
    components = dict(item["components"])
    source_type = item["source_type"]

    if source_type == "case":
        if "year" not in components:
            court_year = components.pop("court_year", "")
            year_match = re.search(r"(?P<year>\d{4})\s*$", court_year)
            if year_match is None:
                raise ValueError("Could not identify the decision year")
            components["year"] = year_match.group("year")
            court = court_year[: year_match.start()].strip()
            if court:
                components["court"] = court
        components.pop("resolved_to", None)
        converted = generate_citation(
            "case", components, mode=mode, output_style=output_style
        )
    elif source_type in {"statute", "regulation"}:
        if components.get("title"):
            converted = generate_citation(
                source_type,
                {
                    "title": components["title"],
                    "code": components["code"],
                    "section": components["section"],
                },
                mode=mode,
                output_style=output_style,
            )
        elif source_type == "statute" and components.get("chapter"):
            converted = (
                f"{components['code']} ch. {components['chapter']}, "
                f"§ {components['section']}"
            )
            parenthetical = " ".join(
                value
                for key in ("publisher", "year")
                if (value := components.get(key))
            )
            if parenthetical:
                converted += f" ({parenthetical})"
        else:
            raise ValueError(
                "Citation lacks the title or chapter metadata required for safe conversion"
            )
    elif source_type == "constitution":
        converted = generate_citation(
            "constitution",
            {
                "constitution": "U.S. Const.",
                "subdivision": components["subdivision"],
            },
            mode=mode,
            output_style=output_style,
        )
    else:
        raise ValueError(f"Conversion is not yet supported for {source_type}")

    return {
        "source_type": source_type,
        "target_mode": mode,
        "output_style": output_style,
        "original": citation,
        "converted": converted,
        "facts_used": components,
    }


async def verify_case_citations(text: str) -> dict[str, Any]:
    """Verify U.S. case citations with CourtListener when configured."""
    return await CourtListenerVerifier().verify_text(text)


def explain_issue(code: str, *, mode: str = "bluepages") -> dict[str, Any]:
    """Explain an AutoCite issue code and its corresponding rule family."""
    normalized_mode = validate_mode(mode)
    normalized_code = code.strip().upper()
    metadata = RULE_CATALOG.get(normalized_code)
    if metadata is None:
        raise ValueError(f"Unknown issue code: {code}")
    return {
        "code": normalized_code,
        "title": metadata["title"],
        "description": metadata["description"],
        "severity": metadata["severity"],
        "autofix": metadata["autofix"],
        "mode": normalized_mode,
        "rule": rule_reference(normalized_code, normalized_mode),
    }


def list_capabilities() -> dict[str, Any]:
    """Describe supported citation workflows and explicit limitations."""
    return {
        "modes": ["bluepages", "whitepages"],
        "source_types": supported_source_types(),
        "document_analysis": {
            "extracts": [
                "federal and state cases",
                "federal and state statutes",
                "federal regulations",
                "U.S. Constitution provisions",
                "journal citations",
                "Id., supra, short-case, and reference citations",
                "internet URLs",
            ],
            "parser": "eyecite with AutoCite malformed-citation fallbacks",
            "short_form_resolution": "Groups resolvable full and short citations by antecedent",
            "safe_autofixes": [
                "reporter abbreviations",
                "U.S.C. and C.F.R. abbreviations",
                "section-symbol spacing",
                "Id. capitalization and punctuation",
            ],
        },
        "verification": {
            "provider": "CourtListener",
            "courtlistener_supports": ["case"],
            "courtlistener_does_not_support": [
                "statutes",
                "law journals",
                "Id. short forms",
                "supra short forms",
            ],
            "requires_environment_variable": "COURTLISTENER_TOKEN",
        },
        "guardrails": [
            "AutoCite never invents missing bibliographic facts.",
            "Only high-confidence mechanical edits are applied automatically.",
            "Context-dependent questions remain review items.",
            "Citation correctness does not establish substantive support for a proposition.",
        ],
    }
