from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .rules import validate_mode

DOCUMENT_TYPE_MODES = {
    "brief": "bluepages",
    "court_filing": "bluepages",
    "motion": "bluepages",
    "pleading": "bluepages",
    "practitioner_memo": "bluepages",
    "legal_memo": "bluepages",
    "memorandum": "bluepages",
    "law_review": "whitepages",
    "journal_article": "whitepages",
    "academic": "whitepages",
    "seminar_paper": "whitepages",
    "student_note": "whitepages",
    "student_comment": "whitepages",
}

CORE_RULES = [
    "Never invent a reporter, court, year, author, title, page, pincite, date, URL, or parenthetical.",
    "Preserve non-citation prose and quotations unless the user separately asks for substantive editing.",
    "Apply deterministic mechanical fixes first; label source-dependent questions for review.",
    "A correctly formatted citation is not proof that the authority exists, is good law, controls, or supports the proposition.",
    "Local court rules, journal manuals, and source-specific citation rules override general guidance when they conflict.",
]

GENERAL_GUIDANCE = [
    "Treat signals as claims about the relationship between the cited authority and the proposition; do not add or change a signal without reading the source.",
    "Use a pincite for quotations and for propositions supported by a specific page, paragraph, section, or footnote.",
    "Keep citation clauses and citation sentences grammatically separate from the surrounding prose and punctuate them consistently.",
    "Order multiple authorities according to the applicable source hierarchy and chronology only after confirming what each authority is being cited to establish.",
    "Use explanatory parentheticals when the signal, authority, or context does not make the source's relevance apparent.",
    "Preserve quotation alterations, omissions, and internal-citation treatment accurately; formatting cleanup must not change the quoted meaning.",
]

MODE_GUIDANCE: dict[str, dict[str, Any]] = {
    "bluepages": {
        "audience": "courts, lawyers, law clerks, and practitioner memoranda",
        "priorities": [
            "Use practitioner typography rather than law-review small capitals.",
            "Follow the filing court's local rules and judge-specific requirements before general citation conventions.",
            "Prefer readable citation sentences and clauses that preserve the document's existing prose.",
            "Use short forms only when the antecedent is unmistakable in the filing context.",
        ],
    },
    "whitepages": {
        "audience": "law reviews, journals, seminar papers, and academic legal writing",
        "priorities": [
            "Apply academic typography and the publication's house style consistently.",
            "Review signals, explanatory parentheticals, source order, and pincites at footnote-level precision.",
            "Use supra and hereinafter only for source types and circumstances where they are permitted.",
            "Review internet sources for a durable archive link or an appropriate on-file statement.",
        ],
    },
}

