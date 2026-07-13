import json
from pathlib import Path

from autocite_mcp.evals import run_gold_evaluation


def test_gold_evaluation_calculates_metrics(tmp_path: Path):
    rows = [
        {
            "task": "fix",
            "input": "42 USC §1983",
            "mode": "bluepages",
            "expected": "42 U.S.C. § 1983",
        },
        {
            "task": "extract",
            "input": "See Obergefell v. Hodges, 576 U.S. 644, 675 (2015).",
            "expected_source_types": ["case"],
        },
        {
            "task": "quote",
            "quote": "the right to marry is fundamental",
            "source": "The right to marry is fundamental under the Constitution.",
            "expected_statuses": ["exact", "normalized"],
        },
        {
            "task": "rank",
            "proposition": "The right to marry is fundamental",
            "source": "Standing requires injury. The right to marry is fundamental under the Constitution.",
            "expected_contains": "right to marry",
        },
    ]
    path = tmp_path / "gold.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    result = run_gold_evaluation(path)
    assert result["total"] == 4
    assert result["passed"] == 4
    assert result["accuracy"] == 1.0
    assert result["by_task"]["fix"]["accuracy"] == 1.0
