from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import asdict, dataclass
from typing import Any, Awaitable, Callable, Mapping, Protocol

from .slm import (
    SLMProposal,
    ProposalValidation,
    apply_validated_proposals,
    validate_proposal,
)


DEFAULT_MODEL = "Qwen/Qwen3.5-0.8B"


@dataclass(frozen=True)
class CitationTask:
    citation_text: str
    citation_start: int
    citation_end: int
    source_type: str
    mode: str
    context: str
    context_start: int
    deterministic_issues: tuple[dict[str, Any], ...]
    components: dict[str, Any]


class SLMRuntime(Protocol):
    async def generate(self, prompt: str) -> str: ...


class CallableSLMRuntime:
    """Small adapter for tests and custom local inference functions."""

    def __init__(self, function: Callable[[str], str | Awaitable[str]]) -> None:
        self.function = function

    async def generate(self, prompt: str) -> str:
        value = self.function(prompt)
        if inspect.isawaitable(value):
            value = await value
        if not isinstance(value, str):
            raise TypeError("SLM runtime must return a string")
        return value


class TransformersSLMRuntime:
    """Lazy, optional Transformers adapter for Qwen3.5 text-only inference."""

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL,
        *,
        max_new_tokens: int = 512,
    ) -> None:
        self.model_path = model_path
        self.max_new_tokens = max_new_tokens
        self._model: Any = None
        self._processor: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ImportError as exc:
            raise RuntimeError(
                "Local SLM inference requires the optional 'slm' dependencies"
            ) from exc
        self._processor = AutoProcessor.from_pretrained(self.model_path)
        self._model = AutoModelForImageTextToText.from_pretrained(
            self.model_path,
            torch_dtype="auto",
            device_map="auto",
        )

    def _generate_sync(self, prompt: str) -> str:
        self._load()
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        rendered = self._processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self._processor(text=[rendered], return_tensors="pt")
        device = next(self._model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        generated = self._model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
        )
        prompt_length = inputs["input_ids"].shape[1]
        return self._processor.batch_decode(
            generated[:, prompt_length:],
            skip_special_tokens=True,
        )[0].strip()

    async def generate(self, prompt: str) -> str:
        return await asyncio.to_thread(self._generate_sync, prompt)


def build_slm_tasks(
    text: str,
    mode: str,
    deterministic_result: Mapping[str, Any],
    *,
    context_chars: int = 400,
) -> list[CitationTask]:
    tasks: list[CitationTask] = []
    issues = list(deterministic_result.get("issues") or [])
    for raw in deterministic_result.get("citations") or []:
        start = int(raw["start"])
        end = int(raw["end"])
        context_start = max(0, start - context_chars)
        context_end = min(len(text), end + context_chars)
        overlapping = tuple(
            dict(issue)
            for issue in issues
            if int(issue.get("start", -1)) < end
            and start < int(issue.get("end", -1))
        )
        tasks.append(
            CitationTask(
                citation_text=str(raw["text"]),
                citation_start=start,
                citation_end=end,
                source_type=str(raw["source_type"]),
                mode=mode,
                context=text[context_start:context_end],
                context_start=context_start,
                deterministic_issues=overlapping,
                components=dict(raw.get("components") or {}),
            )
        )
    return tasks


def render_prompt(task: CitationTask) -> str:
    payload = asdict(task)
    schema = {
        "citation_text": "exact citation span",
        "start": "integer document offset",
        "end": "integer document offset",
        "source_type": task.source_type,
        "mode": task.mode,
        "issue_code": "UPPER_SNAKE_CASE",
        "explanation": "brief formatting explanation only",
        "confidence": "low | medium | high",
        "proposed_citation": "string or null",
        "missing_facts": ["fact names"],
        "facts_used": {"fact": "value already present"},
    }
    return (
        "You are AutoCite, a conservative U.S. legal citation reviewer. "
        "Return exactly one JSON object and no markdown. Do not invent parties, numbers, "
        "reporters, pincites, dates, URLs, treatment, or source facts. Use null for the "
        "proposal when required facts are missing. Never claim good-law status, controlling "
        "authority, or proposition support.\n\n"
        f"TASK:\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}\n\n"
        f"OUTPUT SCHEMA:\n{json.dumps(schema, ensure_ascii=False, sort_keys=True)}"
    )


def _proposal_dict(proposal: SLMProposal) -> dict[str, Any]:
    return asdict(proposal)


async def run_hybrid_review(
    text: str,
    *,
    mode: str,
    deterministic_result: Mapping[str, Any],
    runtime: SLMRuntime,
    apply_slm_fixes: bool = False,
    context_chars: int = 400,
) -> dict[str, Any]:
    tasks = build_slm_tasks(
        text,
        mode,
        deterministic_result,
        context_chars=context_chars,
    )
    if not tasks:
        return {
            "status": "no_citations",
            "model": getattr(runtime, "model_path", "custom"),
            "corrected_text": text,
            "suggestions": [],
            "rejected": [],
            "applied": [],
            "applied_count": 0,
            "fallback_reason": None,
        }

    validations: list[ProposalValidation] = []
    rejected: list[dict[str, Any]] = []
    runtime_errors = 0
    for task in tasks:
        try:
            raw = await runtime.generate(render_prompt(task))
        except Exception as exc:
            runtime_errors += 1
            rejected.append(
                {
                    "citation_text": task.citation_text,
                    "start": task.citation_start,
                    "end": task.citation_end,
                    "reasons": ["runtime_error"],
                    "error_type": type(exc).__name__,
                }
            )
            continue
        try:
            proposal = SLMProposal.from_json(raw)
        except ValueError:
            rejected.append(
                {
                    "citation_text": task.citation_text,
                    "start": task.citation_start,
                    "end": task.citation_end,
                    "reasons": ["invalid_model_output"],
                }
            )
            continue
        validation = validate_proposal(
            proposal,
            text,
            expected_mode=mode,
            expected_source_type=task.source_type,
        )
        validations.append(validation)
        if not validation.valid:
            rejected.append(
                {
                    **_proposal_dict(proposal),
                    "reasons": list(validation.reasons),
                }
            )

    valid = [result for result in validations if result.valid]
    application = apply_validated_proposals(text, valid) if apply_slm_fixes else None
    corrected = application.text if application else text
    applied = list(application.applied) if application else []
    suggestions = [
        _proposal_dict(result.proposal)
        for result in valid
        if result.proposal not in applied
    ]
    if valid and rejected:
        status = "partial"
    elif valid:
        status = "completed"
    else:
        status = "fallback"
    fallback_reason = None
    if status == "fallback":
        fallback_reason = "runtime_error" if runtime_errors == len(tasks) else "invalid_model_output"

    return {
        "status": status,
        "model": getattr(runtime, "model_path", "custom"),
        "corrected_text": corrected,
        "suggestions": suggestions,
        "rejected": rejected,
        "applied": [_proposal_dict(proposal) for proposal in applied],
        "applied_count": len(applied),
        "fallback_reason": fallback_reason,
    }
