from __future__ import annotations

from pathlib import Path

from autocite_mcp.evaluation_framework import (
    ABLATION_CONFIGS,
    REQUIRED_METRICS,
    corpus_fingerprint,
    load_evaluation_corpus,
    score_binary_labels,
    summarize_release_gates,
    run_ablation_study,
)


CORPUS = Path(__file__).parents[1] / "evals" / "system" / "documents.jsonl"


def test_document_splits_are_disjoint_and_feature_complete():
    documents = load_evaluation_corpus(CORPUS)
    ids = [item.document_id for item in documents]
    assert len(ids) == len(set(ids))
    assert {item.split for item in documents} == {"train", "dev", "test"}
    features = {feature for item in documents for feature in item.features}
    required = {
        "court filing", "practitioner memorandum", "law-review footnote",
        "seminar paper", "case", "statute", "regulation", "constitution", "book",
        "journal article", "website", "court document", "administrative material",
        "multiple authorities in one footnote", "invalid Id.", "invalid supra note",
        "signal", "parenthetical", "quotation", "missing pincite",
        "intentionally incomplete citation", "adversarial invention trap",
    }
    assert required <= features
    assert all(item.license in {"CC0-1.0", "public-domain", "licensed", "original"} for item in documents)


def test_required_metrics_and_ablations_are_declared():
    assert {
        "citation_span_precision", "citation_span_recall", "citation_span_f1",
        "source_type_accuracy", "document_mode_accuracy", "authority_identity_accuracy",
        "short_form_antecedent_accuracy", "ambiguity_detection_recall",
        "safe_fix_precision", "unsafe_automatic_edit_count",
        "unsupported_fact_introduction_count", "abstention_precision", "abstention_recall",
        "retrieval_recall_at_k", "reranker_accuracy", "explanation_faithfulness",
        "latency_ms", "peak_memory_mb", "cpu_performance", "gpu_performance",
    } <= REQUIRED_METRICS
    assert [item.name for item in ABLATION_CONFIGS[:5]] == [
        "deterministic_only", "deterministic_qwen", "deterministic_retrieval",
        "deterministic_qwen_retrieval", "deterministic_qwen_retrieval_reranker",
    ]


def test_binary_metric_math_and_critical_release_gates():
    scored = score_binary_labels({"a", "b"}, {"b", "c"})
    assert scored == {"precision": 0.5, "recall": 0.5, "f1": 0.5}
    gates = summarize_release_gates(
        safe_fix_precision=1.0,
        unsafe_automatic_edit_count=0,
        unsupported_fact_introduction_count=0,
        noncitation_prose_modification_count=0,
        unresolved_antecedent_guess_count=0,
        local_mode_network_call_count=0,
        reproducible=True,
    )
    assert gates["passed"] is True
    assert all(gates["gates"].values())


def test_corpus_fingerprint_is_reproducible():
    assert corpus_fingerprint(CORPUS) == corpus_fingerprint(CORPUS)


async def test_ablation_study_measures_local_paths_and_marks_unavailable_models():
    report = await run_ablation_study(CORPUS, split="test")
    statuses = {item["ablation"]["name"]: item["status"] for item in report["results"]}
    assert statuses["deterministic_only"] == "measured"
    assert statuses["deterministic_retrieval"] == "measured"
    assert statuses["deterministic_qwen"] == "not_run"
    assert statuses["experimental_gliner"] == "not_run"


async def test_local_only_evaluation_path_makes_no_socket_connection(monkeypatch):
    import socket

    from autocite_mcp.evaluation_framework import run_system_evaluation

    def blocked(*args, **kwargs):
        raise AssertionError("local-only evaluation attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    report = await run_system_evaluation(CORPUS, split="test")
    assert report["metrics"]["local_mode_network_call_count"] == 0
