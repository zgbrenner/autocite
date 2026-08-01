from __future__ import annotations

from typing import Any

VALID_MODES = {"bluepages", "whitepages"}
VALID_OUTPUT_STYLES = {"plain", "markdown", "html"}

RULE_CATALOG: dict[str, dict[str, Any]] = {
    "REPORTER_ABBREVIATION": {
        "title": "Reporter abbreviation normalization",
        "bluepages_rule": "B10",
        "whitepages_rule": "Rule 10",
        "severity": "error",
        "description": "Use a recognized reporter abbreviation with the required periods and spacing.",
        "autofix": True,
    },
    "STATUTE_CODE_ABBREVIATION": {
        "title": "Statutory code abbreviation",
        "bluepages_rule": "B12",
        "whitepages_rule": "Rule 12",
        "severity": "error",
        "description": "Normalize code abbreviations and place a space after the section symbol.",
        "autofix": True,
    },
    "REGULATION_CODE_ABBREVIATION": {
        "title": "Administrative code abbreviation",
        "bluepages_rule": "B14",
        "whitepages_rule": "Rule 14",
        "severity": "error",
        "description": "Normalize administrative code abbreviations and section-symbol spacing.",
        "autofix": True,
    },
    "SHORT_FORM_CAPITALIZATION": {
        "title": "Short-form capitalization",
        "bluepages_rule": "B4",
        "whitepages_rule": "Rule 4",
        "severity": "error",
        "description": "Use “Id.” with a capital I and terminal period.",
        "autofix": True,
    },
    "SHORT_FORM_ORPHAN_ID": {
        "title": "Unresolved Id. antecedent",
        "bluepages_rule": "B4",
        "whitepages_rule": "Rule 4",
        "severity": "error",
        "description": "“Id.” must unambiguously refer to the immediately preceding authority.",
        "autofix": False,
    },
    "SHORT_FORM_UNRESOLVED": {
        "title": "Unresolved short-form antecedent",
        "bluepages_rule": "B4",
        "whitepages_rule": "Rule 4",
        "severity": "error",
        "description": "A supra, short-case, or reference citation must resolve unambiguously to a prior full authority.",
        "autofix": False,
    },
    "INTERNET_ARCHIVE_REVIEW": {
        "title": "Internet-source archive review",
        "bluepages_rule": "B18",
        "whitepages_rule": "Rule 18",
        "severity": "warning",
        "description": "Review the citation for a durable archive link or an appropriate on-file statement.",
        "autofix": False,
    },
    "CASE_PINCITE_REVIEW": {
        "title": "Case pincite review",
        "bluepages_rule": "B10",
        "whitepages_rule": "Rule 10",
        "severity": "info",
        "description": "Confirm that the citation includes a pinpoint page when the proposition depends on a specific passage.",
        "autofix": False,
    },
}


def validate_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in VALID_MODES:
        raise ValueError(f"mode must be one of {sorted(VALID_MODES)}")
    return normalized


def validate_output_style(output_style: str) -> str:
    normalized = output_style.strip().lower()
    if normalized not in VALID_OUTPUT_STYLES:
        raise ValueError(
            f"output_style must be one of {sorted(VALID_OUTPUT_STYLES)}"
        )
    return normalized


def rule_reference(code: str, mode: str) -> str:
    rule = RULE_CATALOG[code]
    return str(rule["bluepages_rule" if mode == "bluepages" else "whitepages_rule"])
