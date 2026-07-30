from __future__ import annotations

import copy
import io
import posixpath
import stat
import zipfile
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import unquote

from lxml import etree

from ._docx_preservation_model import (
    CT_NS,
    MAX_DOCX_BYTES,
    MAX_DOCX_TOTAL_UNCOMPRESSED_BYTES,
    NS,
    REL,
    W,
    DocxValidationError,
    DocxValidationReport,
    _IndexedPackage,
    _Package,
    _parse_xml,
)


def _safe_member_name(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/"):
        return False
    path = PurePosixPath(name)
    return not any(part in {"", ".", ".."} for part in path.parts)


def _read_package(payload: bytes) -> _Package:
    if not payload:
        raise DocxValidationError("DOCX payload is empty")
    if len(payload) > MAX_DOCX_BYTES:
        raise DocxValidationError("DOCX exceeds the 15 MB compressed size limit")
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise DocxValidationError("DOCX is not a valid ZIP package") from exc
    infos: dict[str, zipfile.ZipInfo] = {}
    parts: dict[str, bytes] = {}
    order: list[str] = []
    total = 0
    for info in archive.infolist():
        name = info.filename
        if name.endswith("/"):
            continue
        if name in infos:
            raise DocxValidationError(f"DOCX contains a duplicate package part: {name}")
        if not _safe_member_name(name):
            raise DocxValidationError(f"DOCX contains an unsafe package path: {name}")
        mode = (info.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise DocxValidationError(f"DOCX contains a symbolic-link entry: {name}")
        if info.flag_bits & 0x1:
            raise DocxValidationError(f"DOCX contains an encrypted package part: {name}")
        total += info.file_size
        if total > MAX_DOCX_TOTAL_UNCOMPRESSED_BYTES:
            raise DocxValidationError("DOCX exceeds the total decompressed size limit")
        try:
            data = archive.read(info)
        except (RuntimeError, zipfile.BadZipFile) as exc:
            raise DocxValidationError(f"DOCX part could not be read: {name}") from exc
        infos[name] = copy.copy(info)
        parts[name] = data
        order.append(name)
    archive.close()
    return _Package(infos=infos, parts=parts, order=tuple(order))


def _serialize_root(root: etree._Element) -> bytes:
    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=None,
    )


def _relationship_source(rels_name: str) -> tuple[str | None, str]:
    if rels_name == "_rels/.rels":
        return None, ""
    marker = "/_rels/"
    if marker not in rels_name or not rels_name.endswith(".rels"):
        return None, ""
    directory, filename = rels_name.split(marker, 1)
    source_filename = filename[: -len(".rels")]
    source = f"{directory}/{source_filename}" if directory else source_filename
    return source, posixpath.dirname(source)


def _normalise_relationship_target(base_dir: str, target: str) -> str | None:
    decoded = unquote(target).replace("\\", "/")
    if not decoded or decoded.startswith("#"):
        return None
    if decoded.startswith("/"):
        candidate = posixpath.normpath(decoded.lstrip("/"))
    else:
        candidate = posixpath.normpath(posixpath.join(base_dir, decoded))
    if candidate == ".." or candidate.startswith("../") or candidate.startswith("/"):
        return None
    return candidate


def _validate_parts(package: _Package, *, raise_on_error: bool) -> DocxValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    required = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
    for name in sorted(required - package.parts.keys()):
        errors.append(f"missing required package part: {name}")

    roots: dict[str, etree._Element] = {}
    for name, data in package.parts.items():
        if name.endswith(".xml") or name.endswith(".rels"):
            try:
                roots[name] = _parse_xml(data, name)
            except DocxValidationError as exc:
                errors.append(str(exc))

    if "[Content_Types].xml" in roots:
        if etree.QName(roots["[Content_Types].xml"]).namespace != CT_NS:
            errors.append("[Content_Types].xml has an unexpected root namespace")

    for rels_name, root in roots.items():
        if not rels_name.endswith(".rels"):
            continue
        _, base_dir = _relationship_source(rels_name)
        for relationship in root.findall(f"{REL}Relationship"):
            if relationship.attrib.get("TargetMode") == "External":
                continue
            target = relationship.attrib.get("Target", "")
            normalized = _normalise_relationship_target(base_dir, target)
            if normalized is None or normalized not in package.parts:
                errors.append(
                    f"missing relationship target from {rels_name}: {target or '<empty>'}"
                )

    comments_root = roots.get("word/comments.xml")
    if comments_root is not None:
        ids: list[str] = [
            str(node.attrib.get(f"{W}id", ""))
            for node in comments_root.findall("w:comment", NS)
        ]
        if len(ids) != len(set(ids)):
            errors.append("word/comments.xml contains duplicate comment IDs")

    report = DocxValidationReport(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        part_count=len(package.parts),
        total_uncompressed_bytes=sum(len(data) for data in package.parts.values()),
    )
    if raise_on_error and errors:
        raise DocxValidationError("; ".join(errors))
    return report


def validate_docx_package(
    payload: bytes, *, raise_on_error: bool = False
) -> DocxValidationReport:
    try:
        package = _read_package(payload)
    except DocxValidationError as exc:
        if raise_on_error:
            raise
        return DocxValidationReport(False, (str(exc),), (), 0, 0)
    return _validate_parts(package, raise_on_error=raise_on_error)


def _write_package(indexed: _IndexedPackage, modified_parts: set[str]) -> bytes:
    parts = dict(indexed.package.parts)
    for name in modified_parts:
        root = indexed.roots.get(name)
        if root is None:
            raise DocxValidationError(f"modified XML part has no parsed root: {name}")
        parts[name] = _serialize_root(root)

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        written: set[str] = set()
        for name in indexed.package.order:
            info = copy.copy(indexed.package.infos[name])
            archive.writestr(info, parts[name])
            written.add(name)
        for name in sorted(parts.keys() - written):
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.date_time = datetime.now().timetuple()[:6]
            archive.writestr(info, parts[name])
    return output.getvalue()
