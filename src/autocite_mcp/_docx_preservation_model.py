from __future__ import annotations

import zipfile
from dataclasses import asdict, dataclass
from typing import Any

from lxml import etree

from .review_session import PlannedAnnotation


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_NS = "http://www.w3.org/XML/1998/namespace"
COMMENTS_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
)
COMMENTS_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
)
MAX_DOCX_BYTES = 15 * 1024 * 1024
MAX_DOCX_XML_BYTES = 50 * 1024 * 1024
MAX_DOCX_TOTAL_UNCOMPRESSED_BYTES = 250 * 1024 * 1024

NS = {"w": W_NS, "r": R_NS}
W = f"{{{W_NS}}}"
REL = f"{{{PKG_REL_NS}}}"
CT = f"{{{CT_NS}}}"


class DocxPreservationError(ValueError):
    pass


class DocxMappingError(DocxPreservationError):
    pass


class DocxValidationError(DocxPreservationError):
    pass


@dataclass(frozen=True, slots=True)
class DocxTextLocation:
    part_name: str
    start: int
    end: int
    text: str
    node_kind: str
    node_path: str | None
    editable: bool
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DocxTextIndex:
    text: str
    locations: tuple[DocxTextLocation, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "locations": [location.as_dict() for location in self.locations],
        }


@dataclass(frozen=True, slots=True)
class DocxValidationReport:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    part_count: int
    total_uncompressed_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PreservedDocxResult:
    payload: bytes
    applied_edit_ids: tuple[str, ...]
    anchored_annotation_ids: tuple[str, ...]
    unanchored_annotations: tuple[PlannedAnnotation, ...]
    modified_parts: tuple[str, ...]
    validation: DocxValidationReport
    preservation_mode: str = "original_docx"

    def as_dict(self) -> dict[str, Any]:
        return {
            "preservation_mode": self.preservation_mode,
            "applied_edit_ids": list(self.applied_edit_ids),
            "anchored_annotation_ids": list(self.anchored_annotation_ids),
            "unanchored_annotations": [
                annotation.as_dict() for annotation in self.unanchored_annotations
            ],
            "modified_parts": list(self.modified_parts),
            "validation": self.validation.as_dict(),
            "size_bytes": len(self.payload),
        }


@dataclass(slots=True)
class _Package:
    infos: dict[str, zipfile.ZipInfo]
    parts: dict[str, bytes]
    order: tuple[str, ...]


@dataclass(slots=True)
class _InternalLocation:
    public: DocxTextLocation
    node: etree._Element | None
    root: etree._Element | None


@dataclass(slots=True)
class _IndexedPackage:
    package: _Package
    roots: dict[str, etree._Element]
    text: str
    locations: list[_InternalLocation]


@dataclass(slots=True)
class _Segment:
    text: str
    node: etree._Element | None
    root: etree._Element
    part_name: str
    kind: str
    editable: bool
    reason: str | None


def _local_name(node: etree._Element) -> str:
    return etree.QName(node).localname


def _secure_parser() -> etree.XMLParser:
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        recover=False,
        remove_blank_text=False,
    )


def _parse_xml(data: bytes, part_name: str) -> etree._Element:
    if len(data) > MAX_DOCX_XML_BYTES:
        raise DocxValidationError(
            f"DOCX part {part_name} exceeds the decompressed XML size limit"
        )
    upper = data.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise DocxValidationError(
            f"DOCX part {part_name} contains a prohibited document type declaration"
        )
    try:
        return etree.fromstring(data, parser=_secure_parser())
    except etree.XMLSyntaxError as exc:
        raise DocxValidationError(f"DOCX part {part_name} is not valid XML") from exc
