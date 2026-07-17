import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _load_runtime():
    package = types.ModuleType("autocite_mcp")
    package.__path__ = [str(ROOT / "src" / "autocite_mcp")]
    sys.modules["autocite_mcp"] = package
    for name in ("slm", "slm_runtime"):
        path = ROOT / "src" / "autocite_mcp" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"autocite_mcp.{name}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"could not load {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return sys.modules["autocite_mcp.slm_runtime"]


def _deterministic():
    return {
        "citations": [
            {
                "text": "42 USC §1983",
                "start": 4,
                "end": 16,
                "source_type": "statute",
                "components": {"title": "42", "section": "1983"},
            }
        ],
        "issues": [
            {
                "code": "STATUTE_CODE_ABBREVIATION",
                "start": 4,
                "end": 16,
                "original": "42 USC §1983",
            }
        ],
    }


def _response(**overrides):
    payload = {
        "citation_text": "42 USC §1983",
        "start": 4,
        "end": 16,
        "source_type": "statute",
        "mode": "bluepages",
        "issue_code": "STATUTE_CODE_ABBREVIATION",
        "explanation": "Normalize abbreviation and spacing.",
        "confidence": "high",
        "proposed_citation": "42 U.S.C. § 1983",
        "missing_facts": [],
        "facts_used": {"title": "42", "section": "1983"},
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_builds_bounded_tasks_from_deterministic_inventory():
    runtime = _load_runtime()
    text = "A" * 600 + "42 USC §1983" + "B" * 600
    deterministic = {
        "citations": [
            {
                "text": "42 USC §1983",
                "start": 600,
                "end": 612,
                "source_type": "statute",
                "components": {},
            }
        ],
        "issues": [],
    }
    tasks = runtime.build_slm_tasks(text, "bluepages", deterministic, context_chars=120)
    assert len(tasks) == 1
    assert len(tasks[0].context) <= 252
    assert tasks[0].citation_start == 600


def test_published_autocite_adapter_is_the_default_model():
    runtime = _load_runtime()
    assert runtime.DEFAULT_MODEL == "foolish-bandit/AutoCite-0.8B"
    source = (ROOT / "src" / "autocite_mcp" / "slm_runtime.py").read_text(
        encoding="utf-8"
    )
    assert "enable_thinking=False" in source


def test_hybrid_review_accepts_safe_json_and_applies_only_when_enabled():
    runtime = _load_runtime()
    fake = runtime.CallableSLMRuntime(lambda prompt: _response())
    result = asyncio.run(
        runtime.run_hybrid_review(
            "See 42 USC §1983.",
            mode="bluepages",
            deterministic_result=_deterministic(),
            runtime=fake,
            apply_slm_fixes=True,
        )
    )
    assert result["status"] == "completed"
    assert result["corrected_text"] == "See 42 U.S.C. § 1983."
    assert result["applied_count"] == 1


def test_hybrid_review_keeps_valid_proposal_as_suggestion_by_default():
    runtime = _load_runtime()
    fake = runtime.CallableSLMRuntime(lambda prompt: _response())
    result = asyncio.run(
        runtime.run_hybrid_review(
            "See 42 USC §1983.",
            mode="bluepages",
            deterministic_result=_deterministic(),
            runtime=fake,
        )
    )
    assert result["corrected_text"] == "See 42 USC §1983."
    assert result["applied_count"] == 0
    assert len(result["suggestions"]) == 1


def test_invalid_json_becomes_fallback_instead_of_raising():
    runtime = _load_runtime()
    fake = runtime.CallableSLMRuntime(lambda prompt: "not json")
    result = asyncio.run(
        runtime.run_hybrid_review(
            "See 42 USC §1983.",
            mode="bluepages",
            deterministic_result=_deterministic(),
            runtime=fake,
        )
    )
    assert result["status"] == "fallback"
    assert result["corrected_text"] == "See 42 USC §1983."
    assert result["rejected"][0]["reasons"] == ["invalid_model_output"]


def test_runtime_exception_becomes_fallback_instead_of_raising():
    runtime = _load_runtime()

    def broken(prompt):
        raise RuntimeError("model unavailable")

    result = asyncio.run(
        runtime.run_hybrid_review(
            "See 42 USC §1983.",
            mode="bluepages",
            deterministic_result=_deterministic(),
            runtime=runtime.CallableSLMRuntime(broken),
        )
    )
    assert result["status"] == "fallback"
    assert result["fallback_reason"] == "runtime_error"


def test_hallucinated_fact_is_rejected_and_never_applied():
    runtime = _load_runtime()
    fake = runtime.CallableSLMRuntime(
        lambda prompt: _response(proposed_citation="42 U.S.C. § 1983 (2024)")
    )
    result = asyncio.run(
        runtime.run_hybrid_review(
            "See 42 USC §1983.",
            mode="bluepages",
            deterministic_result=_deterministic(),
            runtime=fake,
            apply_slm_fixes=True,
        )
    )
    assert result["corrected_text"] == "See 42 USC §1983."
    assert result["rejected"][0]["reasons"] == ["unsupported_material_facts"]
