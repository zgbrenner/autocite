from __future__ import annotations

import asyncio
import dataclasses
import importlib
import inspect
import json
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable


class ReviewEngineUnavailable(RuntimeError):
    pass


@runtime_checkable
class ReviewEngine(Protocol):
    async def review(
        self,
        text: str,
        *,
        mode: str | None = None,
        jurisdiction: str | None = None,
        deep_review: bool = False,
        use_local_model: bool = False,
    ) -> dict[str, Any]: ...


class CallableReviewEngine:
    """Adapter used by tests and embedders with an explicit review callable."""

    def __init__(self, callback: Callable[..., Any] | Callable[..., Awaitable[Any]]) -> None:
        self.callback = callback

    async def review(
        self,
        text: str,
        *,
        mode: str | None = None,
        jurisdiction: str | None = None,
        deep_review: bool = False,
        use_local_model: bool = False,
    ) -> dict[str, Any]:
        result = _invoke_compatible(
            self.callback,
            text,
            mode=mode,
            jurisdiction=jurisdiction,
            deep_review=deep_review,
            use_local_model=use_local_model,
        )
        if inspect.isawaitable(result):
            result = await result
        return _json_safe_mapping(result)


class AutoCiteReviewEngine:
    """Late-bound adapter for AutoCite's deterministic review implementation.

    AutoCite has intentionally evolved its internal module layout without
    making those implementation functions a public API.  The application
    backend therefore resolves a small set of known review entry points at
    first use, validates their signatures, and keeps the selected callable for
    later requests.  A build fails clearly rather than silently substituting a
    different analysis path.
    """

    _CANDIDATES: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "autocite_mcp.review",
            ("review_document", "review_text", "run_review", "review"),
        ),
        (
            "autocite_mcp.review_document",
            ("review_document", "review_text", "run_review"),
        ),
        (
            "autocite_mcp.tools",
            ("review_document", "review_text"),
        ),
        (
            "autocite_mcp.server",
            ("review_document", "review_text"),
        ),
        (
            "autocite_mcp.core",
            ("review_document", "review_text", "review"),
        ),
    )

    def __init__(self) -> None:
        self._resolved: Callable[..., Any] | None = None
        self._resolution_error: str | None = None

    def _resolve(self) -> Callable[..., Any]:
        if self._resolved is not None:
            return self._resolved
        failures: list[str] = []
        for module_name, names in self._CANDIDATES:
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:  # pragma: no cover - installation dependent
                failures.append(f"{module_name}: {type(exc).__name__}")
                continue
            for name in names:
                candidate = getattr(module, name, None)
                if callable(candidate) and _accepts_document_input(candidate):
                    self._resolved = candidate
                    return candidate
            failures.append(f"{module_name}: no compatible review callable")

        self._resolution_error = "; ".join(failures)
        raise ReviewEngineUnavailable(
            "Could not resolve AutoCite's review entry point. "
            f"Attempted: {self._resolution_error}"
        )

    async def review(
        self,
        text: str,
        *,
        mode: str | None = None,
        jurisdiction: str | None = None,
        deep_review: bool = False,
        use_local_model: bool = False,
    ) -> dict[str, Any]:
        callback = self._resolve()
        result = _invoke_compatible(
            callback,
            text,
            mode=mode,
            jurisdiction=jurisdiction,
            deep_review=deep_review,
            use_local_model=use_local_model,
        )
        if inspect.isawaitable(result):
            result = await result
        return _json_safe_mapping(result)


def _accepts_document_input(callback: Callable[..., Any]) -> bool:
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        return True
    names = set(signature.parameters)
    if names & {"text", "document", "content", "document_text", "input_text"}:
        return True
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind
        in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
    ]
    return bool(positional)


def _invoke_compatible(
    callback: Callable[..., Any],
    text: str,
    *,
    mode: str | None,
    jurisdiction: str | None,
    deep_review: bool,
    use_local_model: bool,
) -> Any:
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        return callback(text)

    parameters = signature.parameters
    kwargs: dict[str, Any] = {}
    text_key = next(
        (
            key
            for key in ("text", "document_text", "document", "content", "input_text")
            if key in parameters
        ),
        None,
    )
    if text_key is not None:
        kwargs[text_key] = text
    if mode is not None and "mode" in parameters:
        kwargs["mode"] = mode
    if jurisdiction is not None and "jurisdiction" in parameters:
        kwargs["jurisdiction"] = jurisdiction
    if "deep_review" in parameters:
        kwargs["deep_review"] = deep_review
    if "use_local_model" in parameters:
        kwargs["use_local_model"] = use_local_model
    elif "use_slm" in parameters:
        kwargs["use_slm"] = use_local_model

    if text_key is not None:
        return callback(**kwargs)
    return callback(text, **kwargs)


def _json_safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return json.loads(json.dumps(value, default=_json_default))
    if dataclasses.is_dataclass(value):
        return json.loads(json.dumps(dataclasses.asdict(value), default=_json_default))
    for method_name in ("model_dump", "dict", "to_dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            result = method()
            if isinstance(result, dict):
                return json.loads(json.dumps(result, default=_json_default))
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {"text": value}
        if isinstance(decoded, dict):
            return decoded
        return {"result": decoded}
    return {"result": json.loads(json.dumps(value, default=_json_default))}


def _json_default(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, (set, tuple)):
        return list(value)
    return str(value)


def run_review_sync(engine: ReviewEngine, text: str, **kwargs: Any) -> dict[str, Any]:
    """Small synchronous bridge for worker threads and compatibility callers."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(engine.review(text, **kwargs))
    raise RuntimeError("run_review_sync cannot be used from a running event loop")
