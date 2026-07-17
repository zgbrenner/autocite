from __future__ import annotations

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
from .proposal_models import (
    DEFAULT_ADAPTER_ID,
    LocalQwenProposalModel,
    ModelRuntimeConfig,
)
from .rules import RULE_CATALOG


DEFAULT_MODEL = DEFAULT_ADAPTER_ID
KNOWN_PROPOSAL_CODES = set(RULE_CATALOG) | {"INSUFFICIENT_INFORMATION", "NO_CHANGE"}


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
    retrieved_rule_chunks: tuple[dict[str, Any], ...] = ()


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


class TransformersSLMRuntime(LocalQwenProposalModel):
    """Backward-compatible name for the local Qwen proposal model."""

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL,
        *,
        max_new_tokens: int = 512,
        base_model_id: str = "Qwen/Qwen3.5-0.8B",
        local_model_directory: str | None = None,
        device: str = "auto",
        quantization: str = "none",
        offline_only: bool = True,
        max_context_length: int = 4096,
        timeout_seconds: float = 60.0,
        seed: int = 42,
    ) -> None:
        super().__init__(
            ModelRuntimeConfig(
                enabled=True,
                adapter_id=model_path,
                base_model_id=base_model_id,
                local_model_directory=local_model_directory,
                device=device,
                quantization=quantization,
                offline_only=offline_only,
                max_context_length=max_context_length,
                max_generated_tokens=max_new_tokens,
                timeout_seconds=timeout_seconds,
                seed=seed,
            )
        )


def build_slm_tasks(
    text: str,
    mode: str,
    deterministic_result: Mapping[str, Any],
    *,
    context_chars: int = 400,
    retrieved_rule_chunks: tuple[dict[str, Any], ...] = (),
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
                retrieved_rule_chunks=retrieved_rule_chunks,
            )
        )
    return tasks


def render_prompt(task: CitationTask) -> str:
    system_prompt = (
        "You are AutoCite, a conservative U.S. legal citation reviewer. Return exactly "
        "one JSON object. Do not invent parties, numbers, reporters, pincites, dates, URLs, "
        "treatment, or source facts. Use null when required facts are missing. Never claim "
        "good-law status, controlling weight, precedential value, or proposition support."
    )
    payload = {
        "document": task.context,
        "citation_text": task.citation_text,
        "start": task.citation_start,
        "end": task.citation_end,
        "source_type": task.source_type,
        "mode": task.mode,
        "retrieved_rule_chunks": list(task.retrieved_rule_chunks),
        "permitted_rule_chunk_ids": [
            item.get("chunk_id")
            for item in task.retrieved_rule_chunks
            if item.get("chunk_id")
        ],
    }
    return json.dumps(
        {"system_prompt": system_prompt, "task": payload},
        ensure_ascii=False,
        sort_keys=True,
    )


def _proposal_dict(proposal: SLMProposal) -> dict[str, Any]:
    return asdict(proposal)


def _matches_deterministic_suggestion(issue: Mapping[str, Any], proposal: SLMProposal) -> bool:
    suggestion = issue.get("suggestion")
    if not isinstance(suggestion, str) or proposal.proposed_citation is None:
        return False
    if suggestion == proposal.proposed_citation:
        return True
    trailing = str(issue.get("original", ""))[len(proposal.citation_text) :]
    return bool(trailing) and suggestion == proposal.proposed_citation + trailing


async def run_hybrid_review(
    text: str,
    *,
    mode: str,
    deterministic_result: Mapping[str, Any],
    runtime: SLMRuntime,
    apply_slm_fixes: bool = False,
    context_chars: int = 400,
    retrieved_rule_chunks: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    tasks = build_slm_tasks(
        text,
        mode,
        deterministic_result,
        context_chars=context_chars,
        retrieved_rule_chunks=retrieved_rule_chunks,
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
    automatic_validations: list[ProposalValidation] = []
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
            expected_start=task.citation_start,
            expected_end=task.citation_end,
            known_issue_codes=KNOWN_PROPOSAL_CODES,
            deterministic_issues=task.deterministic_issues,
            supplied_rule_chunk_ids={
                str(item["chunk_id"])
                for item in task.retrieved_rule_chunks
                if item.get("chunk_id")
            },
        )
        validations.append(validation)
        if validation.valid and any(
            issue.get("code") == proposal.issue_code
            and _matches_deterministic_suggestion(issue, proposal)
            and issue.get("confidence") == "high"
            and RULE_CATALOG.get(proposal.issue_code, {}).get("autofix") is True
            for issue in task.deterministic_issues
        ):
            automatic_validations.append(validation)
        if not validation.valid:
            rejected.append(
                {
                    **_proposal_dict(proposal),
                    "reasons": list(validation.reasons),
                }
            )

    valid = [result for result in validations if result.valid]
    application = (
        apply_validated_proposals(text, automatic_validations)
        if apply_slm_fixes
        else None
    )
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
