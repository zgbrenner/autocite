"""Build a court- and reviewer-facing citation audit report from a review result.

Standing orders in a growing number of courts require counsel to certify that
citations in a filing were verified. This module turns an AutoCite review into
a truthful, human-readable audit trail: what was checked, what was fixed, what
was verified against a source, and what still requires human review. It never
claims more than the review actually did.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from . import __version__

VERIFICATION_TIERS = {
    "mechanical_only": "Deterministic format checks only; not compared against any source.",
    "source_matched": "The citation was matched to an authority in the CourtListener database.",
    "source_not_matched": "CourtListener lookup ran but did not match this citation to an authority.",
    "evidence_prepared": "Primary source text was retrieved and compared for quotation and page markers.",
}


def _citation_key(citation: dict[str, Any]) -> str:
    return str(citation.get("text") or "").strip().lower()


def _verification_tier(
    citation: dict[str, Any],
    verified_keys: dict[str, str],
    deep_keys: dict[str, str],
) -> str:
    key = _citation_key(citation)
    if citation.get("source_type") != "case":
        return "mechanical_only"
    if key in deep_keys:
        return deep_keys[key]
    # Lookup results carry the bare reporter citation (e.g. "410 U.S. 113"),
    # which appears inside the fuller inventory text.
    for verified_key, tier in verified_keys.items():
        if verified_key == key or verified_key in key:
            return tier
    return "mechanical_only"


def build_certification_report(
    review: dict[str, Any],
    *,
    prepared_for: str | None = None,
) -> dict[str, Any]:
    """Derive a structured audit report plus Markdown rendering from a review result."""
    original_text = str(review.get("original_text") or "")
    citations = list(review.get("citation_inventory") or [])
    applied_edits = list(review.get("applied_edits") or [])
    remaining = list(review.get("remaining_issues") or [])
    verification = dict(review.get("case_verification") or {})
    deep = dict(review.get("deep_review_results") or {})
    graph = dict(review.get("citation_graph") or {})

    verification_ran = bool(verification.get("available"))
    deep_ran = bool(deep.get("available")) and bool(deep.get("cases"))

    verified_keys: dict[str, str] = {}
    for result in verification.get("results") or []:
        key = str(result.get("citation") or "").strip().lower()
        if not key:
            continue
        verified_keys[key] = "source_matched" if result.get("verified") else "source_not_matched"

    deep_keys: dict[str, str] = {}
    for case in deep.get("cases") or []:
        key = _citation_key(case.get("citation") or {})
        if not key:
            continue
        deep_keys[key] = (
            "evidence_prepared"
            if case.get("status") == "evidence_prepared"
            else "source_not_matched"
        )

    entries: list[dict[str, Any]] = []
    tier_counts: dict[str, int] = {tier: 0 for tier in VERIFICATION_TIERS}
    for citation in citations:
        tier = _verification_tier(citation, verified_keys, deep_keys)
        tier_counts[tier] += 1
        entries.append(
            {
                "citation": citation.get("text"),
                "source_type": citation.get("source_type"),
                "span": [citation.get("start"), citation.get("end")],
                "verification_tier": tier,
            }
        )

    unresolved_short_forms = [
        item
        for item in (graph.get("resolutions") or [])
        if not item.get("resolved_authority_id")
    ]

    generated_at = datetime.now(timezone.utc).replace(microsecond=0)
    fingerprint = hashlib.sha256(original_text.encode("utf-8")).hexdigest()

    checks_performed = [
        "Deterministic citation-format review of every detected citation.",
        f"{len(applied_edits)} safe automatic formatting edit(s) applied.",
        f"{len(remaining)} formatting issue(s) left for human review.",
    ]
    checks_not_performed = []
    if verification_ran:
        matched = sum(1 for tier in verified_keys.values() if tier == "source_matched")
        checks_performed.append(
            f"CourtListener citation lookup for case citations ({matched} matched)."
        )
    else:
        checks_not_performed.append(
            "No citation was checked for existence against any source database."
        )
    if deep_ran:
        checks_performed.append(
            "Primary source text retrieved for matched cases; quotations and page "
            "markers compared deterministically."
        )
    else:
        checks_not_performed.append(
            "No quotation or page marker was compared against primary source text."
        )
    checks_not_performed.extend(
        [
            "Good-law status (subsequent history and treatment) was not assessed; AutoCite is not a citator.",
            "Whether any authority supports any proposition was not assessed.",
        ]
    )

    statement = (
        f"AutoCite {__version__} reviewed this document on {generated_at.isoformat()}. "
        "The checks listed under 'Checks performed' were completed by deterministic code; "
        "everything under 'Not checked by this review' remains the responsibility of a "
        "human reviewer. AutoCite does not claim complete Bluebook compliance, does not "
        "determine good-law status, and does not determine whether an authority supports "
        "a proposition. This report is an audit trail of automated review, not a "
        "certification of legal accuracy."
    )

    report = {
        "schema_version": "1.0",
        "report_type": "citation_review_audit",
        "generated_at": generated_at.isoformat(),
        "tool_version": __version__,
        "prepared_for": prepared_for,
        "document_sha256": fingerprint,
        "document_characters": len(original_text),
        "mode": review.get("mode"),
        "jurisdiction": review.get("jurisdiction"),
        "citation_count": len(citations),
        "verification_tier_counts": tier_counts,
        "verification_tier_legend": VERIFICATION_TIERS,
        "checks_performed": checks_performed,
        "checks_not_performed": checks_not_performed,
        "applied_edit_count": len(applied_edits),
        "outstanding_issue_count": len(remaining),
        "unresolved_short_form_count": len(unresolved_short_forms),
        "citations": entries,
        "statement": statement,
    }
    report["markdown"] = _render_markdown(report)
    return report


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Citation Review Audit Report",
        "",
        f"- Generated: {report['generated_at']} by AutoCite {report['tool_version']}",
        f"- Document SHA-256: `{report['document_sha256']}`",
        f"- Mode: {report['mode']} | Jurisdiction: {report['jurisdiction']}",
        f"- Citations reviewed: {report['citation_count']}",
    ]
    if report.get("prepared_for"):
        lines.append(f"- Prepared for: {report['prepared_for']}")
    lines += ["", "## Checks performed", ""]
    lines += [f"- {item}" for item in report["checks_performed"]]
    lines += ["", "## Not checked by this review", ""]
    lines += [f"- {item}" for item in report["checks_not_performed"]]
    lines += [
        "",
        "## Citations",
        "",
        "| # | Citation | Type | Verification tier |",
        "|---|----------|------|-------------------|",
    ]
    for index, entry in enumerate(report["citations"], start=1):
        citation = str(entry.get("citation") or "").replace("|", "\\|")
        lines.append(
            f"| {index} | {citation} | {entry.get('source_type')} | {entry.get('verification_tier')} |"
        )
    counts = report["verification_tier_counts"]
    lines += ["", "## Verification tier summary", ""]
    for tier, description in report["verification_tier_legend"].items():
        lines.append(f"- **{tier}** ({counts.get(tier, 0)}): {description}")
    if report["unresolved_short_form_count"]:
        lines += [
            "",
            f"**{report['unresolved_short_form_count']} short-form citation(s) could not be "
            "resolved to an antecedent and require human review.**",
        ]
    lines += ["", "## Statement", "", report["statement"], ""]
    return "\n".join(lines)
