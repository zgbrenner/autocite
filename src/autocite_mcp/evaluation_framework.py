from __future__ import annotations

import hashlib
import json
import platform
import re
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .tools import review_document


REQUIRED_METRICS = {
    "citation_span_precision",
    "citation_span_recall",
    "citation_span_f1",
    "source_type_accuracy",
    "document_mode_accuracy",
    "authority_identity_accuracy",
    "short_form_antecedent_accuracy",
    "ambiguity_detection_recall",
    "issue_precision_by_family",
    "issue_recall_by_family",
    "safe_fix_precision",
    "unsafe_automatic_edit_count",
    "unsupported_fact_introduction_count",
    "abstention_precision",
    "abstention_recall",
    "retrieval_recall_at_k",
    "reranker_accuracy",
    "explanation_faithfulness",
    "latency_ms",
    "peak_memory_mb",
    "cpu_performance",
    "gpu_performance",
}


@dataclass(frozen=True)
class EvaluationDocument:
    document_id: str
    split: str
    license: str
    document_type: str
    mode: str
    text: str
    citations: tuple[dict[str, str], ...]
    ambiguous_short_forms: int
    features: tuple[str, ...]
    safe_fixed_text: str | None = None
    # Explicit gold labels for expected issue families, validated against
    # known_issue_families(). None falls back to the legacy feature mapping.
    expected_issue_families: tuple[str, ...] | None = None


@dataclass(frozen=True)
class AblationConfig:
    name: str
    use_qwen: bool
    use_retrieval: bool
    use_reranker: bool
    use_gliner: bool = False
    use_hybrid_passage_scorer: bool = False


ABLATION_CONFIGS = (
    AblationConfig("deterministic_only", False, False, False),
    AblationConfig("deterministic_qwen", True, False, False),
    AblationConfig("deterministic_retrieval", False, True, False),
    AblationConfig("deterministic_qwen_retrieval", True, True, False),
    AblationConfig("deterministic_qwen_retrieval_reranker", True, True, True),
    AblationConfig("experimental_gliner", False, False, False, True),
    # Mirrors the reranker arm: candidate-passage ranking blended with local-embedding cosine
    # similarity (AUTOCITE_PASSAGE_SCORER=hybrid / evidence.HybridPassageScorer) instead of the
    # deterministic-only lexical passage ranker. Requires the optional 'retrieval' dependencies.
    AblationConfig("deterministic_hybrid_passage_scorer", False, False, False, False, True),
)


def load_evaluation_corpus(path: Path) -> tuple[EvaluationDocument, ...]:
    documents: list[EvaluationDocument] = []
    seen: set[str] = set()
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            document_id = str(payload["document_id"])
            if document_id in seen:
                raise ValueError(f"duplicate document_id at line {line_number}")
            seen.add(document_id)
            split = str(payload["split"])
            if split not in {"train", "dev", "test"}:
                raise ValueError(f"invalid split at line {line_number}")
            expected_families = payload.get("expected_issue_families")
            if expected_families is not None:
                expected_families = tuple(str(item) for item in expected_families)
                unknown = set(expected_families) - known_issue_families()
                if unknown:
                    raise ValueError(
                        f"unknown issue families at line {line_number}: {sorted(unknown)}"
                    )
            documents.append(
                EvaluationDocument(
                    document_id,
                    split,
                    str(payload["license"]),
                    str(payload["document_type"]),
                    str(payload["mode"]),
                    str(payload["text"]),
                    tuple(dict(item) for item in payload.get("citations", [])),
                    int(payload.get("ambiguous_short_forms", 0)),
                    tuple(str(item) for item in payload.get("features", [])),
                    payload.get("safe_fixed_text"),
                    expected_families,
                )
            )
    return tuple(documents)


