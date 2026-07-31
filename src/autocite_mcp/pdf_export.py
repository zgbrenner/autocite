from __future__ import annotations

import textwrap
from collections.abc import Iterable

_PAGE_WIDTH = 612
_PAGE_HEIGHT = 792
_MARGIN_X = 54
_MARGIN_TOP = 54
_MARGIN_BOTTOM = 54
_FONT_SIZE = 11
_LEADING = 15
_MAX_LINE_CHARS = 88


def _display_lines(text: str) -> Iterable[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    for source_line in normalized.split("\n"):
        if not source_line:
            yield ""
            continue
        expanded = source_line.expandtabs(4)
        wrapped = textwrap.wrap(
            expanded,
            width=_MAX_LINE_CHARS,
            break_long_words=True,
            break_on_hyphens=False,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        yield from wrapped or [""]


def _encode_pdf_text(value: str) -> bytes:
    return value.encode("cp1252", errors="replace").hex().upper().encode("ascii")


def _content_stream(lines: list[str], *, title: str, page: int, pages: int) -> bytes:
    commands = [
        b"BT",
        f"/F1 {_FONT_SIZE} Tf".encode("ascii"),
        f"{_MARGIN_X} {_PAGE_HEIGHT - _MARGIN_TOP} Td".encode("ascii"),
        f"{_LEADING} TL".encode("ascii"),
    ]
    if page == 1 and title.strip():
        commands.extend(
            [
                b"/F1 14 Tf",
                b"<" + _encode_pdf_text(title.strip()) + b"> Tj",
                b"T*",
                b"T*",
                f"/F1 {_FONT_SIZE} Tf".encode("ascii"),
            ]
        )
    for line in lines:
        if line:
            commands.append(b"<" + _encode_pdf_text(line) + b"> Tj")
        commands.append(b"T*")
    commands.extend(
        [
            b"ET",
            b"BT",
            b"/F1 8 Tf",
            f"{_PAGE_WIDTH - 108} 28 Td".encode("ascii"),
            b"<" + _encode_pdf_text(f"Page {page} of {pages}") + b"> Tj",
            b"ET",
        ]
    )
    return b"\n".join(commands) + b"\n"


def _pdf_object(number: int, body: bytes) -> bytes:
    return f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"


def build_text_pdf(text: str, *, title: str = "AutoCite reviewed document") -> bytes:
    """Build a small searchable Letter-size PDF without a runtime dependency.

    This export intentionally favors reliable text and pagination over layout
    reconstruction. DOCX remains the format for preserving editable Word markup.
    """

    max_lines = max(
        1,
        int((_PAGE_HEIGHT - _MARGIN_TOP - _MARGIN_BOTTOM) / _LEADING) - 4,
    )
    all_lines = list(_display_lines(text)) or [""]
    chunks = [
        all_lines[index : index + max_lines]
        for index in range(0, len(all_lines), max_lines)
    ] or [[""]]

    font_object = 3
    page_object_numbers: list[int] = []
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    }
    next_object = 4
    for page_number, lines in enumerate(chunks, start=1):
        page_object = next_object
        content_object = next_object + 1
        next_object += 2
        page_object_numbers.append(page_object)
        stream = _content_stream(
            lines,
            title=title,
            page=page_number,
            pages=len(chunks),
        )
        objects[page_object] = (
            b"<< /Type /Page /Parent 2 0 R "
            + f"/MediaBox [0 0 {_PAGE_WIDTH} {_PAGE_HEIGHT}] ".encode("ascii")
            + f"/Resources << /Font << /F1 {font_object} 0 R >> >> ".encode("ascii")
            + f"/Contents {content_object} 0 R >>".encode("ascii")
        )
        objects[content_object] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )

    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects[2] = (
        f"<< /Type /Pages /Count {len(page_object_numbers)} /Kids [{kids}] >>".encode(
            "ascii"
        )
    )

    output = bytearray(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = [0] * (max(objects) + 1)
    for number in sorted(objects):
        offsets[number] = len(output)
        output.extend(_pdf_object(number, objects[number]))
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for number in range(1, len(offsets)):
        output.extend(f"{offsets[number]:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)
