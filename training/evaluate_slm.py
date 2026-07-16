from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from autocite_mcp.slm import SLMProposal, validate_proposal


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _macro_f1(expected: list[str], predicted: list[str]) -> float:
    labels = sorted(set(expected) | set(predicted))
    scores: list[float] = []
    for label in labels:
        true_positive = sum(e == label and p == label for e, p in zip(expected, predicted))
        false_positive = sum(e != label and p == label for e, p in zip(expected, predicted))
        false_negative = sum(e == label and p != label for e, p in zip(expected, predicted))
        precision = _ratio(true_positive, true_positive + false_positive)
        recall = _ratio(true_positive, true_positive + false_negative)
        scores.append(_ratio(2 * precision * recall, precision + recall))
    return round(sum(scores) / len(scores), 6) if scores else 0.0


def evaluate_predictions(rows: Iterable[dict[str, Any]]) -> dict[str, float]:
    items = list(rows)
    total = len(items)
    valid_json = sum(bool(row.get("valid_json")) for row in items)
    span_matches = 0
    expected_labels: list[str] = []
    predicted_labels: list[str] = []
    correction_total = 0
    correction_matches = 0
    expected_abstentions = 0
    predicted_abstentions = 0
    correct_abstentions = 0
    for row in items:
        expected = dict(row.get("expected") or {})
        predicted = dict(row.get("predicted") or {})
        span_matches += (
            expected.get("start") == predicted.get("start")
            and expected.get("end") == predicted.get("end")
        )
        expected_labels.append(str(expected.get("issue_code") or "INVALID"))
        predicted_labels.append(str(predicted.get("issue_code") or "INVALID"))
        if expected.get("proposed_citation") is not None:
            correction_total += 1
            correction_matches += (
                expected.get("proposed_citation") == predicted.get("proposed_citation")
            )
        expected_abstain = expected.get("proposed_citation") is None
        predicted_abstain = predicted.get("proposed_citation") is None
        expected_abstentions += expected_abstain
        predicted_abstentions += predicted_abstain
        correct_abstentions += expected_abstain and predicted_abstain

    return {
        "valid_json_rate": _ratio(valid_json, total),
        "citation_span_accuracy": _ratio(span_matches, total),
        "issue_classification_macro_f1": _macro_f1(expected_labels, predicted_labels),
        "exact_correction_accuracy": _ratio(correction_matches, correction_total),
        "abstention_precision": _ratio(correct_abstentions, predicted_abstentions),
        "abstention_recall": _ratio(correct_abstentions, expected_abstentions),
        "hallucinated_fact_rate": _ratio(
            sum(bool(row.get("unsupported_facts")) for row in items), total
        ),
        "unsafe_auto_apply_rate": _ratio(
            sum(bool(row.get("unsafe_applied")) for row in items), total
        ),
    }


def run_safety_evaluation(path: str | Path) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    unsafe = 0
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        proposal = SLMProposal.from_mapping(row["proposal"])
        validation = validate_proposal(
            proposal,
            str(row["document"]),
            expected_mode=proposal.mode,
            expected_source_type=proposal.source_type,
        )
        expected_valid = bool(row["expected_valid"])
        passed = validation.valid == expected_valid
        unsafe_acceptance = (
            not expected_valid
            and validation.valid
            and proposal.confidence == "high"
            and proposal.proposed_citation is not None
        )
        unsafe += unsafe_acceptance
        details.append(
            {
                "line": line_number,
                "name": row.get("name"),
                "passed": passed,
                "actual_valid": validation.valid,
                "expected_valid": expected_valid,
                "reasons": list(validation.reasons),
                "unsafe_acceptance": unsafe_acceptance,
            }
        )
    failed = sum(not item["passed"] for item in details)
    return {
        "path": str(Path(path)),
        "total": len(details),
        "passed": len(details) - failed,
        "failed": failed,
        "unsafe_auto_apply_count": unsafe,
        "release_gate_passed": failed == 0 and unsafe == 0,
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate AutoCite SLM outputs")
    parser.add_argument("--safety-file", type=Path, default=Path("evals/slm_safety.jsonl"))
    parser.add_argument("--predictions", type=Path)
    args = parser.parse_args()
    result: dict[str, Any] = {"safety": run_safety_evaluation(args.safety_file)}
    if args.predictions:
        rows = [
            json.loads(line)
            for line in args.predictions.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        result["metrics"] = evaluate_predictions(rows)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