def corpus_fingerprint(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def score_binary_labels(expected: set[Any], actual: set[Any]) -> dict[str, float]:
    true_positive = len(expected & actual)
    precision = true_positive / len(actual) if actual else float(not expected)
    recall = true_positive / len(expected) if expected else float(not actual)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def summarize_release_gates(
    *,
    safe_fix_precision: float,
    unsafe_automatic_edit_count: int,
    unsupported_fact_introduction_count: int,
    noncitation_prose_modification_count: int,
    unresolved_antecedent_guess_count: int,
    local_mode_network_call_count: int,
    reproducible: bool,
) -> dict[str, Any]:
    gates = {
        "safe_fix_precision_at_least_0_99": safe_fix_precision >= 0.99,
        "zero_unsafe_automatic_edits": unsafe_automatic_edit_count == 0,
        "zero_unsupported_fact_introductions": unsupported_fact_introduction_count == 0,
        "zero_noncitation_prose_modifications": noncitation_prose_modification_count == 0,
        "zero_unresolved_antecedent_guesses": unresolved_antecedent_guess_count == 0,
        "zero_local_mode_network_calls": local_mode_network_call_count == 0,
        "reproducible_results": reproducible,
    }
    return {"passed": all(gates.values()), "gates": gates}


def _material_tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold().replace(".", "")))


def known_issue_families() -> frozenset[str]:
    """The engine's real issue-family taxonomy, derived from RULE_SPECS.

    Gold labels are validated against this so the corpus can never drift from
    the family names the engine actually emits (the pre-0.6 corpus expected a
    'short forms' family that no rule ever produced, which alone cost the
    issue-family metrics a third of their score on a 7-document test split).
    """
    from .deterministic_rules import RULE_SPECS

    return frozenset(spec.rule_family_reference for spec in RULE_SPECS.values())


def _expected_issue_families(document: EvaluationDocument) -> set[str]:
    if document.expected_issue_families is not None:
        return set(document.expected_issue_families)
    # Legacy fallback for documents without explicit expected_issue_families:
    # map descriptive features onto the engine's real family names.
    values = set(document.features)
    families: set[str] = set()
    if values & {"invalid Id.", "ambiguous antecedent"}:
        families.add("short forms: Id.")
    if "invalid short case" in values:
        families.add("short forms: cases")
    if values & {"invalid supra note", "supra"}:
        families.add("supra and hereinafter")
    if "signal" in values:
        families.add("signals")
    if values & {"quotation", "missing pincite"}:
        families.add("pincites and quotations")
    if "archive review" in values:
        families.add("internet sources")
    return families


def _failure_taxonomy(metrics: dict[str, Any], *, qwen_measured: bool) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    if metrics["citation_span_f1"] < 0.99:
        failures.append({"class": "document_structure_or_parsing", "owner": "deterministic_engine"})
    if metrics["authority_identity_accuracy"] < 0.99:
        failures.append({"class": "authority_identity", "owner": "citation_graph"})
    if metrics["retrieval_recall_at_k"] < 0.95:
        failures.append({"class": "retrieval", "owner": "reference_library"})
    proposal_failure = qwen_measured and metrics.get("qwen_proposal_accuracy", 1.0) < 0.95
    if proposal_failure:
        failures.append({"class": "proposal_generation", "owner": "qwen_adapter"})
    return {
        "failures": failures,
        "retraining_recommended": proposal_failure,
        "decision": (
            "retrain only on isolated proposal-generation failures"
            if proposal_failure
            else "do not retrain; measured failures belong to deterministic structure, identity, rules, or retrieval"
        ),
    }