SOURCE_GUIDANCE: dict[str, dict[str, Any]] = {
    "case": {
        "rule_families": {"bluepages": "B10", "whitepages": "Rule 10"},
        "template": "Case name, volume reporter first page, pincite (court year).",
        "required_facts": ["case name", "volume", "reporter", "first page", "year"],
        "checks": [
            "Use the correct case-name abbreviation and mode-specific typography.",
            "Confirm the reporter, first page, deciding court when required, and decision year.",
            "Add a pincite when relying on a specific proposition or quotation.",
            "Treat parallel citations and database identifiers as jurisdiction- or court-specific questions.",
        ],
    },
    "statute": {
        "rule_families": {"bluepages": "B12", "whitepages": "Rule 12"},
        "template": "Title code § section (edition or year when required).",
        "required_facts": ["code or session-law source", "section"],
        "checks": [
            "Use the preferred code or session-law source for the jurisdiction.",
            "Preserve subsection structure and use §§ only for a genuine section range or list.",
            "Include publisher, edition, supplement, or year information when needed to identify the cited text.",
        ],
    },
    "regulation": {
        "rule_families": {"bluepages": "B14", "whitepages": "Rule 14"},
        "template": "Title C.F.R. § section (year).",
        "required_facts": ["title", "code", "section", "year"],
        "checks": [
            "Use the jurisdiction's preferred administrative code and abbreviation.",
            "Confirm the regulation year or currency information rather than assuming it.",
            "Distinguish regulations from administrative decisions, guidance, and register notices.",
        ],
    },
    "constitution": {
        "rule_families": {"bluepages": "B11", "whitepages": "Rule 11"},
        "template": "Constitution abbreviation art./amend. subdivision.",
        "required_facts": ["constitution", "article or amendment"],
        "checks": [
            "Identify the correct constitution and subdivision.",
            "Use article, amendment, section, clause, and paragraph labels consistently.",
        ],
    },
    "journal_article": {
        "rule_families": {"bluepages": "B16", "whitepages": "Rule 16"},
        "template": "Author, article title, volume journal first page, pincite (year).",
        "required_facts": ["author", "title", "volume", "journal", "first page", "year"],
        "checks": [
            "Apply mode-specific typography to the author, title, and journal name.",
            "Use the publication's accepted journal abbreviation.",
            "Include a pincite for the relied-on passage and a DOI only when appropriate.",
        ],
    },
    "book": {
        "rule_families": {"bluepages": "B15", "whitepages": "Rule 15"},
        "template": "Author(s), title pincite (editor/translator, edition year as applicable).",
        "required_facts": ["author or institutional author", "title", "year"],
        "checks": [
            "List the available authors accurately; do not invent or silently omit contributors.",
            "Include edition, editor, translator, volume, and publisher facts only when the source requires them.",
            "Use a page, section, or paragraph pincite that matches the source's organization.",
        ],
    },
    "court_document": {
        "rule_families": {"bluepages": "B17", "whitepages": "Rule 17"},
        "template": "Document title, pincite, case name, docket number (court filing date).",
        "required_facts": ["document title", "case or proceeding", "docket information", "date"],
        "checks": [
            "Use the actual docket number and filing date.",
            "Identify the document and electronic docket entry precisely enough to retrieve it.",
            "Follow the filing court's local citation convention when it differs.",
        ],
    },
    "internet": {
        "rule_families": {"bluepages": "B18", "whitepages": "Rule 18"},
        "template": "Author, page title, website, publication/update date, URL, archive information.",
        "required_facts": ["page title", "URL"],
        "checks": [
            "Use the page's actual author, title, site name, and date when available.",
            "Review the citation for a durable archive link or an appropriate on-file statement.",
            "Do not infer a publication date from an access date or copyright footer.",
        ],
    },
    "ai_content": {
        "rule_families": {"bluepages": "B18", "whitepages": "Rule 18.3"},
        "template": "Model or system, provider, description of query/output, query date, permanent archive or on-file copy.",
        "required_facts": ["model", "provider", "date", "retrievable record"],
        "checks": [
            "Identify the model and provider actually used.",
            "Preserve a stable record of the prompt and output through an archive or on-file copy.",
            "Do not present generated content as an independently verified authority.",
        ],
    },
    "archival": {
        "rule_families": {"bluepages": "B23", "whitepages": "Rule 23"},
        "template": "Author, document title, pincite (date) (repository, collection, location).",
        "required_facts": ["document identity", "date if known", "repository or custodian"],
        "checks": [
            "Provide enough collection, box, folder, item, and location data to retrieve the material.",
            "Describe undated or uncertain material transparently rather than supplying a guessed date.",
        ],
    },
    "short_form": {
        "rule_families": {"bluepages": "B4", "whitepages": "Rule 4"},
        "template": "Id.; shortened case form; or permitted supra/hereinafter form with pincite.",
        "required_facts": ["unambiguous antecedent"],
        "checks": [
            "Use Id. only when it unambiguously refers to the immediately preceding authority.",
            "Add ‘at’ before a page pincite when the short form requires it.",
            "Do not use supra as a substitute for a case or statute short form.",
            "Create a hereinafter form only when the full citation is cumbersome and will recur.",
        ],
    },
    "foreign_international_tribal": {
        "rule_families": {"bluepages": "B20–B22", "whitepages": "Rules 20–22"},
        "template": "Use the source jurisdiction's preferred form, then the applicable general fallback.",
        "required_facts": ["jurisdiction or sovereign", "source type", "retrieval information"],
        "checks": [
            "Defer to an established sovereign or jurisdiction-specific citation system when one exists.",
            "Flag translation, transliteration, parallel-source, and jurisdiction-table questions for source review.",
        ],
    },
}


def infer_citation_mode(*, document_type: str = "auto", text: str = "", explicit_mode: str = "auto") -> dict[str, Any]:
    """Infer Bluepages or Whitepages mode with an explainable confidence signal."""
    from .document_ir import classify_document_mode, parse_text_ir

    normalized_type = document_type.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized_type in {"", "unknown", "unspecified"}:
        normalized_type = "auto"
    ir = parse_text_ir(text)
    return classify_document_mode(
        ir,
        explicit_mode=explicit_mode,
        document_type=normalized_type,
    )


def _normalize_source_types(source_types: Iterable[str] | None) -> list[str]:
    if source_types is None:
        return list(SOURCE_GUIDANCE)
    aliases = {
        "internet_url": "internet",
        "website": "internet",
        "case_law": "case",
        "periodical": "journal_article",
        "short_forms": "short_form",
        "statutes": "statute",
        "regulations": "regulation",
    }
    normalized: list[str] = []
    for source_type in source_types:
        key = aliases.get(source_type.strip().lower(), source_type.strip().lower())
        if key in SOURCE_GUIDANCE and key not in normalized:
            normalized.append(key)
    if source_types is not None and not normalized:
        raise ValueError(f"Unknown source type. Choose one of {sorted(SOURCE_GUIDANCE)} or all")
    return normalized or list(SOURCE_GUIDANCE)


def get_knowledge_pack(mode: str, source_types: Iterable[str] | None = None) -> dict[str, Any]:
    """Return an original, compact citation playbook suitable for an LLM tool result."""
    normalized_mode = validate_mode(mode)
    selected = _normalize_source_types(source_types)
    sources: dict[str, dict[str, Any]] = {}
    for key in selected:
        guidance = dict(SOURCE_GUIDANCE[key])
        rule_families = guidance.pop("rule_families")
        guidance["rule_family"] = rule_families[normalized_mode]
        sources[key] = guidance
    return {
        "mode": normalized_mode,
        "core_rules": CORE_RULES,
        "general_guidance": GENERAL_GUIDANCE,
        "mode_guidance": MODE_GUIDANCE[normalized_mode],
        "sources": sources,
        "use": (
            "Use these summaries to reason about unresolved citation-format questions. "
            "They are not a substitute for the official manual, local rules, a journal's "
            "house style, or source verification."
        ),
    }
