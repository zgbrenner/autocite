from __future__ import annotations

import json
from pathlib import Path

import pytest

from autocite_mcp.real_document_eval import (
    ManifestError,
    aggregate_real_document_scores,
    load_real_document_manifest,
    score_real_document,
)


def _write_manifest(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _row(relative_path: str = "brief.txt") -> dict:
    return {
        "document_id": "brief-001",
        "relative_path": relative_path,
        "split": "test",
        "permission": {
            "basis": "Original synthetic test document",
            "reviewed_by": "fixture-author",
        },
        "mode": "bluepages",
        "document_type": "brief",
        "jurisdiction": "federal",
        "expected": {
            "citations": [
                {
                    "text": "42 U.S.C. § 1983",
                    "start": 4,
                    "end": 21,
                    "source_type": "statute",
                }
            ],
            "issue_codes": [],
            "safe_fixed_text": "See 42 U.S.C. § 1983.",
        },
    }


def test_manifest_rejects_paths_outside_document_root(tmp_path: Path):
    root = tmp_path / "documents"
    root.mkdir()
    manifest = _write_manifest(tmp_path / "manifest.jsonl", [_row("../secret.txt")])

    with pytest.raises(ManifestError, match="document root"):
        load_real_document_manifest(manifest, root)


def test_manifest_requires_an_explicit_permission_basis(tmp_path: Path):
    root = tmp_path / "documents"
    root.mkdir()
    (root / "brief.txt").write_text("See 42 USC §1983.", encoding="utf-8")
    row = _row()
    row["permission"] = {}
    manifest = _write_manifest(tmp_path / "manifest.jsonl", [row])

    with pytest.raises(ManifestError, match="permission basis"):
        load_real_document_manifest(manifest, root)


def test_manifest_rejects_duplicate_document_ids(tmp_path: Path):
    root = tmp_path / "documents"
    root.mkdir()
    (root / "brief.txt").write_text("See 42 USC §1983.", encoding="utf-8")
    manifest = _write_manifest(tmp_path / "manifest.jsonl", [_row(), _row()])

    with pytest.raises(ManifestError, match="duplicate document_id"):
        load_real_document_manifest(manifest, root)


def test_metrics_count_unsafe_edit_as_a_release_blocker():
    entry = _row()
    actual = {
        "corrected_text": "See invented authority.",
        "citation_inventory": [],
        "applied_edits": [
            {
                "code": "MODEL_GUESS",
                "start": 4,
                "end": 7,
                "original": "old",
                "suggestion": "invented",
                "correction_level": "suggested_fix",
                "confidence": "medium",
            }
        ],
        "remaining_issues": [],
        "rule_findings": [],
        "citation_graph": {"resolutions": []},
        "case_verification": {"available": False},
        "deep_review_results": {"available": False},
    }

    score = score_real_document(entry, actual)

    assert score.unsafe_automatic_edits == 1
    assert score.safe_fixed_text_match is False
    assert score.release_gate_passed is False


def test_metrics_score_exact_citations_and_expected_clean_output():
    entry = _row()
    actual = {
        "corrected_text": "See 42 U.S.C. § 1983.",
        "citation_inventory": [
            {
                "text": "42 U.S.C. § 1983",
                "start": 4,
                "end": 21,
                "source_type": "statute",
            }
        ],
        "applied_edits": [
            {
                "code": "STATUTE_CODE_ABBREVIATION",
                "start": 7,
                "end": 10,
                "original": "USC",
                "suggestion": "U.S.C.",
                "correction_level": "safe_auto_fix",
                "confidence": "high",
            }
        ],
        "remaining_issues": [],
        "rule_findings": [],
        "citation_graph": {"resolutions": []},
        "case_verification": {"available": False},
        "deep_review_results": {"available": False},
    }

    score = score_real_document(entry, actual)

    assert score.citation_precision == 1.0
    assert score.citation_recall == 1.0
    assert score.issue_precision == 1.0
    assert score.issue_recall == 1.0
    assert score.safe_fixed_text_match is True
    assert score.release_gate_passed is True


def test_aggregate_report_does_not_copy_document_text_or_absolute_paths(tmp_path: Path):
    entry = _row()
    actual = {
        "corrected_text": entry["expected"]["safe_fixed_text"],
        "citation_inventory": entry["expected"]["citations"],
        "applied_edits": [],
        "remaining_issues": [],
        "rule_findings": [],
        "citation_graph": {"resolutions": []},
        "case_verification": {"available": False},
        "deep_review_results": {"available": False},
    }
    score = score_real_document(entry, actual)

    report = aggregate_real_document_scores(
        [score],
        manifest_path=tmp_path / "manifest.jsonl",
        documents_root=tmp_path / "private-documents",
    )
    serialized = json.dumps(report)

    assert "See 42" not in serialized
    assert str(tmp_path) not in serialized
    assert report["summary"]["release_gate_passed"] is True
    assert report["documents"][0]["document_id"] == "brief-001"
