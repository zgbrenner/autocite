from __future__ import annotations

import html
import re
from collections.abc import Mapping
from typing import Any, Callable

from .rules import validate_mode, validate_output_style


def _required(fields: Mapping[str, Any], names: tuple[str, ...]) -> dict[str, str]:
    missing = [name for name in names if not str(fields.get(name, "")).strip()]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")
    return {name: str(fields[name]).strip() for name in names}


def _optional(fields: Mapping[str, Any], name: str) -> str | None:
    value = fields.get(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# Canonical reporter abbreviations keyed by their period/space-stripped form, so
# a mechanically malformed reporter ("P2d", "so.2d", "N E 2d") normalizes to the
# Bluebook (Table T1) spelling. Single-capital initialisms close up with their
# ordinal ("P.2d", "N.E.2d"); multi-letter word abbreviations keep a space
# before the ordinal ("So. 2d", "F. Supp. 2d"). This never invents a reporter —
# an unrecognized key is returned unchanged apart from whitespace collapsing.
_REPORTER_ALIASES = {
    # Federal
    "US": "U.S.",
    "SCT": "S. Ct.",
    "LED": "L. Ed.",
    "LED2D": "L. Ed. 2d",
    "F": "F.",
    "F2D": "F.2d",
    "F3D": "F.3d",
    "F4TH": "F.4th",
    "FSUPP": "F. Supp.",
    "FSUPP2D": "F. Supp. 2d",
    "FSUPP3D": "F. Supp. 3d",
    "FAPPX": "F. App'x",
    "FEDCL": "Fed. Cl.",
    # Regional reporters (Table T1)
    "A": "A.",
    "A2D": "A.2d",
    "A3D": "A.3d",
    "P": "P.",
    "P2D": "P.2d",
    "P3D": "P.3d",
    "NE": "N.E.",
    "NE2D": "N.E.2d",
    "NE3D": "N.E.3d",
    "NW": "N.W.",
    "NW2D": "N.W.2d",
    "NW3D": "N.W.3d",
    "SE": "S.E.",
    "SE2D": "S.E.2d",
    "SW": "S.W.",
    "SW2D": "S.W.2d",
    "SW3D": "S.W.3d",
    "SO": "So.",
    "SO2D": "So. 2d",
    "SO3D": "So. 3d",
    "NYS": "N.Y.S.",
    "NYS2D": "N.Y.S.2d",
    "NYS3D": "N.Y.S.3d",
    "CALRPTR": "Cal. Rptr.",
    "CALRPTR2D": "Cal. Rptr. 2d",
    "CALRPTR3D": "Cal. Rptr. 3d",
}


def _normalize_reporter(reporter: str) -> str:
    compact = re.sub(r"\s+", " ", reporter.strip())
    key = re.sub(r"[.\s]", "", compact).upper()
    return _REPORTER_ALIASES.get(key, compact)


def _normalize_code(code: str) -> str:
    key = re.sub(r"[.\s]", "", code).upper()
    return {
        "USC": "U.S.C.",
        "USCA": "U.S.C.A.",
        "USCS": "U.S.C.S.",
        "CFR": "C.F.R.",
        "FEDREG": "Fed. Reg.",
    }.get(key, re.sub(r"\s+", " ", code.strip()))


def _case(fields: Mapping[str, Any], mode: str, output_style: str) -> str:
    values = _required(
        fields, ("case_name", "volume", "reporter", "first_page", "year")
    )
    case_name = values["case_name"]
    if output_style == "markdown":
        case_name = f"*{case_name}*"
    elif output_style == "html":
        case_name = f"<i>{case_name}</i>"

    reporter = _normalize_reporter(values["reporter"])
    pincite = _optional(fields, "pincite")
    court = _optional(fields, "court")
    parenthetical = " ".join(part for part in (court, values["year"]) if part)
    result = f"{case_name}, {values['volume']} {reporter} {values['first_page']}"
    if pincite:
        result += f", {pincite}"
    return f"{result} ({parenthetical})"


def _statute(fields: Mapping[str, Any], _mode: str, _style: str) -> str:
    values = _required(fields, ("title", "code", "section"))
    year = _optional(fields, "year")
    result = (
        f"{values['title']} {_normalize_code(values['code'])} § "
        f"{values['section'].lstrip('§ ').strip()}"
    )
    return f"{result} ({year})" if year else result


def _regulation(fields: Mapping[str, Any], _mode: str, _style: str) -> str:
    # Unlike a federal statute (where the year became optional in the 21st
    # edition), a full C.F.R. citation still requires the year of the code
    # edition (BP Rule B14 / Rule 14.2). Requiring it here refuses to present an
    # incomplete regulation citation as finished rather than inventing a year.
    values = _required(fields, ("title", "code", "section", "year"))
    result = (
        f"{values['title']} {_normalize_code(values['code'])} § "
        f"{values['section'].lstrip('§ ').strip()}"
    )
    return f"{result} ({values['year']})"


def _constitution(fields: Mapping[str, Any], _mode: str, _style: str) -> str:
    values = _required(fields, ("constitution", "subdivision"))
    return f"{values['constitution']} {values['subdivision']}"


def _journal(fields: Mapping[str, Any], _mode: str, _style: str) -> str:
    values = _required(
        fields,
        ("author", "title", "volume", "journal", "first_page", "year"),
    )
    pincite = _optional(fields, "pincite")
    result = (
        f"{values['author']}, {values['title']}, {values['volume']} "
        f"{values['journal']} {values['first_page']}"
    )
    if pincite:
        result += f", {pincite}"
    return f"{result} ({values['year']})"


def _book(fields: Mapping[str, Any], mode: str, output_style: str) -> str:
    values = _required(fields, ("author", "title", "year"))
    title = values["title"]
    if output_style == "markdown":
        title = f"*{title}*"
    elif output_style == "html":
        title = f"<i>{title}</i>"
    pincite = _optional(fields, "pincite")
    edition = _optional(fields, "edition")
    result = f"{values['author']}, {title}"
    if pincite:
        result += f" {pincite}"
    parenthetical = " ".join(part for part in (edition, values["year"]) if part)
    return f"{result} ({parenthetical})"


def _website(fields: Mapping[str, Any], _mode: str, output_style: str) -> str:
    values = _required(fields, ("title", "site", "url"))
    # The specific-page title takes the same italic/underline typeface as a case
    # name or book title (BP Rule B18.1.1 / Rule 18.2.2(b)(ii)).
    title = values["title"]
    if output_style == "markdown":
        title = f"*{title}*"
    elif output_style == "html":
        title = f"<i>{title}</i>"
    author = _optional(fields, "author")
    date = _optional(fields, "date")
    archive_url = _optional(fields, "archive_url")
    on_file = bool(fields.get("on_file_with_author", False))
    lead = f"{author}, " if author else ""
    result = f"{lead}{title}, {values['site']}"
    if date:
        result += f" ({date})"
    result += f", {values['url']}"
    if archive_url:
        result += f" [archived at {archive_url}]"
    elif on_file:
        result += " (on file with author)"
    return result


def _court_document(fields: Mapping[str, Any], _mode: str, _style: str) -> str:
    values = _required(fields, ("document_title", "case_name", "docket_number"))
    court = _optional(fields, "court")
    date = _optional(fields, "date")
    entry = _optional(fields, "docket_entry")
    result = (
        f"{values['document_title']}, {values['case_name']}, "
        f"No. {values['docket_number']}"
    )
    if entry:
        result += f", ECF No. {entry}"
    parenthetical = " ".join(part for part in (court, date) if part)
    return f"{result} ({parenthetical})" if parenthetical else result


def _ai_content(fields: Mapping[str, Any], _mode: str, _style: str) -> str:
    values = _required(fields, ("model", "provider", "date"))
    prompt_title = _optional(fields, "prompt_title") or "Response to author query"
    archive_url = _optional(fields, "archive_url")
    on_file = bool(fields.get("on_file_with_author", False))
    if not archive_url and not on_file:
        raise ValueError("AI content requires archive_url or on_file_with_author=true")
    result = f"{values['model']} ({values['provider']}), {prompt_title} ({values['date']})"
    return result + (f", {archive_url}" if archive_url else " (on file with author)")


def _archival(fields: Mapping[str, Any], _mode: str, _style: str) -> str:
    values = _required(fields, ("author", "document_title", "date", "archive"))
    collection = _optional(fields, "collection")
    location = _optional(fields, "location")
    pincite = _optional(fields, "pincite")
    result = f"{values['author']}, {values['document_title']}"
    if pincite:
        result += f", {pincite}"
    holding = ", ".join(
        part for part in (values["archive"], collection, location) if part
    )
    return f"{result} ({values['date']}) (on file with {holding})"


_FORMATTERS: dict[str, Callable[[Mapping[str, Any], str, str], str]] = {
    "case": _case,
    "statute": _statute,
    "regulation": _regulation,
    "constitution": _constitution,
    "journal_article": _journal,
    "book": _book,
    "website": _website,
    "court_document": _court_document,
    "ai_content": _ai_content,
    "archival": _archival,
}


def generate_citation(
    source_type: str,
    fields: Mapping[str, Any],
    *,
    mode: str = "bluepages",
    output_style: str = "plain",
) -> str:
    """Generate a citation only from supplied facts; never infer missing metadata."""
    normalized_mode = validate_mode(mode)
    normalized_style = validate_output_style(output_style)
    normalized_type = source_type.strip().lower()
    formatter = _FORMATTERS.get(normalized_type)
    if formatter is None:
        raise ValueError(f"Unsupported source_type: {source_type}")
    prepared_fields: Mapping[str, Any] = fields
    if normalized_style == "html":
        # Every formatter interpolates caller-supplied field values directly
        # into the result string (some inside <i>...</i> tags). Escape all
        # string values up front so HTML output can never inject markup.
        prepared_fields = {
            key: html.escape(value) if isinstance(value, str) else value
            for key, value in fields.items()
        }
    return formatter(prepared_fields, normalized_mode, normalized_style)


def supported_source_types() -> list[str]:
    return sorted(_FORMATTERS)
