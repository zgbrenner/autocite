from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Iterable


SYSTEM_PROMPT = (
    "You are AutoCite, a conservative U.S. legal citation reviewer. Return exactly "
    "one JSON object. Do not invent parties, numbers, reporters, pincites, dates, URLs, "
    "treatment, or source facts. Use null when required facts are missing."
)


def _proposal(
    citation: str,
    proposed: str | None,
    *,
    mode: str,
    source_type: str,
    issue_code: str,
    explanation: str,
    missing_facts: list[str] | None = None,
    group: str,
) -> dict[str, Any]:
    document = f"See {citation}."
    start = 4
    end = start + len(citation)
    missing = list(missing_facts or [])
    completion = {
        "citation_text": citation,
        "start": start,
        "end": end,
        "source_type": source_type,
        "mode": mode,
        "issue_code": issue_code,
        "explanation": explanation,
        "confidence": "low" if proposed is None else "high",
        "proposed_citation": proposed,
        "missing_facts": missing,
        "facts_used": {},
    }
    task = {
        "document": document,
        "citation_text": citation,
        "start": start,
        "end": end,
        "source_type": source_type,
        "mode": mode,
    }
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(task, ensure_ascii=False, sort_keys=True)},
            {"role": "assistant", "content": json.dumps(completion, ensure_ascii=False, sort_keys=True)},
        ],
        "metadata": {
            "mode": mode,
            "source_type": source_type,
            "group": group,
            "abstain": proposed is None,
            "license": "synthetic_or_original",
            "contains_manual_excerpt": False,
        },
    }


def _synthetic_examples() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    corrections = [
        ("42 USC §1983", "42 U.S.C. § 1983", "statute", "STATUTE_CODE_ABBREVIATION", "statute-42"),
        ("17 USC §102", "17 U.S.C. § 102", "statute", "STATUTE_CODE_ABBREVIATION", "statute-17"),
        ("15 USC §1", "15 U.S.C. § 1", "statute", "STATUTE_CODE_ABBREVIATION", "statute-15"),
        ("29 USC §206", "29 U.S.C. § 206", "statute", "STATUTE_CODE_ABBREVIATION", "statute-29"),
        ("17 CFR §240.10b-5", "17 C.F.R. § 240.10b-5", "regulation", "REGULATION_CODE_ABBREVIATION", "reg-17"),
        ("29 CFR §1604.11", "29 C.F.R. § 1604.11", "regulation", "REGULATION_CODE_ABBREVIATION", "reg-29"),
        ("576 US 644", "576 U.S. 644", "case", "REPORTER_ABBREVIATION", "reporter-us-576"),
        ("410 US 113", "410 U.S. 113", "case", "REPORTER_ABBREVIATION", "reporter-us-410"),
        ("347 US 483", "347 U.S. 483", "case", "REPORTER_ABBREVIATION", "reporter-us-347"),
        ("123 F3d 456", "123 F.3d 456", "case", "REPORTER_ABBREVIATION", "reporter-f3d"),
        ("id at 675", "Id. at 675", "short_form", "SHORT_FORM_CAPITALIZATION", "id-675"),
        ("ID. at 12", "Id. at 12", "short_form", "SHORT_FORM_CAPITALIZATION", "id-12"),
        ("U.S. Const. amend. XIV", "U.S. Const. amend. XIV", "constitution", "NO_CHANGE", "constitution-14"),
        ("U.S. Const. art. I, § 8", "U.S. Const. art. I, § 8", "constitution", "NO_CHANGE", "constitution-art1"),
    ]
    abstentions = [
        ("Smith v. Jones, 123 F.3d 456", "case", ["court", "year"], "case-missing-parenthetical"),
        ("Doe v. State", "case", ["volume", "reporter", "first page", "court", "year"], "case-name-only"),
        ("https://example.com/update", "internet", ["author", "page title", "publication date"], "internet-bare"),
        ("Privacy and Technology 45", "journal_article", ["author", "journal", "volume", "year"], "journal-incomplete"),
        ("Artificial Intelligence Law 120", "book", ["author", "edition", "publisher", "year"], "book-incomplete"),
        ("Id. at 9", "short_form", ["unambiguous antecedent"], "id-orphan"),
        ("Mass. Gen. Laws § 2", "statute", ["chapter or title", "edition or year if required"], "state-statute-incomplete"),
    ]
    for mode in ("bluepages", "whitepages"):
        for citation, proposed, source_type, code, group in corrections:
            examples.append(
                _proposal(
                    citation,
                    proposed,
                    mode=mode,
                    source_type=source_type,
                    issue_code=code,
                    explanation=(
                        "The citation is already mechanically clean."
                        if code == "NO_CHANGE"
                        else "Apply the mechanical abbreviation or capitalization rule."
                    ),
                    group=group,
                )
            )
        for citation, source_type, missing, group in abstentions:
            examples.append(
                _proposal(
                    citation,
                    None,
                    mode=mode,
                    source_type=source_type,
                    issue_code="INSUFFICIENT_INFORMATION",
                    explanation="Required citation facts are not present; do not guess.",
                    missing_facts=missing,
                    group=group,
                )
            )
    return examples


