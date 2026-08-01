from __future__ import annotations

import io
import re
import statistics
import zipfile
from bisect import bisect_right
from dataclasses import dataclass, field, replace
from functools import cached_property
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET

from pypdf import PdfReader


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DC_NS = "http://purl.org/dc/elements/1.1/"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NS = {"w": W_NS, "r": R_NS}
LOCATION_KINDS = {
    "heading",
    "paragraph",
    "footnote",
    "endnote",
    "table",
    "block_quotation",
}
_CITATION_HINT = re.compile(
    r"(?:\b\d+\s+(?:U\.?\s*S\.?\s*C\.?|C\.?\s*F\.?\s*R\.?|"
    r"U\.?\s*S\.?|F\.?\s*(?:2d|3d|Supp\.?))\b|\bv\.\s|\b(?:Id\.|supra)\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DocumentMetadata:
    filename: str = "document.txt"
    mime_type: str = "text/plain"
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    properties: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentBlock:
    block_id: str
    kind: str
    text: str
    absolute_start: int
    absolute_end: int
    block_local_start: int
    block_local_end: int
    order: int
    parent_id: str | None = None
    note_id: str | None = None
    note_number: str | None = None
    page_number: int | None = None
    reconstruction_confidence: str = "certain"
    coordinates: tuple[tuple[float, ...], ...] = ()
    formatting_anchor: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CitationLocation:
    block_id: str | None
    block_kind: str | None
    absolute_start: int
    absolute_end: int
    block_local_start: int | None
    block_local_end: int | None
    note_id: str | None = None
    note_number: str | None = None
    page_number: int | None = None
    reconstruction_confidence: str = "certain"
    provenance: str = "parsed_document_structure"


@dataclass(frozen=True)
class CitationOccurrence:
    occurrence_id: str
    source_type: str
    text: str
    start: int
    end: int
    components: Mapping[str, Any]
    location: CitationLocation


@dataclass(frozen=True)
class DocumentIR:
    metadata: DocumentMetadata
    document_type: str
    mode: str | None
    source_format: str
    text: str
    blocks: tuple[DocumentBlock, ...]
    citations: tuple[CitationOccurrence, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_text(self) -> str:
        return self.text

    def blocks_of_kind(self, kind: str) -> list[DocumentBlock]:
        return [block for block in self.blocks if block.kind == kind]

    @cached_property
    def _block_segments(self) -> tuple[list[int], list[DocumentBlock | None]]:
        """Precompute smallest-containing-block per text segment for O(log n) lookup.

        block_at runs once per citation occurrence, so the naive full scan made
        citation location O(citations x blocks) on large documents.
        """
        located = [block for block in self.blocks if block.kind in LOCATION_KINDS]
        boundaries = sorted({b.absolute_start for b in located} | {b.absolute_end for b in located})
        starts: dict[int, list[int]] = {}
        ends: dict[int, list[int]] = {}
        for index, block in enumerate(located):
            starts.setdefault(block.absolute_start, []).append(index)
            ends.setdefault(block.absolute_end, []).append(index)
        active: set[int] = set()
        winners: list[DocumentBlock | None] = []
        for boundary in boundaries:
            active.difference_update(ends.get(boundary, ()))
            active.update(starts.get(boundary, ()))
            if active:
                winner = min(
                    (located[i] for i in active),
                    key=lambda item: (item.absolute_end - item.absolute_start, item.order),
                )
            else:
                winner = None
            winners.append(winner)
        return boundaries, winners

    def block_at(self, offset: int) -> DocumentBlock | None:
        boundaries, winners = self._block_segments
        index = bisect_right(boundaries, offset) - 1
        if index < 0:
            return None
        return winners[index]

    def with_citations(self, citations: Sequence[CitationOccurrence]) -> "DocumentIR":
        return replace(self, citations=tuple(citations))

    def summary(self) -> dict[str, Any]:
        return {
            "source_format": self.source_format,
            "document_type": self.document_type,
            "mode": self.mode,
            "block_count": len(self.blocks),
            "citation_count": len(self.citations),
            "footnote_count": len(self.blocks_of_kind("footnote")),
            "endnote_count": len(self.blocks_of_kind("endnote")),
            "page_count": len(self.blocks_of_kind("page")),
            "warnings": list(self.warnings),
        }


def _block(
    block_id: str,
    kind: str,
    text: str,
    start: int,
    order: int,
    local_start: int = 0,
    **kwargs: Any,
) -> DocumentBlock:
    return DocumentBlock(
        block_id=block_id,
        kind=kind,
        text=text,
        absolute_start=start,
        absolute_end=start + len(text),
        block_local_start=local_start,
        block_local_end=local_start + len(text),
        order=order,
        formatting_anchor=kwargs.pop("formatting_anchor", block_id),
        **kwargs,
    )


def _nested_spans(primary: Sequence[DocumentBlock], start_order: int) -> list[DocumentBlock]:
    nested: list[DocumentBlock] = []
    order = start_order
    for parent in primary:
        if parent.kind not in LOCATION_KINDS:
            continue
        sentence_index = 0
        boundaries = list(re.finditer(r"[^\n]+?(?:[!?](?=\s|$)|\.(?=\s|$)|$)", parent.text))
        for match in boundaries:
            value = match.group(0).strip()
            if not value:
                continue
            local_start = match.start() + len(match.group(0)) - len(match.group(0).lstrip())
            sentence = _block(
                f"{parent.block_id}:s:{sentence_index}",
                "sentence",
                value,
                parent.absolute_start + local_start,
                order,
                local_start=local_start,
                parent_id=parent.block_id,
            )
            nested.append(sentence)
            order += 1
            if _CITATION_HINT.search(value):
                nested.append(replace(sentence, block_id=f"{sentence.block_id}:citation", kind="citation_sentence", order=order))
                order += 1
                for clause_index, clause in enumerate(re.finditer(r"[^;]+", value)):
                    clause_text = clause.group(0).strip()
                    if not clause_text or not _CITATION_HINT.search(clause_text):
                        continue
                    clause_start = clause.start() + len(clause.group(0)) - len(clause.group(0).lstrip())
                    nested.append(
                        _block(
                            f"{sentence.block_id}:clause:{clause_index}",
                            "citation_clause",
                            clause_text,
                            sentence.absolute_start + clause_start,
                            order,
                            local_start=clause_start,
                            parent_id=sentence.block_id,
                        )
                    )
                    order += 1
            sentence_index += 1
        for quote_index, quote in enumerate(re.finditer(r'[“"]([^”"]+)[”"]', parent.text)):
            nested.append(
                _block(
                    f"{parent.block_id}:quote:{quote_index}",
                    "quotation",
                    quote.group(0),
                    parent.absolute_start + quote.start(),
                    order,
                    local_start=quote.start(),
                    parent_id=parent.block_id,
                )
            )
            order += 1
    return nested


def _metadata(filename: str, mime_type: str, **values: Any) -> DocumentMetadata:
    return DocumentMetadata(filename=Path(filename).name, mime_type=mime_type, **values)


def _ordered(blocks: Sequence[DocumentBlock]) -> tuple[DocumentBlock, ...]:
    ranked = sorted(
        blocks,
        key=lambda item: (
            item.absolute_start,
            0 if item.kind in LOCATION_KINDS or item.kind == "page" else 1,
            item.absolute_end,
            item.block_id,
        ),
    )
    return tuple(replace(block, order=index) for index, block in enumerate(ranked))


def parse_text_ir(
    text: str,
    *,
    filename: str = "document.txt",
    mime_type: str = "text/plain",
) -> DocumentIR:
    primary: list[DocumentBlock] = []
    note_definition_spans: list[tuple[int, int]] = []
    markdown_note_order = 0
    for index, match in enumerate(
        re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\s*\Z)", text, re.DOTALL)
    ):
        note = re.match(r"^\[(\d+)\]\s+", match.group(0))
        # Markdown-style footnote definitions ("[^1]: ...") reach this parser
        # whenever a caller hands plain text containing them (review_document
        # always calls parse_text_ir, never parse_markdown_ir). Without this
        # branch such a paragraph falls through to the generic "paragraph"
        # case below and never gets a note_number, which makes supra-note
        # resolution (which matches on location.note_number) structurally
        # unreachable for these documents.
        markdown_note = None if note else re.match(r"^\[\^([^\]]+)\]:\s*", match.group(0))
        if note:
            value = match.group(0)[note.end() :]
            primary.append(
                _block(
                    f"footnote:{note.group(1)}:p:0",
                    "footnote",
                    value,
                    match.start() + note.end(),
                    index,
                    note_id=note.group(1),
                    note_number=note.group(1),
                    metadata={"plain_text_identifier": note.group(1), "paragraph_order": 0},
                )
            )
            note_definition_spans.append(match.span())
        elif markdown_note:
            markdown_note_order += 1
            identifier = markdown_note.group(1)
            value = match.group(0)[markdown_note.end() :]
            primary.append(
                _block(
                    f"footnote:{identifier}:p:0",
                    "footnote",
                    value,
                    match.start() + markdown_note.end(),
                    index,
                    note_id=identifier,
                    note_number=str(markdown_note_order),
                    metadata={"markdown_identifier": identifier, "paragraph_order": 0},
                )
            )
            note_definition_spans.append(match.span())
        else:
            primary.append(_block(f"body:p:{index}", "paragraph", match.group(0), match.start(), index))
    references: list[DocumentBlock] = []
    next_order = len(primary)
    for ref_index, match in enumerate(re.finditer(r"\[(\d+)\]", text)):
        if any(start <= match.start() < end for start, end in note_definition_spans):
            continue
        references.append(
            _block(
                f"body:footnote-ref:{ref_index}",
                "footnote_reference",
                match.group(0),
                match.start(),
                next_order,
                note_id=match.group(1),
                note_number=match.group(1),
            )
        )
        next_order += 1
    # Markdown-style in-body reference markers ("[^1]", not the "[^1]:"
    # definition itself). citation_graph._logical_key uses these to order a
    # footnote's citations as if they appeared at the reference marker's
    # position in the body -- not at the footnote definition's position near
    # the end of the document -- which is what lets a "supra note N" mention
    # earlier in the body correctly see the footnote's citations as prior.
    for ref_index, match in enumerate(re.finditer(r"\[\^([^\]]+)\](?!:)", text)):
        if any(start <= match.start() < end for start, end in note_definition_spans):
            continue
        references.append(
            _block(
                f"body:footnote-ref-md:{ref_index}",
                "footnote_reference",
                match.group(0),
                match.start(),
                next_order,
                note_id=match.group(1),
                note_number=match.group(1),
                metadata={"markdown_identifier": match.group(1)},
            )
        )
        next_order += 1
    nested = _nested_spans(primary, next_order)
    return DocumentIR(
        metadata=_metadata(filename, mime_type),
        document_type="unknown",
        mode=None,
        source_format="text",
        text=text,
        blocks=_ordered(primary + references + nested),
    )


def parse_markdown_ir(
    text: str,
    *,
    filename: str = "document.md",
    mime_type: str = "text/markdown",
) -> DocumentIR:
    blocks: list[DocumentBlock] = []
    note_ranges: list[tuple[int, int]] = []
    order = 0
    note_pattern = re.compile(r"(?m)^\[\^([^\]]+)\]:\s*(.*(?:\n(?: {2,}|\t).*)*)$")
    for note_order, match in enumerate(note_pattern.finditer(text)):
        identifier = match.group(1)
        content = match.group(2).strip()
        content_start = match.start(2) + len(match.group(2)) - len(match.group(2).lstrip())
        blocks.append(
            _block(
                f"footnote:{identifier}:p:0",
                "footnote",
                content,
                content_start,
                order,
                note_id=identifier,
                note_number=str(note_order + 1),
                metadata={"markdown_identifier": identifier, "paragraph_order": 0},
            )
        )
        order += 1
        note_ranges.append(match.span())

    def in_note(position: int) -> bool:
        return any(start <= position < end for start, end in note_ranges)

    paragraph_index = 0
    for match in re.finditer(r"(?m)^(?!\s*$).+(?:\n(?!\s*$).+)*", text):
        if in_note(match.start()):
            continue
        raw = match.group(0)
        if raw.startswith("#"):
            marker = re.match(r"^#{1,6}\s+", raw)
            prefix = marker.end() if marker else 0
            blocks.append(_block(f"body:h:{paragraph_index}", "heading", raw[prefix:], match.start() + prefix, order))
        elif raw.startswith(">"):
            prefix = len(raw) - len(raw.lstrip("> "))
            blocks.append(_block(f"body:q:{paragraph_index}", "block_quotation", raw[prefix:], match.start() + prefix, order))
        else:
            blocks.append(_block(f"body:p:{paragraph_index}", "paragraph", raw, match.start(), order))
        paragraph_index += 1
        order += 1

    for index, match in enumerate(re.finditer(r"\[\^([^\]]+)\](?!:)", text)):
        blocks.append(
            _block(
                f"body:footnote-ref:{index}",
                "footnote_reference",
                match.group(0),
                match.start(),
                order,
                note_id=match.group(1),
                metadata={"markdown_identifier": match.group(1)},
            )
        )
        order += 1
    for index, match in enumerate(re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", text)):
        blocks.append(
            _block(
                f"body:link:{index}",
                "hyperlink",
                match.group(1),
                match.start(1),
                order,
                metadata={"url": match.group(2)},
            )
        )
        order += 1
    primary = [block for block in blocks if block.kind in LOCATION_KINDS]
    blocks.extend(_nested_spans(primary, order))
    return DocumentIR(
        metadata=_metadata(filename, mime_type),
        document_type="unknown",
        mode=None,
        source_format="markdown",
        text=text,
        blocks=_ordered(blocks),
    )


# The 15 MB upload cap bounds only the compressed archive; cap what any single
# XML part may decompress to so a crafted DOCX cannot balloon in memory.
MAX_DOCX_XML_BYTES = 50 * 1024 * 1024

# A 15 MB PDF can carry tens of thousands of distinct /Page objects that all
# share one tiny content stream, so the byte cap alone does not bound per-page
# work. Cap the page count so a crafted PDF cannot pin the process in the
# (formerly quadratic, now linear) page-extraction loop. This is far above any
# real filing; genuinely larger records should be split before review.
MAX_PDF_PAGES = 5000


def _read_docx_xml(archive: zipfile.ZipFile, path: str) -> ET.Element:
    info = archive.getinfo(path)
    if info.file_size > MAX_DOCX_XML_BYTES:
        raise ValueError(f"DOCX part {path} exceeds the decompressed size limit")
    data = archive.read(path)
    # Well-formed DOCX parts never carry a DTD; entity declarations are the
    # expansion ("billion laughs") vector for xml.etree's expat parser.
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError(f"DOCX part {path} contains a prohibited document type declaration")
    return ET.fromstring(data)


def _relationships(archive: zipfile.ZipFile, path: str) -> dict[str, str]:
    if path not in archive.namelist():
        return {}
    root = _read_docx_xml(archive, path)
    return {
        str(node.attrib.get("Id")): str(node.attrib.get("Target"))
        for node in root.findall(f"{{{PKG_REL_NS}}}Relationship")
    }


def _paragraph_content(node: ET.Element, note_numbers: Mapping[str, str]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    parts: list[str] = []
    markers: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    def walk(element: ET.Element, link_id: str | None = None) -> None:
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "hyperlink":
            link_id = element.attrib.get(f"{{{R_NS}}}id")
            link_start = sum(len(item) for item in parts)
            for child in element:
                walk(child, link_id)
            links.append({"start": link_start, "end": sum(len(item) for item in parts), "relationship_id": link_id})
            return
        if tag in {"t", "delText"} and element.text:
            parts.append(element.text)
        elif tag == "tab":
            parts.append("\t")
        elif tag in {"br", "cr"}:
            parts.append("\n")
        elif tag in {"footnoteReference", "endnoteReference"}:
            note_id = str(element.attrib.get(f"{{{W_NS}}}id", ""))
            number = note_numbers.get(note_id, note_id)
            marker_text = f"[{number}]"
            start = sum(len(item) for item in parts)
            parts.append(marker_text)
            markers.append({"kind": tag, "note_id": note_id, "number": number, "start": start, "end": start + len(marker_text)})
        for child in element:
            walk(child, link_id)

    walk(node)
    return "".join(parts), markers, links


def _core_metadata(archive: zipfile.ZipFile, filename: str) -> DocumentMetadata:
    if "docProps/core.xml" not in archive.namelist():
        return _metadata(filename, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    root = _read_docx_xml(archive, "docProps/core.xml")
    def value(namespace: str, name: str) -> str | None:
        return root.findtext(f"{{{namespace}}}{name}")
    return _metadata(
        filename,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        title=value(DC_NS, "title"),
        author=value(DC_NS, "creator"),
        subject=value(DC_NS, "subject"),
    )


def parse_docx_ir(payload: bytes, *, filename: str = "document.docx") -> DocumentIR:
    archive = zipfile.ZipFile(io.BytesIO(payload))
    if "word/document.xml" not in archive.namelist():
        raise ValueError("DOCX has no word/document.xml")
    note_specs: list[dict[str, Any]] = []
    for kind, path, element_name in (
        ("footnote", "word/footnotes.xml", "footnote"),
        ("endnote", "word/endnotes.xml", "endnote"),
    ):
        if path not in archive.namelist():
            continue
        root = _read_docx_xml(archive, path)
        visible = [
            node
            for node in root.findall(f"w:{element_name}", NS)
            if int(node.attrib.get(f"{{{W_NS}}}id", "-1")) > 0
        ]
        for note_order, node in enumerate(visible):
            note_id = str(node.attrib[f"{{{W_NS}}}id"])
            for paragraph_order, paragraph in enumerate(node.findall("w:p", NS)):
                value, _, links = _paragraph_content(paragraph, {})
                if value.strip():
                    note_specs.append(
                        {
                            "kind": kind,
                            "note_id": note_id,
                            "number": str(note_order + 1),
                            "paragraph_order": paragraph_order,
                            "text": value,
                            "links": links,
                        }
                    )
    footnote_numbers = {spec["note_id"]: spec["number"] for spec in note_specs if spec["kind"] == "footnote"}
    endnote_numbers = {spec["note_id"]: spec["number"] for spec in note_specs if spec["kind"] == "endnote"}
    relationships = _relationships(archive, "word/_rels/document.xml.rels")
    root = _read_docx_xml(archive, "word/document.xml")
    body = root.find("w:body", NS)
    specs: list[dict[str, Any]] = []
    if body is not None:
        paragraph_order = 0
        table_order = 0
        for child in body:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                numbers = footnote_numbers | endnote_numbers
                value, markers, links = _paragraph_content(child, numbers)
                if not value:
                    continue
                style = child.find("w:pPr/w:pStyle", NS)
                style_name = style.attrib.get(f"{{{W_NS}}}val", "") if style is not None else ""
                specs.append({"kind": "heading" if style_name.lower().startswith("heading") else "paragraph", "text": value, "id": f"body:p:{paragraph_order}", "markers": markers, "links": links, "style": style_name})
                paragraph_order += 1
            elif tag == "tbl":
                rows: list[str] = []
                for row in child.findall("w:tr", NS):
                    cells = []
                    for cell in row.findall("w:tc", NS):
                        cell_text = "\n".join(_paragraph_content(p, {})[0] for p in cell.findall("w:p", NS))
                        cells.append(cell_text)
                    rows.append("\t".join(cells))
                specs.append({"kind": "table", "text": "\n".join(rows), "id": f"body:table:{table_order}", "markers": [], "links": []})
                table_order += 1
    for spec in note_specs:
        spec["id"] = f"{spec['kind']}:{spec['note_id']}:p:{spec['paragraph_order']}"
        spec["markers"] = []
    all_specs = specs + note_specs
    text_parts: list[str] = []
    blocks: list[DocumentBlock] = []
    pending_markers: list[tuple[dict[str, Any], DocumentBlock]] = []
    order = 0
    for spec in all_specs:
        if text_parts:
            text_parts.append("\n\n")
        start = sum(len(item) for item in text_parts)
        text_parts.append(spec["text"])
        note_id = spec.get("note_id")
        note_number = spec.get("number")
        block = _block(
            spec["id"],
            spec["kind"],
            spec["text"],
            start,
            order,
            note_id=note_id,
            note_number=note_number,
            metadata={
                "paragraph_order": spec.get("paragraph_order"),
                "style": spec.get("style", ""),
            },
        )
        blocks.append(block)
        order += 1
        for marker in spec.get("markers", []):
            pending_markers.append((marker, block))
        for link_index, link in enumerate(spec.get("links", [])):
            blocks.append(
                _block(
                    f"{block.block_id}:link:{link_index}",
                    "hyperlink",
                    block.text[link["start"] : link["end"]],
                    block.absolute_start + link["start"],
                    order,
                    local_start=link["start"],
                    parent_id=block.block_id,
                    metadata={"url": relationships.get(link.get("relationship_id"), "")},
                )
            )
            order += 1
    note_targets = {block.note_id: block.block_id for block in blocks if block.kind in {"footnote", "endnote"}}
    for index, (marker, parent) in enumerate(pending_markers):
        note_kind = "footnote" if marker["kind"] == "footnoteReference" else "endnote"
        blocks.append(
            _block(
                f"{parent.block_id}:{note_kind}-ref:{index}",
                f"{note_kind}_reference",
                parent.text[marker["start"] : marker["end"]],
                parent.absolute_start + marker["start"],
                order,
                local_start=marker["start"],
                parent_id=parent.block_id,
                note_id=marker["note_id"],
                note_number=marker["number"],
                metadata={"target_block_id": note_targets.get(marker["note_id"])},
            )
        )
        order += 1
    primary = [block for block in blocks if block.kind in LOCATION_KINDS]
    blocks.extend(_nested_spans(primary, order))
    return DocumentIR(
        metadata=_core_metadata(archive, filename),
        document_type="unknown",
        mode=None,
        source_format="docx",
        text="".join(text_parts),
        blocks=_ordered(blocks),
        warnings=(),
    )


def parse_pdf_ir(payload: bytes, *, filename: str = "document.pdf") -> DocumentIR:
    from .documents import DocumentLoadError, MIN_PDF_TEXT_CHARS

    try:
        reader = PdfReader(io.BytesIO(payload))
    except Exception as exc:
        raise DocumentLoadError("ocr_required", "The PDF could not be parsed as a text PDF. OCR or a searchable PDF is required.") from exc
    try:
        page_count = len(reader.pages)
    except Exception as exc:
        raise DocumentLoadError("ocr_required", "The PDF page structure could not be read.") from exc
    if page_count > MAX_PDF_PAGES:
        raise DocumentLoadError(
            "document_too_large",
            f"The PDF has {page_count} pages; AutoCite reviews at most {MAX_PDF_PAGES} pages at once.",
        )
    blocks: list[DocumentBlock] = []
    text_parts: list[str] = []
    order = 0
    running_offset = 0
    uncertain = False
    for page_number, page in enumerate(reader.pages, 1):
        fragments: list[dict[str, Any]] = []

        def visitor(value: str, cm: Any, tm: Any, font: Any, font_size: Any) -> None:
            if not value:
                return
            matrix = tm if isinstance(tm, (list, tuple)) and len(tm) >= 6 else cm
            x = float(matrix[4]) if isinstance(matrix, (list, tuple)) and len(matrix) >= 6 else 0.0
            y = float(matrix[5]) if isinstance(matrix, (list, tuple)) and len(matrix) >= 6 else 0.0
            fragments.append({"text": value, "x": x, "y": y, "font_size": float(font_size or 0)})

        try:
            fallback = page.extract_text(visitor_text=visitor) or ""
        except TypeError:
            fallback = page.extract_text() or ""
        if not fragments and fallback:
            fragments = [{"text": fallback, "x": 0.0, "y": 0.0, "font_size": 0.0}]
        if text_parts:
            text_parts.append("\n\n")
            running_offset += 2
        page_start = running_offset
        page_values: list[str] = []
        page_chars = 0
        sizes = [item["font_size"] for item in fragments if item["font_size"] > 0]
        median_size = statistics.median(sizes) if sizes else 0
        height = float(getattr(getattr(page, "media_box", None), "height", 0) or 0)
        for fragment_index, fragment in enumerate(fragments):
            value = fragment["text"]
            if not value:
                continue
            fragment_start = page_start + page_chars
            page_values.append(value)
            page_chars += len(value)
            low_on_page = bool(height and fragment["y"] < height * 0.15)
            small_font = bool(median_size and fragment["font_size"] and fragment["font_size"] < median_size * 0.85)
            likely_note = low_on_page
            confidence = "medium" if low_on_page and small_font else "low" if likely_note else "certain"
            uncertain = uncertain or likely_note
            blocks.append(
                _block(
                    f"page:{page_number}:fragment:{fragment_index}",
                    "paragraph",
                    value,
                    fragment_start,
                    order,
                    page_number=page_number,
                    reconstruction_confidence=confidence,
                    coordinates=((fragment["x"], fragment["y"], fragment["font_size"]),),
                    metadata={"likely_footnote": likely_note},
                )
            )
            order += 1
        page_text = "".join(page_values) or fallback
        text_parts.extend(page_values or [fallback])
        running_offset += page_chars if page_values else len(fallback)
        coordinates = tuple((item["x"], item["y"], item["font_size"]) for item in fragments)
        blocks.append(
            _block(
                f"page:{page_number}",
                "page",
                page_text,
                page_start,
                order,
                page_number=page_number,
                coordinates=coordinates,
                metadata={"fragment_count": len(fragments)},
            )
        )
        order += 1
    text = "".join(text_parts)
    if len(text.strip()) < MIN_PDF_TEXT_CHARS:
        raise DocumentLoadError("ocr_required", "The PDF contains too little extractable text and appears scanned or image-only.")
    primary = [block for block in blocks if block.kind in LOCATION_KINDS]
    blocks.extend(_nested_spans(primary, order))
    warnings = (
        "PDF footnote reconstruction is uncertain because the format does not expose reliable note relationships.",
    ) if uncertain else ()
    return DocumentIR(
        metadata=_metadata(filename, "application/pdf"),
        document_type="unknown",
        mode=None,
        source_format="pdf",
        text=text,
        blocks=_ordered(blocks),
        warnings=warnings,
    )


def locate_citations(ir: DocumentIR, engine: Any) -> tuple[CitationOccurrence, ...]:
    occurrences: list[CitationOccurrence] = []
    for index, citation in enumerate(engine.extract(ir.text)):
        # eyecite's case-name backward scan can absorb a block separator's
        # leading whitespace/newlines into citation.start (e.g. a citation
        # opening a new paragraph or footnote right after a blank-line
        # boundary), landing citation.start in the inter-block gap rather
        # than the block the citation is actually in. block_at looks up the
        # block containing an exact offset, so it returns None (or the wrong,
        # preceding block) for a position in that gap; searching forward past
        # any leading whitespace finds the block the citation's real content
        # is in without changing the citation's own reported start/end/text.
        block_lookup_start = citation.start
        while block_lookup_start < citation.end and ir.text[block_lookup_start].isspace():
            block_lookup_start += 1
        block = ir.block_at(block_lookup_start)
        contained = bool(block and citation.end <= block.absolute_end)
        location = CitationLocation(
            block_id=block.block_id if contained and block else None,
            block_kind=block.kind if contained and block else None,
            absolute_start=citation.start,
            absolute_end=citation.end,
            block_local_start=max(0, citation.start - block.absolute_start) if contained and block else None,
            block_local_end=citation.end - block.absolute_start if contained and block else None,
            note_id=block.note_id if contained and block else None,
            note_number=block.note_number if contained and block else None,
            page_number=block.page_number if contained and block else None,
            reconstruction_confidence=block.reconstruction_confidence if contained and block else "low",
            provenance="parsed_document_structure" if contained else "unresolved_ambiguity",
        )
        occurrences.append(
            CitationOccurrence(
                occurrence_id=f"cite:{index:04d}",
                source_type=citation.source_type,
                text=citation.text,
                start=citation.start,
                end=citation.end,
                components=dict(citation.components),
                location=location,
            )
        )
    return tuple(occurrences)


def classify_document_mode(
    ir: DocumentIR,
    *,
    explicit_mode: str = "auto",
    document_type: str = "auto",
) -> dict[str, Any]:
    explicit = explicit_mode.strip().lower()
    if explicit not in {"auto", "bluepages", "whitepages"}:
        raise ValueError("explicit_mode must be auto, bluepages, or whitepages")
    normalized_type = document_type.strip().lower().replace("-", "_").replace(" ", "_")
    blue_types = {"brief", "motion", "pleading", "court_filing", "legal_memorandum", "memorandum", "practitioner"}
    white_types = {"law_review", "law_review_article", "journal_article", "seminar_paper", "academic", "student_note"}
    blue_evidence: list[str] = []
    white_evidence: list[str] = []
    if normalized_type in blue_types:
        blue_evidence.append(f"document_type:{normalized_type}")
    elif normalized_type in white_types:
        white_evidence.append(f"document_type:{normalized_type}")
    elif normalized_type != "auto":
        raise ValueError("document_type must be auto or a recognized court/practitioner/academic type")
    searchable = " ".join(filter(None, [ir.metadata.title, ir.metadata.subject, ir.text[:4000]]))
    if re.search(r"\b(?:district|supreme|superior|bankruptcy) court\b|\bplaintiff\b|\bdefendant\b|\bmotion\b", searchable, re.I):
        blue_evidence.append("court_filing_language")
    if re.search(r"\blaw review\b|\bseminar paper\b|\bthis (?:article|note)\b|\bscholarly\b", searchable, re.I):
        white_evidence.append("academic_language")
    note_count = len(ir.blocks_of_kind("footnote")) + len(ir.blocks_of_kind("endnote"))
    if note_count:
        white_evidence.append(f"numbered_notes:{note_count}")
    inline_citations = len(_CITATION_HINT.findall(ir.text))
    if inline_citations >= 2 and not note_count:
        blue_evidence.append(f"inline_citations:{inline_citations}")
    if ir.metadata.title and re.search(r"brief|motion|memorandum", ir.metadata.title, re.I):
        blue_evidence.append("document_metadata_title")
    if ir.metadata.title and re.search(r"article|review|paper|note", ir.metadata.title, re.I):
        white_evidence.append("document_metadata_title")
    def _score(evidence: list[str]) -> int:
        # An explicit document_type is a direct user assertion, so it outweighs
        # any single textual signal inferred from document content.
        return sum(2 if item.startswith("document_type:") else 1 for item in evidence)

    blue_score = _score(blue_evidence)
    white_score = _score(white_evidence)
    auto_mode = "whitepages" if white_score > blue_score else "bluepages"
    auto_evidence = white_evidence if auto_mode == "whitepages" else blue_evidence
    conflicts = blue_evidence if auto_mode == "whitepages" else white_evidence
    if explicit != "auto":
        selected = explicit
        evidence = [f"explicit_mode:{explicit}"]
        conflicts = white_evidence if explicit == "bluepages" else blue_evidence
        confidence = "high"
        confirmation = False
    else:
        selected = auto_mode
        evidence = auto_evidence
        margin = abs(blue_score - white_score)
        auto_score = white_score if auto_mode == "whitepages" else blue_score
        confidence = "high" if margin >= 2 and auto_score >= 2 else "medium" if margin >= 1 else "low"
        confirmation = confidence == "low" or bool(conflicts and margin <= 1)
    return {
        "selected_mode": selected,
        "mode": selected,
        "confidence": confidence,
        "evidence": evidence,
        "signals": evidence,
        "conflicting_evidence": conflicts,
        "user_confirmation_recommended": confirmation,
        "reason": evidence[0] if evidence else "default_bluepages_due_to_insufficient_evidence",
        "provenance": "deterministic_logic",
    }