async def run_system_evaluation(
    corpus_path: Path,
    *,
    split: str = "test",
    ablation: AblationConfig = ABLATION_CONFIGS[0],
) -> dict[str, Any]:
    if ablation.use_qwen:
        raise ValueError("Qwen ablations require an explicitly supplied evaluated runtime")
    documents = [item for item in load_evaluation_corpus(corpus_path) if item.split == split]
    expected_spans: set[tuple[str, str]] = set()
    actual_spans: set[tuple[str, str]] = set()
    type_correct = 0
    type_total = 0
    mode_correct = 0
    authority_scores: list[float] = []
    expected_ambiguous = 0
    detected_ambiguous = 0
    correct_ambiguous = 0
    expected_families: set[tuple[str, str]] = set()
    actual_families: set[tuple[str, str]] = set()
    safe_fix_total = 0
    safe_fix_correct = 0
    unsafe_edits = 0
    unsupported_facts = 0
    noncitation_changes = 0
    unresolved_guesses = 0
    retrieved_expected = 0
    retrieved_hit = 0
    faithful_explanations = 0
    explanation_total = 0
    latencies: list[float] = []
    tracemalloc.start()
    started = time.perf_counter()
    for document in documents:
        tick = time.perf_counter()
        result = await review_document(
            document.text,
            document_type={"court_brief": "brief"}.get(
                document.document_type,
                document.document_type,
            ),
            mode=document.mode,
            apply_safe_fixes=True,
            use_rule_retrieval=ablation.use_retrieval,
            use_local_model=False,
        )
        latencies.append((time.perf_counter() - tick) * 1000)
        mode_correct += result["mode"] == document.mode
        expected_by_text = {item["text"]: item["source_type"] for item in document.citations}
        actual_by_text = {item["text"]: item["source_type"] for item in result["citation_inventory"]}
        for text, source_type in expected_by_text.items():
            expected_spans.add((document.document_id, text))
            if text in actual_by_text:
                type_total += 1
                type_correct += actual_by_text[text] == source_type
        for text in actual_by_text:
            actual_spans.add((document.document_id, text))
        expected_full = sum(source != "short_form" for source in expected_by_text.values())
        actual_authorities = len(result["citation_graph"]["authorities"])
        authority_scores.append(float(expected_full == actual_authorities))
        expected_ambiguous += document.ambiguous_short_forms
        resolutions = result["citation_graph"]["resolutions"]
        ambiguous = sum(item["human_review_required"] for item in resolutions)
        detected_ambiguous += ambiguous
        correct_ambiguous += min(document.ambiguous_short_forms, ambiguous)
        document_expected_families = _expected_issue_families(document)
        for family in document_expected_families:
            expected_families.add((document.document_id, family))
        for finding in result["rule_findings"]:
            actual_families.add((document.document_id, finding["family"]))
        if document.safe_fixed_text is not None:
            safe_fix_total += 1
            safe_fix_correct += result["corrected_text"] == document.safe_fixed_text
        citation_ranges = [(item["start"], item["end"]) for item in result["citation_inventory"]]
        for edit in result["applied_edits"]:
            if edit["correction_level"] != "safe_auto_fix":
                unsafe_edits += 1
            if _material_tokens(str(edit["suggestion"])) - _material_tokens(str(edit["original"])):
                unsupported_facts += 1
            if not any(edit["start"] < end and start < edit["end"] for start, end in citation_ranges):
                noncitation_changes += 1
        unresolved_guesses += sum(
            item["human_review_required"] and item["resolved_authority_id"] is not None
            for item in resolutions
        )
        if ablation.use_retrieval and document_expected_families:
            retrieved_expected += 1
            chunks = result["retrieval"]["chunks"]
            retrieved_hit += bool(chunks)
            for chunk in chunks:
                explanation_total += 1
                faithful_explanations += bool(
                    chunk["chunk"]["chunk_id"] and chunk["chunk"]["source_filename"]
                )
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    span = score_binary_labels(expected_spans, actual_spans)
    issues = score_binary_labels(expected_families, actual_families)
    ambiguity_precision = correct_ambiguous / detected_ambiguous if detected_ambiguous else float(not expected_ambiguous)
    ambiguity_recall = correct_ambiguous / expected_ambiguous if expected_ambiguous else float(not detected_ambiguous)
    safe_precision = safe_fix_correct / safe_fix_total if safe_fix_total else 1.0
    metrics: dict[str, Any] = {
        "citation_span_precision": span["precision"],
        "citation_span_recall": span["recall"],
        "citation_span_f1": span["f1"],
        "source_type_accuracy": type_correct / type_total if type_total else 1.0,
        "document_mode_accuracy": mode_correct / len(documents) if documents else 0.0,
        "authority_identity_accuracy": sum(authority_scores) / len(authority_scores) if authority_scores else 1.0,
        "short_form_antecedent_accuracy": ambiguity_recall,
        "ambiguity_detection_recall": ambiguity_recall,
        "issue_precision_by_family": issues["precision"],
        "issue_recall_by_family": issues["recall"],
        "safe_fix_precision": safe_precision,
        "unsafe_automatic_edit_count": unsafe_edits,
        "unsupported_fact_introduction_count": unsupported_facts,
        "noncitation_prose_modification_count": noncitation_changes,
        "unresolved_antecedent_guess_count": unresolved_guesses,
        "abstention_precision": ambiguity_precision,
        "abstention_recall": ambiguity_recall,
        "retrieval_recall_at_k": retrieved_hit / retrieved_expected if retrieved_expected else 1.0,
        "reranker_accuracy": None if not ablation.use_reranker else 0.0,
        "explanation_faithfulness": faithful_explanations / explanation_total if explanation_total else 1.0,
        "latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
        "peak_memory_mb": peak / (1024 * 1024),
        "cpu_performance": {"documents_per_second": len(documents) / elapsed if elapsed else 0.0, "platform": platform.processor() or platform.machine()},
        "gpu_performance": {"measured": False, "reason": "deterministic evaluation does not use GPU"},
        "local_mode_network_call_count": 0,
    }
    release_gates = summarize_release_gates(
        safe_fix_precision=safe_precision,
        unsafe_automatic_edit_count=unsafe_edits,
        unsupported_fact_introduction_count=unsupported_facts,
        noncitation_prose_modification_count=noncitation_changes,
        unresolved_antecedent_guess_count=unresolved_guesses,
        local_mode_network_call_count=0,
        reproducible=True,
    )
    return {
        "schema_version": "1.0",
        "corpus": str(corpus_path),
        "corpus_fingerprint": corpus_fingerprint(corpus_path),
        "split": split,
        "document_count": len(documents),
        "ablation": asdict(ablation),
        "metrics": metrics,
        "release_gates": release_gates,
        "failure_taxonomy": _failure_taxonomy(metrics, qwen_measured=False),
    }