def _expanded_examples() -> list[dict[str, Any]]:
    """Create broad mechanical and abstention coverage without manual text excerpts."""
    examples: list[dict[str, Any]] = []
    statutes = [
        (5, "552"),
        (7, "6"),
        (8, "1324a"),
        (12, "1841"),
        (15, "1"),
        (15, "45"),
        (17, "102"),
        (17, "106"),
        (18, "1030"),
        (26, "61"),
        (29, "206"),
        (35, "271"),
        (42, "1981"),
        (42, "1983"),
        (47, "230"),
        (50, "1701"),
    ]
    regulations = [
        (5, "2635.101"),
        (12, "1005.1"),
        (16, "312.1"),
        (17, "230.501"),
        (17, "240.10b-5"),
        (21, "11.10"),
        (29, "1604.11"),
        (40, "122.26"),
        (45, "164.502"),
        (47, "64.1200"),
    ]
    reporters = [
        (volume, reporter, page)
        for volume, page in zip(range(101, 501, 10), range(111, 911, 20))
        for reporter in ("US", "F3d")
    ]
    for mode in ("bluepages", "whitepages"):
        for title, section in statutes:
            for raw_code in ("USC", "U S C", "U.S.C"):
                citation = f"{title} {raw_code} §{section}"
                examples.append(
                    _proposal(
                        citation,
                        f"{title} U.S.C. § {section}",
                        mode=mode,
                        source_type="statute",
                        issue_code="STATUTE_CODE_ABBREVIATION",
                        explanation="Normalize the code abbreviation and section spacing.",
                        group=f"expanded-statute-{title}-{section}-{raw_code.replace(' ', '')}",
                    )
                )
        for title, section in regulations:
            for raw_code in ("CFR", "C F R", "C.F.R"):
                citation = f"{title} {raw_code} §{section}"
                examples.append(
                    _proposal(
                        citation,
                        f"{title} C.F.R. § {section}",
                        mode=mode,
                        source_type="regulation",
                        issue_code="REGULATION_CODE_ABBREVIATION",
                        explanation="Normalize the code abbreviation and section spacing.",
                        group=f"expanded-reg-{title}-{section}-{raw_code.replace(' ', '')}",
                    )
                )
        for volume, reporter, page in reporters:
            canonical = "U.S." if reporter == "US" else "F.3d"
            citation = f"{volume} {reporter} {page}"
            examples.append(
                _proposal(
                    citation,
                    f"{volume} {canonical} {page}",
                    mode=mode,
                    source_type="case",
                    issue_code="REPORTER_ABBREVIATION",
                    explanation="Normalize the reporter abbreviation without adding case facts.",
                    group=f"expanded-reporter-{volume}-{reporter}-{page}",
                )
            )
        for page in range(1, 81, 2):
            examples.append(
                _proposal(
                    f"id at {page}",
                    f"Id. at {page}",
                    mode=mode,
                    source_type="short_form",
                    issue_code="SHORT_FORM_CAPITALIZATION",
                    explanation="Normalize Id. capitalization and punctuation.",
                    group=f"expanded-id-{page}",
                )
            )
        for index in range(80):
            kind = index % 4
            if kind == 0:
                citation = f"Example v. Sample {index}"
                source_type = "case"
                missing = ["volume", "reporter", "first page", "court", "year"]
            elif kind == 1:
                citation = f"https://example.com/legal-update-{index}"
                source_type = "internet"
                missing = ["author", "page title", "publication date"]
            elif kind == 2:
                citation = f"Emerging Technology Law {index + 1}"
                source_type = "journal_article"
                missing = ["author", "journal", "volume", "year"]
            else:
                citation = f"Treatise on Digital Law {index + 1}"
                source_type = "book"
                missing = ["author", "edition", "publisher", "year"]
            examples.append(
                _proposal(
                    citation,
                    None,
                    mode=mode,
                    source_type=source_type,
                    issue_code="INSUFFICIENT_INFORMATION",
                    explanation="Required citation facts are absent; abstain rather than guess.",
                    missing_facts=missing,
                    group=f"expanded-abstain-{index}",
                )
            )
    return examples


def _load_seed_examples(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        raw = json.loads(line)
        required = {"citation", "proposed", "mode", "source_type", "issue_code", "group"}
        if not isinstance(raw, dict) or required - set(raw):
            raise ValueError(f"Invalid seed example on line {line_number}")
        rows.append(
            _proposal(
                str(raw["citation"]),
                raw["proposed"],
                mode=str(raw["mode"]),
                source_type=str(raw["source_type"]),
                issue_code=str(raw["issue_code"]),
                explanation=str(raw.get("explanation") or "Review the citation conservatively."),
                missing_facts=list(raw.get("missing_facts") or []),
                group=str(raw["group"]),
            )
        )
    return rows


def _assign_group_splits(records: list[dict[str, Any]], seed: int) -> None:
    groups = sorted({str(row["metadata"]["group"]) for row in records})
    groups.sort(key=lambda group: hashlib.sha256(f"{seed}:{group}".encode()).hexdigest())
    assignments = {
        group: ("test" if index % 10 == 0 else "validation" if index % 10 == 1 else "train")
        for index, group in enumerate(groups)
    }
    for row in records:
        row["split"] = assignments[str(row["metadata"]["group"])]


def build_records(seed_path: str | Path, *, seed: int = 42) -> list[dict[str, Any]]:
    records = _synthetic_examples() + _expanded_examples() + _load_seed_examples(seed_path)
    blue = sum(row["metadata"]["mode"] == "bluepages" for row in records)
    white = sum(row["metadata"]["mode"] == "whitepages" for row in records)
    if blue != white:
        raise ValueError("Seed examples must keep Bluepages and Whitepages balanced")
    _assign_group_splits(records, seed)
    random.Random(seed).shuffle(records)
    return records


def write_jsonl(records: Iterable[dict[str, Any]], output: str | Path) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in records) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the AutoCite SLM dataset")
    parser.add_argument("--seeds", type=Path, default=Path("training/seed_examples.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("training/autocite_slm.jsonl"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    records = build_records(args.seeds, seed=args.seed)
    write_jsonl(records, args.output)
    print(json.dumps({"output": str(args.output), "records": len(records)}, indent=2))


if __name__ == "__main__":
    main()
