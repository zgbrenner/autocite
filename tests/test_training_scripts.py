import json
from pathlib import Path

from training.evaluate_slm import evaluate_predictions, run_safety_evaluation
from training.train_sft import MODEL_ID, training_defaults


ROOT = Path(__file__).parents[1]


def test_training_defaults_use_qwen_lora_trackio_and_hub_persistence():
    defaults = training_defaults()
    assert MODEL_ID == "Qwen/Qwen3.5-0.8B"
    assert defaults["lora_r"] == 16
    assert defaults["lora_alpha"] == 32
    assert defaults["seed"] == 42
    assert defaults["report_to"] == ["trackio"]
    assert defaults["push_to_hub"] is True
    source = (ROOT / "training" / "train_sft.py").read_text(encoding="utf-8")
    assert "SFTTrainer" in source
    assert "LoraConfig" in source
    assert "trainer.push_to_hub()" in source


def test_evaluation_reports_required_safety_and_quality_metrics():
    rows = [
        {
            "expected": {
                "start": 4,
                "end": 16,
                "issue_code": "STATUTE_CODE_ABBREVIATION",
                "proposed_citation": "42 U.S.C. § 1983",
            },
            "predicted": {
                "start": 4,
                "end": 16,
                "issue_code": "STATUTE_CODE_ABBREVIATION",
                "proposed_citation": "42 U.S.C. § 1983",
            },
            "valid_json": True,
            "unsupported_facts": False,
            "unsafe_applied": False,
        },
        {
            "expected": {
                "start": 4,
                "end": 20,
                "issue_code": "INSUFFICIENT_INFORMATION",
                "proposed_citation": None,
            },
            "predicted": {
                "start": 4,
                "end": 20,
                "issue_code": "INSUFFICIENT_INFORMATION",
                "proposed_citation": None,
            },
            "valid_json": True,
            "unsupported_facts": False,
            "unsafe_applied": False,
        },
    ]
    metrics = evaluate_predictions(rows)
    required = {
        "valid_json_rate",
        "citation_span_accuracy",
        "issue_classification_macro_f1",
        "exact_correction_accuracy",
        "abstention_precision",
        "abstention_recall",
        "hallucinated_fact_rate",
        "unsafe_auto_apply_rate",
    }
    assert required == set(metrics)
    assert all(value == 1.0 for key, value in metrics.items() if key not in {"hallucinated_fact_rate", "unsafe_auto_apply_rate"})
    assert metrics["hallucinated_fact_rate"] == 0.0
    assert metrics["unsafe_auto_apply_rate"] == 0.0


def test_safety_evaluation_requires_zero_unsafe_acceptances():
    result = run_safety_evaluation(ROOT / "evals" / "slm_safety.jsonl")
    assert result["total"] == 4
    assert result["failed"] == 0
    assert result["unsafe_auto_apply_count"] == 0
    assert json.dumps(result)