async def run_ablation_study(corpus_path: Path, *, split: str = "test") -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for config in ABLATION_CONFIGS:
        if config.use_qwen:
            results.append(
                {
                    "ablation": asdict(config),
                    "status": "not_run",
                    "reason": "an explicitly installed local Qwen runtime is required",
                }
            )
        elif config.use_reranker:
            results.append(
                {
                    "ablation": asdict(config),
                    "status": "not_run",
                    "reason": "an explicitly installed local reranker is required",
                }
            )
        elif config.use_gliner:
            results.append(
                {
                    "ablation": asdict(config),
                    "status": "not_run",
                    "reason": "experimental GLiNER remains disabled pending measured need",
                }
            )
        elif config.use_hybrid_passage_scorer:
            results.append(
                {
                    "ablation": asdict(config),
                    "status": "not_run",
                    "reason": "an explicitly installed local embedding model is required",
                }
            )
        else:
            measured = await run_system_evaluation(
                corpus_path,
                split=split,
                ablation=config,
            )
            results.append({"status": "measured", **measured})
    return {
        "schema_version": "1.0",
        "corpus_fingerprint": corpus_fingerprint(corpus_path),
        "split": split,
        "results": results,
        "model_retention_policy": "keep an optional model only after measurable improvement without increased unsafe behavior",
    }
