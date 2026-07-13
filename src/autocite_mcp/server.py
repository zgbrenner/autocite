from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.types import ToolAnnotations

from . import __version__
from .formatters import generate_citation as _generate_citation
from .knowledge import CORE_RULES, get_knowledge_pack
from .rules import RULE_CATALOG, validate_mode
from .tools import (
    check_citations as _check_citations,
    check_single_citation as _check_single_citation,
    convert_citation as _convert_citation,
    explain_issue as _explain_issue,
    get_citation_guidance as _get_citation_guidance,
    list_capabilities as _list_capabilities,
    review_document as _review_document,
    verify_case_citations as _verify_case_citations,
)

_HOST = os.getenv("AUTOCITE_HOST", "127.0.0.1")
_PORT = int(os.getenv("PORT", os.getenv("AUTOCITE_PORT", "8000")))
_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
_NETWORK_READ = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

mcp = FastMCP(
    "AutoCite",
    website_url="https://github.com/zgbrenner/autocite",
    instructions=(
        "AutoCite is the citation specialist for U.S. legal writing. When a user asks "
        "to check, fix, clean up, Bluebook, citecheck, or review citations, call "
        "review_document first rather than answering from memory. Let that tool choose "
        "Bluepages or Whitepages unless the user specifies a mode. Use corrected_text "
        "as the base, consult the returned knowledge for unresolved issues, preserve "
        "non-citation prose, and never invent source facts. Use the granular tools only "
        "for follow-up work. Never treat formatting as proof that authority exists, is "
        "good law, controls, or supports the proposition."
    ),
    host=_HOST,
    port=_PORT,
    stateless_http=True,
    json_response=True,
)


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health_check(request: Request) -> JSONResponse:
    """Public liveness endpoint for container platforms and connector diagnostics."""
    return JSONResponse(
        {
            "status": "ok",
            "service": "autocite-mcp",
            "version": __version__,
            "mcp_endpoint": "/mcp",
        }
    )


@mcp.tool(
    title="Review and fix legal citations (start here)",
    annotations=_NETWORK_READ,
)
async def review_document(
    text: str,
    document_type: str = "auto",
    mode: str = "auto",
    jurisdiction: str | None = None,
    apply_safe_fixes: bool = True,
    verify_cases: bool = False,
) -> dict[str, Any]:
    """Start here for any request to check or fix citations in legal writing.

    Automatically detects whether Bluepages or Whitepages applies, inventories the
    citations, applies safe mechanical fixes, returns the relevant citation knowledge
    pack for the host model, and supplies an explicit response contract for unresolved
    issues. Set verify_cases=true to optionally query CourtListener when configured.
    """
    return await _review_document(
        text,
        document_type=document_type,
        mode=mode,
        jurisdiction=jurisdiction,
        apply_safe_fixes=apply_safe_fixes,
        verify_cases=verify_cases,
    )


@mcp.tool(title="Get legal citation guidance", annotations=_READ_ONLY)
def get_citation_guidance(
    mode: str = "bluepages",
    source_type: str = "all",
) -> dict[str, Any]:
    """Get a compact original citation playbook for one mode and source type.

    Use this after review_document when a remaining issue requires LLM judgment, or
    before generating a citation whose source-specific fields or checks are unclear.
    Source types include case, statute, regulation, constitution, journal_article,
    book, court_document, internet, ai_content, archival, and short_form.
    """
    return _get_citation_guidance(mode=mode, source_type=source_type)


@mcp.tool(title="Audit citation formatting", annotations=_READ_ONLY)
def check_citations(
    text: str,
    mode: str = "bluepages",
    apply_safe_fixes: bool = False,
) -> dict[str, Any]:
    """Advanced: audit legal writing in an explicitly selected citation mode."""
    return _check_citations(text, mode=mode, apply_safe_fixes=apply_safe_fixes)


@mcp.tool(title="Apply safe citation fixes", annotations=_READ_ONLY)
def fix_citations(text: str, mode: str = "bluepages") -> dict[str, Any]:
    """Advanced: apply only deterministic, high-confidence mechanical citation fixes."""
    return _check_citations(text, mode=mode, apply_safe_fixes=True)


