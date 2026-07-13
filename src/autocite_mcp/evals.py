from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .engine import CitationEngine
from .evidence import match_quote, rank_passages

_ENGINE = CitationEngine()


def _evaluate_row(row: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    task = str(row.get("task") or "")
    if task == "fix":
        result = _ENGINE.fix(str(row["input"]), mode=str(row.get("mode") or "bluepages"))
        actual = result["fixed_text"]
        expected = str(row["expected"])
        return actual == expected, {"actual": actual, "expected": expected}
    if task == "extract":
        result = _ENGINE.analyze(str(row["input"]), mode=str(row.get("mode") or "bluepages"))
        actual = [item["source_type"] for item in result["citations"]]
        expected = list(row.get("expected_source_types") or [])
        return actual == expected, {"actual": actual, "expected": expected}
    if task == "quote":
        result = match_quote(str(row["quote"]), str(row["source"]))
        expected = set(row.get("expected_statuses") or [])
        return result["status"] in expected, {"actual": result["status"], "expected": sorted(expected)}
    if task == "rank":
        ranked = rank_passages(str(row["proposition"]), str(row["source"]), limit=1)
        actual = ranked[0]["passage"] if ranked else ""
        expected = str(row["expected_contains"])
        return expected.lower() in actual.lower(), {"actual": actual, "expected_contains": expected}
    raise ValueError(f"Unknown evaluation task: {task}")


def run_gold_evaluation(path: str | Path) -> dict[str, Any]:
    """Run deterministic gold fixtures and report per-task accuracy."""
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"Line {line_number} must contain a JSON object")
        rows.append(payload)

    task_totals: dict[str, int] = defaultdict(int)
    task_passed: dict[str, int] = defaultdict(int)
    details: list[dict[str, Any]] = []
    passed = 0
    for index, row in enumerate(rows, start=1):
        task = str(row.get("task") or "unknown")
        ok, detail = _evaluate_row(row)
        task_totals[task] += 1
        if ok:
            passed += 1
            task_passed[task] += 1
        details.append({"index": index, "task": task, "passed": ok, **detail})

    total = len(rows)
    by_task = {
        task: {
            "total": count,
            "passed": task_passed[task],
            "accuracy": round(task_passed[task] / count, 4) if count else 0.0,
        }
        for task, count in sorted(task_totals.items())
    }
    return {
        "path": str(Path(path)),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "by_task": by_task,
        "details": details,
    }
