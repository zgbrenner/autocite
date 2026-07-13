from __future__ import annotations

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


def _normalize_reporter(reporter: str) -> str:
    compact = re.sub(r"\s+", " ", reporter.strip())
    key = re.sub(r"[.\s]", "", compact).upper()
    aliases = {
        "US": "U.S.",
        "SCT": "S. Ct.",
        "F": "F.",
        "F2D": "F.2d",
        "F3D": "F.3d",
        "FSUPP": "F. Supp.",
        "FSUPP2D": "F. Supp. 2d",
        "FSUPP3D": "F. Supp. 3d",
        "LED": "L. Ed.",
        "LED2D": "L. Ed. 2d",
    }
    return aliases.get(key, compact)


def _normalize_code(code: str) -> str:
    key = re.sub(r"[.\s]", "", code).upper()
    return {
        "USC": "U.S.C.",
        "CFR": "C.F.R.",
    }.get(key, re.sub(r"\s+", " ", code.strip()))


def _case(fields: Mapping[str, Any], mode: str, output_style: str) -> str:
    values = _required(
        fields, ("case_name", "volume", "reporter", "first_page", "year")
    )
    case_name = values["case_name"]
    if output_style == "markdown" and mode == "bluepages":
        case_name = f"*{case_name}*"
    elif output_style == "html" and mode == "bluepages":
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
    values = _required(fields, ("title", "code", "section"))
    year = _optional(fields, "year")
    result = (
        f"{values['title']} {_normalize_code(values['code'])} § "
        f"{values['section'].lstrip('§ ').strip()}"
    )
    return f"{result} ({year})" if year else result


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
    if output_style == "markdown" and mode == "bluepages":
        title = f"*{title}*"
    elif output_style == "html" and mode == "bluepages":
        title = f"<i>{title}</i>"
    pincite = _optional(fields, "pincite")
    edition = _optional(fields, "edition")
    result = f"{values['author']}, {title}"
    if pincite:
        result += f" {pincite}"
    parenthetical = " ".join(part for part in (edition, values["year"]) if part)
    return f"{result} ({parenthetical})"


def _website(fields: Mapping[str, Any], _mode: str, _style: str) -> str:
    values = _required(fields, ("title", "site", "url"))
    author = _optional(fields, "author")
    date = _optional(fields, "date")
    archive_url = _optional(fields, "archive_url")
    on_file = bool(fields.get("on_file_with_author", False))
    lead = f"{author}, " if author else ""
    result = f"{lead}{values['title']}, {values['site']}"
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
    return formatter(fields, normalized_mode, normalized_style)


def supported_source_types() -> list[str]:
    return sorted(_FORMATTERS)
