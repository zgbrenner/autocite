from __future__ import annotations

import io
import mimetypes
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pypdf import PdfReader

MAX_DOCUMENT_BYTES = 15 * 1024 * 1024
MIN_PDF_TEXT_CHARS = 20


class DocumentLoadError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DocumentInput:
    text: str
    filename: str
    mime_type: str
    source_format: str
    warnings: tuple[str, ...] = ()


def _normalized_mime(filename: str, mime_type: str | None) -> str:
    if mime_type:
        return mime_type.split(";", 1)[0].strip().lower()
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _docx_text(payload: bytes) -> str:
    document = Document(io.BytesIO(payload))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text:
            parts.append(paragraph.text)
    for table in document.tables:
        for row in table.rows:
            parts.append("\t".join(cell.text for cell in row.cells))
    return "\n".join(parts).strip()


def _pdf_text(payload: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(payload))
        parts = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:
        raise DocumentLoadError(
            "ocr_required",
            "The PDF could not be parsed as a text PDF. OCR or a searchable PDF is required.",
        ) from exc
    text = "\n\n".join(part for part in parts if part).strip()
    if len(text) < MIN_PDF_TEXT_CHARS:
        raise DocumentLoadError(
            "ocr_required",
            "The PDF contains too little extractable text and appears scanned or image-only.",
        )
    return text


def load_document_bytes(data: bytes, filename: str, mime_type: str | None = None) -> DocumentInput:
    """Load a supported document without persisting it."""
    if not data:
        raise DocumentLoadError("empty_document", "The uploaded document is empty.")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise DocumentLoadError(
            "document_too_large",
            f"Documents are limited to {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB.",
        )
    safe_name = Path(filename or "document.txt").name
    mime = _normalized_mime(safe_name, mime_type)
    suffix = Path(safe_name).suffix.lower()

    if mime in {"text/plain", "text/markdown"} or suffix in {".txt", ".md", ".markdown"}:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentLoadError("invalid_text_encoding", "Text documents must use UTF-8.") from exc
        source_format = "markdown" if suffix in {".md", ".markdown"} or mime == "text/markdown" else "text"
    elif (
        mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or suffix == ".docx"
    ):
        try:
            text = _docx_text(data)
        except Exception as exc:
            raise DocumentLoadError("invalid_docx", "The DOCX file could not be read.") from exc
        source_format = "docx"
    elif mime == "application/pdf" or suffix == ".pdf":
        text = _pdf_text(data)
        source_format = "pdf"
    else:
        raise DocumentLoadError(
            "unsupported_document_type",
            "Supported files are TXT, Markdown, DOCX, and text-based PDF.",
        )

    if not text.strip():
        raise DocumentLoadError("empty_document", "The document contains no readable text.")
    return DocumentInput(
        text=text,
        filename=safe_name,
        mime_type=mime,
        source_format=source_format,
        warnings=(
            "Input formatting is normalized to text for citation analysis; layout may not be preserved in exports.",
        ),
    )


def _text_node(tag: str, value: str) -> OxmlElement:
    node = OxmlElement(tag)
    if value[:1].isspace() or value[-1:].isspace():
        node.set(qn("xml:space"), "preserve")
    node.text = value
    return node


def _revision(parent: OxmlElement, tag: str, value: str, revision_id: int) -> None:
    if not value:
        return
    change = OxmlElement(tag)
    change.set(qn("w:id"), str(revision_id))
    change.set(qn("w:author"), "AutoCite")
    change.set(qn("w:date"), datetime.now(timezone.utc).isoformat())
    run = OxmlElement("w:r")
    run.append(_text_node("w:delText" if tag == "w:del" else "w:t", value))
    change.append(run)
    parent.append(change)


def build_review_docx(original_text: str, corrected_text: str, *, tracked: bool = True) -> bytes:
    """Build a simple review DOCX; tracked mode emits Word insertion/deletion markup."""
    document = Document()
    paragraph = document.add_paragraph()
    if not tracked:
        paragraph.add_run(corrected_text)
    else:
        matcher = SequenceMatcher(None, original_text, corrected_text)
        revision_id = 1
        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            if opcode == "equal":
                paragraph.add_run(original_text[i1:i2])
            elif opcode == "delete":
                _revision(paragraph._p, "w:del", original_text[i1:i2], revision_id)
                revision_id += 1
            elif opcode == "insert":
                _revision(paragraph._p, "w:ins", corrected_text[j1:j2], revision_id)
                revision_id += 1
            elif opcode == "replace":
                _revision(paragraph._p, "w:del", original_text[i1:i2], revision_id)
                revision_id += 1
                _revision(paragraph._p, "w:ins", corrected_text[j1:j2], revision_id)
                revision_id += 1
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()
