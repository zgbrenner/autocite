from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .formatters import generate_citation as _generate_citation
from .rules import RULE_CATALOG, validate_mode
from .tools import (
    check_citations as _check_citations,
    check_single_citation as _check_single_citation,
    convert_citation as _convert_citation,
    explain_issue as _explain_issue,
    list_capabilities as _list_capabilities,
    verify_case_citations as _verify_case_citations,
)

mcp = FastMCP(
    "AutoCite",
    instructions=(
        "Use AutoCite to inspect, repair, generate, and verify U.S. legal citations. "
        "Choose bluepages for practitioner and court documents; choose whitepages "
        "for law reviews and academic legal research. Never treat a formatting result "
        "as proof that an authority supports a proposition."
    ),
    json_response=True,
)


@mcp.tool()
def check_citations(
    text: str,
    mode: str = "bluepages",
    apply_safe_fixes: bool = False,
) -> dict[str, Any]:
    """Audit legal writing for citation-format problems.

    Args:
        text: Plain text or Markdown containing legal citations.
        mode: "bluepages" for court/practitioner documents or "whitepages" for
            academic legal research and law-review writing.
        apply_safe_fixes: When true, apply only high-confidence mechanical edits.

    Returns citation spans, issue codes, rule-family references, suggested edits,
    unresolved review items, and explicit limitations. Missing facts are never invented.
    """
    return _check_citations(text, mode=mode, apply_safe_fixes=apply_safe_fixes)


@mcp.tool()
def fix_citations(text: str, mode: str = "bluepages") -> dict[str, Any]:
    """Apply conservative citation fixes to a legal document.

    Only reporter/code abbreviation, section-symbol spacing, and Id. punctuation or
    capitalization fixes are automatic. Context-sensitive issues remain unresolved.
    """
    return _check_citations(text, mode=mode, apply_safe_fixes=True)


@mcp.tool()
def check_single_citation(
    citation: str,
    mode: str = "bluepages",
) -> dict[str, Any]:
    """Check exactly one citation and return a focused correction report."""
    return _check_single_citation(citation, mode=mode)


@mcp.tool()
def convert_citation(
    citation: str,
    target_mode: str,
    output_style: str = "plain",
) -> dict[str, Any]:
    """Convert a recognized case, statute, regulation, or constitutional citation.

    The conversion uses only facts already present in the citation. Output style may
    be plain, markdown, or html.
    """
    return _convert_citation(
        citation,
        target_mode=target_mode,
        output_style=output_style,
    )


@mcp.tool()
def generate_citation(
    source_type: str,
    fields: dict[str, Any],
    mode: str = "bluepages",
    output_style: str = "plain",
) -> dict[str, Any]:
    """Generate a citation from structured source facts without guessing.

    Supported source types: case, statute, regulation, constitution, journal_article,
    book, website, court_document, ai_content, and archival. The tool returns an error
    when a required fact is missing rather than fabricating it.
    """
    citation = _generate_citation(
        source_type,
        fields,
        mode=mode,
        output_style=output_style,
    )
    return {
        "source_type": source_type,
        "mode": mode,
        "output_style": output_style,
        "citation": citation,
        "facts_used": fields,
    }


@mcp.tool()
async def verify_case_citations(text: str) -> dict[str, Any]:
    """Verify and normalize U.S. case citations through CourtListener.

    Requires COURTLISTENER_TOKEN. CourtListener can validate case citations but does
    not validate statutes, law journals, Id., or supra citations.
    """
    return await _verify_case_citations(text)


@mcp.tool()
def explain_issue(code: str, mode: str = "bluepages") -> dict[str, Any]:
    """Explain an AutoCite issue code and identify its Bluepages or Whitepages rule family."""
    return _explain_issue(code, mode=mode)


@mcp.tool()
def list_capabilities() -> dict[str, Any]:
    """List AutoCite's supported sources, safe fixes, verification coverage, and guardrails."""
    return _list_capabilities()


@mcp.resource("autocite://capabilities")
def capabilities_resource() -> str:
    """Machine-readable AutoCite capability and limitation manifest."""
    return json.dumps(_list_capabilities(), indent=2, ensure_ascii=False)


@mcp.resource("autocite://rules/{mode}")
def rules_resource(mode: str) -> str:
    """Issue-code catalog with mode-specific rule-family references."""
    normalized_mode = validate_mode(mode)
    payload = {
        code: {
            "title": metadata["title"],
            "description": metadata["description"],
            "severity": metadata["severity"],
            "autofix": metadata["autofix"],
            "rule": metadata[
                "bluepages_rule" if normalized_mode == "bluepages" else "whitepages_rule"
            ],
        }
        for code, metadata in RULE_CATALOG.items()
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


@mcp.prompt()
def court_filing_citecheck(document_text: str, jurisdiction: str = "unspecified") -> str:
    """Create a practitioner-focused citation-audit instruction."""
    return f"""Audit the following court or practitioner document using AutoCite's
Bluepages mode. First call check_citations with mode='bluepages'. Then call
verify_case_citations for case authorities when available. Apply only safe mechanical
fixes. Separately identify unresolved pincites, ambiguous short forms, local-rule or
jurisdiction-specific questions, and authorities that require substantive source
review. Jurisdiction: {jurisdiction}.

DOCUMENT:
{document_text}"""


@mcp.prompt()
def law_review_citecheck(document_text: str) -> str:
    """Create an academic/Whitepages citation-audit instruction."""
    return f"""Audit the following academic legal writing using AutoCite's Whitepages
mode. First call check_citations with mode='whitepages'. Verify case citations when
possible, review internet citations for durable archives, and preserve a clear split
between safe mechanical fixes and edits requiring source or editorial judgment.
Do not invent authors, dates, pincites, parentheticals, or publication facts.

DOCUMENT:
{document_text}"""


@mcp.prompt()
def citation_repair(citation: str, mode: str = "bluepages") -> str:
    """Create a focused single-citation repair instruction."""
    return f"""Call check_single_citation on the citation below in {mode} mode. Explain
each issue briefly, return the safest corrected form, and clearly identify any missing
facts that prevent a definitive correction. Do not guess.

CITATION:
{citation}"""


def main() -> None:
    transport = os.getenv("AUTOCITE_TRANSPORT", "stdio").strip().lower()
    allowed = {"stdio", "sse", "streamable-http"}
    if transport not in allowed:
        raise ValueError(f"AUTOCITE_TRANSPORT must be one of {sorted(allowed)}")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