@mcp.tool(title="Check one legal citation", annotations=_READ_ONLY)
def check_single_citation(
    citation: str,
    mode: str = "bluepages",
) -> dict[str, Any]:
    """Check exactly one recognized citation and return a focused correction report."""
    return _check_single_citation(citation, mode=mode)


@mcp.tool(title="Convert a legal citation", annotations=_READ_ONLY)
def convert_citation(
    citation: str,
    target_mode: str,
    output_style: str = "plain",
) -> dict[str, Any]:
    """Convert a recognized citation using only facts already present in it."""
    return _convert_citation(
        citation,
        target_mode=target_mode,
        output_style=output_style,
    )


@mcp.tool(title="Generate a legal citation", annotations=_READ_ONLY)
def generate_citation(
    source_type: str,
    fields: dict[str, Any],
    mode: str = "bluepages",
    output_style: str = "plain",
) -> dict[str, Any]:
    """Generate a citation from structured source facts; error rather than guess."""
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


@mcp.tool(title="Verify U.S. case citations", annotations=_NETWORK_READ)
async def verify_case_citations(text: str) -> dict[str, Any]:
    """Verify and normalize U.S. case citations through optional CourtListener lookup."""
    return await _verify_case_citations(text)


@mcp.tool(title="Explain a citation issue", annotations=_READ_ONLY)
def explain_issue(code: str, mode: str = "bluepages") -> dict[str, Any]:
    """Explain an AutoCite issue code and its relevant rule family."""
    return _explain_issue(code, mode=mode)


@mcp.tool(title="List AutoCite capabilities", annotations=_READ_ONLY)
def list_capabilities() -> dict[str, Any]:
    """List supported workflows, source types, verification coverage, and guardrails."""
    return _list_capabilities()


@mcp.resource("autocite://capabilities", mime_type="application/json")
def capabilities_resource() -> str:
    """Machine-readable AutoCite capability and limitation manifest."""
    return json.dumps(_list_capabilities(), indent=2, ensure_ascii=False)


@mcp.resource("autocite://knowledge/core", mime_type="application/json")
def core_knowledge_resource() -> str:
    """Core non-fabrication and citechecking principles for every workflow."""
    return json.dumps({"core_rules": CORE_RULES}, indent=2, ensure_ascii=False)


@mcp.resource("autocite://rules/{mode}", mime_type="application/json")
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


@mcp.resource(
    "autocite://knowledge/{mode}/{source_type}",
    mime_type="application/json",
)
def knowledge_resource(mode: str, source_type: str) -> str:
    """Mode- and source-specific citation playbook for model context."""
    selected = None if source_type.lower() == "all" else [source_type]
    return json.dumps(
        get_knowledge_pack(mode, selected),
        indent=2,
        ensure_ascii=False,
    )


@mcp.prompt(title="Complete legal citation review")
def complete_citecheck(
    document_text: str,
    document_type: str = "auto",
    jurisdiction: str = "unspecified",
) -> str:
    """Run the easiest complete Bluepages-or-Whitepages citecheck workflow."""
    return f"""Call review_document first with the text below, document_type={document_type!r},
and jurisdiction={jurisdiction!r}. Use automatic mode detection unless the user has
specified otherwise. Use corrected_text as the base. Then apply the returned knowledge
to any remaining issues only when all required facts are present. Preserve non-citation
prose. Return: (1) the corrected document, (2) a concise change log, and (3) a clearly
labeled source-review list for anything unresolved. Never invent citation facts.

DOCUMENT:
{document_text}"""


@mcp.prompt(title="Court filing citecheck")
def court_filing_citecheck(document_text: str, jurisdiction: str = "unspecified") -> str:
    """Create a practitioner-focused citation-audit instruction."""
    return complete_citecheck(document_text, "court_filing", jurisdiction)


@mcp.prompt(title="Law review citecheck")
def law_review_citecheck(document_text: str) -> str:
    """Create an academic/Whitepages citation-audit instruction."""
    return complete_citecheck(document_text, "law_review", "unspecified")


@mcp.prompt(title="Repair one citation")
def citation_repair(citation: str, mode: str = "bluepages") -> str:
    """Create a focused single-citation repair instruction."""
    return f"""Call check_single_citation on the citation below in {mode} mode. If the
result leaves a source-specific question, call get_citation_guidance for that source.
Explain each issue briefly, return the safest corrected form, and identify missing facts.
Do not guess.

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
