from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


class ManifestError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ManifestDocument:
    document_id: str
    path: Path
    relative_path: str
    split: str
    permission_basis: str
    permission_reviewer: str | None
    mode: str
    document_type: str
    jurisdiction: str | None
    expected: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RealDocumentScore:
    document_id: str
    split: str
    citation_precision: float
    citation_recall: float
    issue_precision: float
    issue_recall: float
    expected_citations: int
    detected_citations: int
    expected_issue_codes: int
    detected_issue_codes: int
    unsafe_automatic_edits: int
    safe_fixed_text_match: bool | None
    unresolved_antecedent_guesses: int
    local_mode_network_calls: int
    source_overwritten: bool
    export_valid: bool
    release_gate_passed: bool
    runtime_seconds: float | None = None
    peak_memory_bytes: int | None = None
    error_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _manifest_view(entry: ManifestDocument | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(entry, ManifestDocument):
        return {
            "document_id": entry.document_id,
            "split": entry.split,
            "expected": entry.expected,
        }
    return entry


def _safe_child(root: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ManifestError("document path must be relative to the document root")
    resolved_root = root.resolve(strict=True)
    resolved = (resolved_root / candidate).resolve(strict=False)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ManifestError("document path escapes the configured document root") from exc
    return resolved


def load_real_document_manifest(
    manifest_path: Path, documents_root: Path
) -> tuple[ManifestDocument, ...]:
    manifest_path = Path(manifest_path)
    documents_root = Path(documents_root)
    if not manifest_path.is_file():
        raise ManifestError(f"manifest file not found: {manifest_path.name}")
    if not documents_root.is_dir():
        raise ManifestError("document root is not an accessible directory")

    documents: list[ManifestDocument] = []
    seen_ids: set[str] = set()
    for line_number, raw_line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ManifestError(
                f"manifest line {line_number} is not valid JSON"
            ) from exc
        if not isinstance(row, dict):
            raise ManifestError(f"manifest line {line_number} must be a JSON object")

        document_id = str(row.get("document_id") or "").strip()
        if not document_id:
            raise ManifestError(f"manifest line {line_number} has no document_id")
        if document_id in seen_ids:
            raise ManifestError(f"duplicate document_id: {document_id}")
        seen_ids.add(document_id)

        relative_path = str(row.get("relative_path") or "").strip()
        if not relative_path:
            raise ManifestError(f"document {document_id} has no relative_path")
        path = _safe_child(documents_root, relative_path)
        if not path.is_file():
            raise ManifestError(f"document file not found for {document_id}: {relative_path}")

        permission = _mapping(row.get("permission"))
        permission_basis = str(permission.get("basis") or "").strip()
        if not permission_basis:
            raise ManifestError(f"document {document_id} has no permission basis")
        reviewer_value = permission.get("reviewed_by")
        permission_reviewer = (
            str(reviewer_value).strip() if reviewer_value is not None else None
        )

        split = str(row.get("split") or "test").strip().casefold()
        if split not in {"train", "dev", "test", "holdout"}:
            raise ManifestError(f"document {document_id} has an invalid split: {split}")
        expected = _mapping(row.get("expected"))
        if not expected:
            raise ManifestError(f"document {document_id} has no expected gold data")

        jurisdiction_value = row.get("jurisdiction")
        documents.append(
            ManifestDocument(
                document_id=document_id,
                path=path,
                relative_path=relative_path.replace("\\", "/"),
                split=split,
                permission_basis=permission_basis,
                permission_reviewer=permission_reviewer,
                mode=str(row.get("mode") or "auto"),
                document_type=str(row.get("document_type") or "auto"),
                jurisdiction=(
                    str(jurisdiction_value) if jurisdiction_value is not None else None
                ),
                expected=expected,
            )
        )
    if not documents:
        raise ManifestError("manifest contains no document rows")
    return tuple(documents)


def _citation_key(item: Mapping[str, Any]) -> tuple[str, int, int, str]:
    start = item.get("start")
    end = item.get("end")
    return (
        str(item.get("text") or ""),
        start if isinstance(start, int) else -1,
        end if isinstance(end, int) else -1,
        str(item.get("source_type") or ""),
    )


def _issue_codes(result: Mapping[str, Any]) -> set[str]:
    codes: set[str] = set()
    for collection in ("remaining_issues", "rule_findings"):
        for raw in _sequence(result.get(collection)):
            if not isinstance(raw, Mapping):
                continue
            code = str(raw.get("issue_code") or raw.get("code") or "").strip()
            if code:
                codes.add(code)
    return codes


def _precision_recall(
    expected: set[Any], actual: set[Any]
) -> tuple[float, float]:
    if not expected and not actual:
        return 1.0, 1.0
    true_positive = len(expected & actual)
    precision = true_positive / len(actual) if actual else 0.0
    recall = true_positive / len(expected) if expected else 1.0
    return precision, recall


def _unsafe_edits(result: Mapping[str, Any]) -> int:
    count = 0
    for raw in _sequence(result.get("applied_edits")):
        if not isinstance(raw, Mapping):
            count += 1
            continue
        safe = (
            str(raw.get("correction_level") or "") == "safe_auto_fix"
            and str(raw.get("confidence") or "") == "high"
            and raw.get("suggestion") is not None
        )
        if not safe:
            count += 1
    return count


def _unresolved_guesses(result: Mapping[str, Any]) -> int:
    graph = _mapping(result.get("citation_graph"))
    count = 0
    for raw in _sequence(graph.get("resolutions")):
        if not isinstance(raw, Mapping):
            continue
        guessed = bool(raw.get("guessed")) or str(
            raw.get("resolution_status") or ""
        ).casefold() == "guessed"
        if guessed:
            count += 1
    return count


def _network_calls(result: Mapping[str, Any]) -> int:
    calls = 0
    for key in ("case_verification", "deep_review_results"):
        value = _mapping(result.get(key))
        if bool(value.get("available")):
            calls += 1
    return calls


def score_real_document(
    entry: ManifestDocument | Mapping[str, Any],
    actual: Mapping[str, Any],
    *,
    source_overwritten: bool = False,
    export_valid: bool = True,
    runtime_seconds: float | None = None,
    peak_memory_bytes: int | None = None,
    error_code: str | None = None,
) -> RealDocumentScore:
    row = _manifest_view(entry)
    expected = _mapping(row.get("expected"))
    expected_citations = {
        _citation_key(item)
        for item in _sequence(expected.get("citations"))
        if isinstance(item, Mapping)
    }
    actual_citations = {
        _citation_key(item)
        for item in _sequence(actual.get("citation_inventory"))
        if isinstance(item, Mapping)
    }
    citation_precision, citation_recall = _precision_recall(
        expected_citations, actual_citations
    )

    expected_codes = {
        str(code) for code in _sequence(expected.get("issue_codes")) if str(code)
    }
    actual_codes = _issue_codes(actual)
    issue_precision, issue_recall = _precision_recall(expected_codes, actual_codes)

    expected_fixed = expected.get("safe_fixed_text")
    safe_fixed_text_match = (
        None
        if expected_fixed is None
        else str(actual.get("corrected_text") or "") == str(expected_fixed)
    )
    unsafe_automatic_edits = _unsafe_edits(actual)
    unresolved_antecedent_guesses = _unresolved_guesses(actual)
    local_mode_network_calls = _network_calls(actual)
    release_gate_passed = all(
        (
            error_code is None,
            citation_precision == 1.0,
            citation_recall == 1.0,
            issue_precision == 1.0,
            issue_recall == 1.0,
            safe_fixed_text_match is not False,
            unsafe_automatic_edits == 0,
            unresolved_antecedent_guesses == 0,
            local_mode_network_calls == 0,
            not source_overwritten,
            export_valid,
        )
    )
    return RealDocumentScore(
        document_id=str(row.get("document_id") or "unknown"),
        split=str(row.get("split") or "unknown"),
        citation_precision=citation_precision,
        citation_recall=citation_recall,
        issue_precision=issue_precision,
        issue_recall=issue_recall,
        expected_citations=len(expected_citations),
        detected_citations=len(actual_citations),
        expected_issue_codes=len(expected_codes),
        detected_issue_codes=len(actual_codes),
        unsafe_automatic_edits=unsafe_automatic_edits,
        safe_fixed_text_match=safe_fixed_text_match,
        unresolved_antecedent_guesses=unresolved_antecedent_guesses,
        local_mode_network_calls=local_mode_network_calls,
        source_overwritten=source_overwritten,
        export_valid=export_valid,
        release_gate_passed=release_gate_passed,
        runtime_seconds=runtime_seconds,
        peak_memory_bytes=peak_memory_bytes,
        error_code=error_code,
    )


def aggregate_real_document_scores(
    scores: Sequence[RealDocumentScore],
    *,
    manifest_path: Path,
    documents_root: Path,
) -> dict[str, Any]:
    values = tuple(scores)
    count = len(values)

    def average(name: str) -> float:
        if not values:
            return 0.0
        return sum(float(getattr(item, name)) for item in values) / count

    return {
        "schema_version": "1.0",
        "evaluation": "permissioned_real_documents",
        "manifest": Path(manifest_path).name,
        "documents_root": Path(documents_root).name,
        "summary": {
            "document_count": count,
            "citation_precision": average("citation_precision"),
            "citation_recall": average("citation_recall"),
            "issue_precision": average("issue_precision"),
            "issue_recall": average("issue_recall"),
            "unsafe_automatic_edits": sum(
                item.unsafe_automatic_edits for item in values
            ),
            "unresolved_antecedent_guesses": sum(
                item.unresolved_antecedent_guesses for item in values
            ),
            "local_mode_network_calls": sum(
                item.local_mode_network_calls for item in values
            ),
            "source_overwrites": sum(item.source_overwritten for item in values),
            "invalid_exports": sum(not item.export_valid for item in values),
            "release_gate_passed": bool(values)
            and all(item.release_gate_passed for item in values),
        },
        "documents": [item.as_dict() for item in values],
        "privacy": {
            "source_text_included": False,
            "absolute_paths_included": False,
        },
    }


async def evaluate_real_documents(
    documents: Sequence[ManifestDocument],
) -> tuple[RealDocumentScore, ...]:
    from .docx_preservation import apply_docx_export_plan, validate_docx_package
    from .review_session import ReviewSession
    from .tools import review_uploaded_document

    scores: list[RealDocumentScore] = []
    for document in documents:
        payload = document.path.read_bytes()
        before_hash = hashlib.sha256(payload).hexdigest()
        started = time.perf_counter()
        tracemalloc.start()
        result: Mapping[str, Any] = {}
        export_valid = True
        error_code: str | None = None
        try:
            result = await review_uploaded_document(
                {
                    "file_name": document.path.name,
                    "data_base64": base64.b64encode(payload).decode("ascii"),
                },
                document_type=document.document_type,
                mode=document.mode,
                jurisdiction=document.jurisdiction,
                use_local_model=False,
                model_offline_only=True,
                deep_review=False,
            )
            if document.path.suffix.casefold() == ".docx":
                try:
                    plan = ReviewSession.from_result(result).export_plan()
                    exported = apply_docx_export_plan(payload, plan, tracked=True)
                    export_valid = validate_docx_package(exported.payload).valid
                except ValueError:
                    export_valid = False
        except Exception as exc:
            error_code = type(exc).__name__
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        runtime = time.perf_counter() - started
        after_hash = hashlib.sha256(document.path.read_bytes()).hexdigest()
        score = score_real_document(
            document,
            result,
            source_overwritten=before_hash != after_hash,
            export_valid=export_valid,
            runtime_seconds=runtime,
            peak_memory_bytes=peak_memory,
            error_code=error_code,
        )
        scores.append(score)
    return tuple(scores)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate AutoCite against permissioned local documents without "
            "copying source text or absolute paths into the report."
        )
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--documents-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    documents = load_real_document_manifest(args.manifest, args.documents_root)
    scores = asyncio.run(evaluate_real_documents(documents))
    report = aggregate_real_document_scores(
        scores,
        manifest_path=args.manifest,
        documents_root=args.documents_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["release_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
