import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "src" / "autocite_mcp" / "proposal_models.py"


def _load_models():
    spec = importlib.util.spec_from_file_location("autocite_proposal_models", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load proposal_models module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runtime_config_is_disabled_and_offline_by_default():
    models = _load_models()
    config = models.ModelRuntimeConfig()
    assert config.enabled is False
    assert config.offline_only is True
    assert config.adapter_id == "foolish-bandit/AutoCite-0.8B"
    assert config.base_model_id == "Qwen/Qwen3.5-0.8B"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("device", "quantum"),
        ("quantization", "3bit"),
        ("max_context_length", 0),
        ("max_generated_tokens", 0),
        ("timeout_seconds", 0),
    ],
)
def test_runtime_config_rejects_unsafe_values(field, value):
    models = _load_models()
    with pytest.raises(ValueError):
        models.ModelRuntimeConfig(**{field: value})


def test_disabled_model_never_loads_ml_dependencies():
    models = _load_models()
    before = set(sys.modules)
    model = models.DisabledProposalModel()
    assert asyncio.run(model.generate("prompt")) is None
    added = set(sys.modules) - before
    assert "transformers" not in added
    assert "torch" not in added


def test_local_model_loads_lazily_and_passes_offline_configuration():
    models = _load_models()
    calls = []

    def loader(config):
        calls.append(config)
        return object(), object()

    model = models.LocalQwenProposalModel(
        models.ModelRuntimeConfig(enabled=True, local_model_directory="/models/autocite"),
        loader=loader,
        generator=lambda model, processor, prompt, config: '{"ok":true}',
    )
    assert calls == []
    assert asyncio.run(model.generate("prompt")) == '{"ok":true}'
    assert calls[0].offline_only is True
    assert len(calls) == 1


def test_local_model_timeout_is_reported_without_crashing_process():
    models = _load_models()

    def slow(model, processor, prompt, config):
        import time

        time.sleep(0.05)
        return "late"

    model = models.LocalQwenProposalModel(
        models.ModelRuntimeConfig(enabled=True, timeout_seconds=0.001),
        loader=lambda config: (object(), object()),
        generator=slow,
    )
    with pytest.raises(TimeoutError, match="timed out"):
        asyncio.run(model.generate("prompt"))

