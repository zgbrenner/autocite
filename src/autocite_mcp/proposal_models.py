from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol


DEFAULT_ADAPTER_ID = "foolish-bandit/AutoCite-0.8B"
DEFAULT_BASE_MODEL_ID = "Qwen/Qwen3.5-0.8B"


class CitationProposalModel(Protocol):
    """Dependency-light interface for optional, local proposal generation."""

    async def generate(self, prompt: str) -> str | None: ...


@dataclass(frozen=True)
class ModelRuntimeConfig:
    enabled: bool = False
    adapter_id: str = DEFAULT_ADAPTER_ID
    base_model_id: str = DEFAULT_BASE_MODEL_ID
    local_model_directory: str | None = None
    device: str = "auto"
    quantization: str = "none"
    offline_only: bool = True
    max_context_length: int = 4096
    max_generated_tokens: int = 512
    timeout_seconds: float = 60.0
    seed: int = 42

    def __post_init__(self) -> None:
        if self.device not in {"auto", "cpu", "cuda", "mps"}:
            raise ValueError("device must be auto, cpu, cuda, or mps")
        if self.quantization not in {"none", "4bit", "8bit"}:
            raise ValueError("quantization must be none, 4bit, or 8bit")
        if self.quantization != "none" and self.device in {"cpu", "mps"}:
            raise ValueError("4-bit and 8-bit modes require a CUDA-capable device")
        if self.max_context_length <= 0:
            raise ValueError("max_context_length must be positive")
        if self.max_generated_tokens <= 0:
            raise ValueError("max_generated_tokens must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.seed < 0:
            raise ValueError("seed must be non-negative")


class DisabledProposalModel:
    """No-op implementation used by deterministic-only installations."""

    model_path = "disabled"

    async def generate(self, prompt: str) -> None:
        return None


Loader = Callable[[ModelRuntimeConfig], tuple[Any, Any]]
Generator = Callable[[Any, Any, str, ModelRuntimeConfig], str]


class LocalQwenProposalModel:
    """Lazy local loader for the Qwen base model plus the AutoCite PEFT adapter."""

    def __init__(
        self,
        config: ModelRuntimeConfig | None = None,
        *,
        loader: Loader | None = None,
        generator: Generator | None = None,
    ) -> None:
        self.config = config or ModelRuntimeConfig(enabled=True)
        if not self.config.enabled:
            raise ValueError("LocalQwenProposalModel requires enabled=True")
        self.model_path = self.config.local_model_directory or self.config.adapter_id
        self._loader = loader or self._load_transformers
        self._generator = generator or self._generate_transformers
        self._model: Any = None
        self._processor: Any = None

    @staticmethod
    def _sources(config: ModelRuntimeConfig) -> tuple[str, str]:
        if not config.local_model_directory:
            return config.base_model_id, config.adapter_id
        root = Path(config.local_model_directory)
        local_base = root / "base"
        local_adapter = root / "adapter"
        if local_base.is_dir() and local_adapter.is_dir():
            return str(local_base), str(local_adapter)
        return config.base_model_id, str(root)

    @classmethod
    def _load_transformers(cls, config: ModelRuntimeConfig) -> tuple[Any, Any]:
        try:
            import torch
            from peft import PeftModel
            from transformers import (
                AutoModelForImageTextToText,
                AutoProcessor,
                BitsAndBytesConfig,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Local Qwen inference requires the optional 'slm' dependencies"
            ) from exc

        torch.manual_seed(config.seed)
        base_source, adapter_source = cls._sources(config)
        load_options: dict[str, Any] = {
            "local_files_only": config.offline_only,
            "torch_dtype": "auto",
        }
        if config.device == "auto":
            load_options["device_map"] = "auto"
        elif config.device == "cuda":
            load_options["device_map"] = {"": "cuda"}
        if config.quantization == "4bit":
            load_options["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True
            )
        elif config.quantization == "8bit":
            load_options["quantization_config"] = BitsAndBytesConfig(
                load_in_8bit=True
            )

        processor = AutoProcessor.from_pretrained(
            base_source,
            local_files_only=config.offline_only,
        )
        base_model = AutoModelForImageTextToText.from_pretrained(
            base_source,
            **load_options,
        )
        model = PeftModel.from_pretrained(
            base_model,
            adapter_source,
            local_files_only=config.offline_only,
        )
        if config.device in {"cpu", "mps"}:
            model = model.to(config.device)
        model.eval()
        return model, processor

    @staticmethod
    def _generate_transformers(
        model: Any,
        processor: Any,
        prompt: str,
        config: ModelRuntimeConfig,
    ) -> str:
        system_prompt: str | None = None
        user_prompt = prompt
        try:
            envelope = json.loads(prompt)
        except (TypeError, ValueError):
            envelope = None
        if isinstance(envelope, dict) and isinstance(envelope.get("task"), dict):
            system_value = envelope.get("system_prompt")
            if isinstance(system_value, str):
                system_prompt = system_value
            user_prompt = json.dumps(
                envelope["task"], ensure_ascii=False, sort_keys=True
            )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
        )
        rendered = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = processor(
            text=[rendered],
            return_tensors="pt",
            truncation=True,
            max_length=config.max_context_length,
        )
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        generated = model.generate(
            **inputs,
            max_new_tokens=config.max_generated_tokens,
            do_sample=False,
        )
        prompt_length = inputs["input_ids"].shape[1]
        return processor.batch_decode(
            generated[:, prompt_length:],
            skip_special_tokens=True,
        )[0].strip()

    def _generate_sync(self, prompt: str) -> str:
        if self._model is None:
            self._model, self._processor = self._loader(self.config)
        value = self._generator(self._model, self._processor, prompt, self.config)
        if not isinstance(value, str):
            raise TypeError("proposal model must return a string")
        return value

    async def generate(self, prompt: str) -> str:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._generate_sync, prompt),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise TimeoutError(
                f"local model generation timed out after {self.config.timeout_seconds}s"
            ) from exc
