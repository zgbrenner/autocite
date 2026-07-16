import json
from pathlib import Path

from training.build_dataset import build_records, write_jsonl


SEEDS = Path(__file__).parents[1] / "training" / "seed_examples.jsonl"


def test_dataset_generation_is_deterministic_and_schema_valid(tmp_path: Path):
    first = build_records(SEEDS, seed=42)
    second = build_records(SEEDS, seed=42)
    assert first == second
    assert len(first) >= 40
    for row in first:
        assert row["split"] in {"train", "validation", "test"}
        assert [message["role"] for message in row["messages"]] == [
            "system",
            "user",
            "assistant",
        ]
        completion = json.loads(row["messages"][-1]["content"])
        assert completion["mode"] in {"bluepages", "whitepages"}
        assert row["metadata"]["contains_manual_excerpt"] is False
        assert row["metadata"]["license"] == "synthetic_or_original"

    output = tmp_path / "dataset.jsonl"
    write_jsonl(first, output)
    assert len(output.read_text(encoding="utf-8").splitlines()) == len(first)


def test_dataset_balances_modes_and_teaches_abstention():
    records = build_records(SEEDS, seed=42)
    counts = {
        mode: sum(row["metadata"]["mode"] == mode for row in records)
        for mode in ("bluepages", "whitepages")
    }
    assert counts["bluepages"] == counts["whitepages"]
    abstentions = [row for row in records if row["metadata"]["abstain"]]
    assert len(abstentions) / len(records) >= 0.20
    for row in abstentions:
        completion = json.loads(row["messages"][-1]["content"])
        assert completion["proposed_citation"] is None
        assert completion["missing_facts"]


def test_citation_groups_do_not_cross_splits():
    records = build_records(SEEDS, seed=42)
    group_splits: dict[str, set[str]] = {}
    for row in records:
        group_splits.setdefault(row["metadata"]["group"], set()).add(row["split"])
    assert all(len(splits) == 1 for splits in group_splits.values())


def test_dataset_contains_major_first_release_source_families():
    records = build_records(SEEDS, seed=42)
    source_types = {row["metadata"]["source_type"] for row in records}
    assert {
        "case",
        "statute",
        "regulation",
        "constitution",
        "journal_article",
        "book",
        "internet",
        "short_form",
    }.issubset(source_types)
