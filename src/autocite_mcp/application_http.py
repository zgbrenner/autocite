from __future__ import annotations

import asyncio
import base64
import binascii
import os
import sys
import threading
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .application_service import AutoCiteApplicationService
from .application_sessions import (
    DocumentSessionStore,
    SessionConflictError,
    SessionNotFoundError,
)
from .documents import MAX_DOCUMENT_BYTES, DocumentLoadError, load_document_bytes


Handler = Callable[[Request], Awaitable[Response]]
_APPLICATION_SERVICE: AutoCiteApplicationService | None = None
_APPLICATION_SERVICE_LOCK = threading.Lock()
_REVIEW_OPTIONS = {
    "deep_review",
    "include_source_text",
    "use_slm",
    "use_local_model",
    "model_path",
    "base_model_id",
    "local_model_directory",
    "model_device",
    "model_quantization",
    "model_offline_only",
    "model_max_context_length",
    "model_max_generated_tokens",
    "model_timeout_seconds",
    "model_seed",
    "use_rule_retrieval",
    "retrieval_top_k",
    "slm_only",
    "apply_slm_fixes",
}


def default_session_database_path() -> Path:
    configured = os.getenv("AUTOCITE_SESSION_DB")
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        base = Path(
            os.getenv("LOCALAPPDATA")
            or os.getenv("APPDATA")
            or Path.home() / "AppData" / "Local"
        )
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(
            os.getenv("XDG_DATA_HOME")
            or Path.home() / ".local" / "share"
        )
    return base / "AutoCite" / "sessions.sqlite3"


def configure_application_service(
    service: AutoCiteApplicationService | None,
) -> None:
    global _APPLICATION_SERVICE
    with _APPLICATION_SERVICE_LOCK:
        _APPLICATION_SERVICE = service


def get_application_service() -> AutoCiteApplicationService:
    global _APPLICATION_SERVICE
    with _APPLICATION_SERVICE_LOCK:
        if _APPLICATION_SERVICE is None:
            _APPLICATION_SERVICE = AutoCiteApplicationService(
                DocumentSessionStore(default_session_database_path())
            )
        return _APPLICATION_SERVICE


def _json_error(error: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        {"error": error, "message": message},
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )


def guarded(handler: Handler) -> Handler:
    async def wrapped(request: Request) -> Response:
        try:
            return await handler(request)
        except SessionNotFoundError as exc:
            return _json_error("not_found", str(exc), 404)
        except SessionConflictError as exc:
            return _json_error("revision_conflict", str(exc), 409)
        except DocumentLoadError as exc:
            return _json_error(exc.code, str(exc), 400)
        except (ValueError, TypeError, KeyError, binascii.Error) as exc:
            return _json_error("invalid_request", str(exc), 400)
        except Exception:
            return _json_error(
                "application_error",
                "AutoCite could not complete the local application request.",
                500,
            )

    return wrapped


async def _payload(request: Request) -> dict[str, Any]:
    try:
        value = await request.json()
    except Exception as exc:
        raise ValueError("request body must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("request body must be a JSON object")
    return value


def _integer_query(request: Request, name: str, default: int) -> int:
    raw = request.query_params.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@guarded
async def application_health(request: Request) -> Response:
    return JSONResponse(
        {
            "status": "ok",
            "service": "autocite-application",
            "schema_version": "1.0",
            "documents_endpoint": "/app/documents",
            "import_endpoint": "/app/import",
            "mcp_endpoint": "/mcp",
            "local_first": True,
        },
        headers={"Cache-Control": "no-store"},
    )


@guarded
async def documents_collection(request: Request) -> Response:
    service = get_application_service()
    if request.method == "GET":
        result = service.list_documents(
            limit=_integer_query(request, "limit", 50),
            cursor=request.query_params.get("cursor"),
        )
        return JSONResponse(result)
    payload = await _payload(request)
    text = payload.get("text", "")
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    created = service.create_document(
        title=str(payload.get("title") or "Untitled document"),
        text=text,
        source_format=str(payload.get("source_format") or "markdown"),
        file_name=(
            str(payload["file_name"])
            if payload.get("file_name") is not None
            else None
        ),
        mime_type=(
            str(payload["mime_type"])
            if payload.get("mime_type") is not None
            else None
        ),
        mode=str(payload.get("mode") or "auto"),
        jurisdiction=(
            str(payload["jurisdiction"])
            if payload.get("jurisdiction") is not None
            else None
        ),
        document_type=str(payload.get("document_type") or "auto"),
    )
    return JSONResponse({"document": created.summary()}, status_code=201)


@guarded
async def import_document(request: Request) -> Response:
    payload = await _payload(request)
    encoded = payload.get("data_base64")
    if not isinstance(encoded, str) or not encoded:
        raise ValueError("data_base64 must be a non-empty base64 string")
    if len(encoded) > (MAX_DOCUMENT_BYTES * 4) // 3 + 8:
        raise DocumentLoadError(
            "document_too_large",
            f"Documents are limited to {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB.",
        )
    try:
        source_bytes = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("data_base64 must contain valid base64") from exc
    file_name = str(payload.get("file_name") or "document.txt")
    mime_type = (
        str(payload["mime_type"])
        if payload.get("mime_type") is not None
        else None
    )
    loaded = await asyncio.to_thread(
        load_document_bytes,
        source_bytes,
        file_name,
        mime_type,
    )
    title = str(
        payload.get("title")
        or Path(loaded.filename).stem
        or "Untitled document"
    )
    created = get_application_service().create_document(
        title=title,
        text=loaded.text,
        source_format=loaded.source_format,
        file_name=loaded.filename,
        mime_type=loaded.mime_type,
        mode=str(payload.get("mode") or "auto"),
        jurisdiction=(
            str(payload["jurisdiction"])
            if payload.get("jurisdiction") is not None
            else None
        ),
        document_type=str(payload.get("document_type") or "auto"),
        source_bytes=source_bytes,
    )
    return JSONResponse(
        {
            "document": created.summary(),
            "warnings": list(loaded.warnings),
        },
        status_code=201,
    )


@guarded
async def document_item(request: Request) -> Response:
    service = get_application_service()
    session_id = request.path_params["session_id"]
    if request.method == "GET":
        include_review = request.query_params.get(
            "include_review", ""
        ).casefold() in {"1", "true", "yes"}
        return JSONResponse(
            {
                "document": service.get_document(
                    session_id,
                    include_text=True,
                    include_review=include_review,
                )
            }
        )
    payload = await _payload(request)
    text = payload.get("text")
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    expected_revision = payload.get("expected_revision")
    if not isinstance(expected_revision, int):
        raise ValueError("expected_revision must be an integer")
    updated = service.update_document(
        session_id,
        text=text,
        expected_revision=expected_revision,
        title=(
            str(payload["title"])
            if payload.get("title") is not None
            else None
        ),
        mode=(
            str(payload["mode"])
            if payload.get("mode") is not None
            else None
        ),
        jurisdiction=(
            str(payload["jurisdiction"])
            if payload.get("jurisdiction") is not None
            else None
        ),
        document_type=(
            str(payload["document_type"])
            if payload.get("document_type") is not None
            else None
        ),
    )
    return JSONResponse({"document": updated.summary()})


@guarded
async def document_review(request: Request) -> Response:
    service = get_application_service()
    session_id = request.path_params["session_id"]
    if request.method == "GET":
        return JSONResponse(
            service.get_review_items(
                session_id,
                offset=_integer_query(request, "offset", 0),
                limit=_integer_query(request, "limit", 100),
            )
        )
    payload = await _payload(request)
    unknown = set(payload) - _REVIEW_OPTIONS
    if unknown:
        raise ValueError(
            f"unsupported review option: {sorted(unknown)[0]}"
        )
    return JSONResponse(await service.review_document(session_id, **payload))


@guarded
async def document_decision(request: Request) -> Response:
    payload = await _payload(request)
    item_id = payload.get("item_id")
    decision = payload.get("decision")
    expected_revision = payload.get("expected_revision")
    if not isinstance(item_id, str) or not item_id:
        raise ValueError("item_id must be a non-empty string")
    if not isinstance(decision, str):
        raise ValueError("decision must be a string")
    if not isinstance(expected_revision, int):
        raise ValueError("expected_revision must be an integer")
    item = get_application_service().set_review_item_decision(
        request.path_params["session_id"],
        item_id=item_id,
        decision=decision,
        expected_revision=expected_revision,
    )
    return JSONResponse({"item": item})


@guarded
async def document_export(request: Request) -> Response:
    payload = await _payload(request)
    export_format = payload.get("format")
    if not isinstance(export_format, str):
        raise ValueError("format must be a string")
    tracked = payload.get("tracked", True)
    if not isinstance(tracked, bool):
        raise ValueError("tracked must be a boolean")
    result = get_application_service().export_document(
        request.path_params["session_id"],
        export_format=export_format,
        tracked=tracked,
    )
    return JSONResponse(result)


@guarded
async def review_job(request: Request) -> Response:
    job = get_application_service().store.get_review_job(
        request.path_params["job_id"]
    )
    return JSONResponse({"job": job.as_dict()})


def build_application_http_app(mcp_app: Any) -> Starlette:
    """Mount the local application API alongside the existing MCP app."""
    # Starlette's lifespan protocol is only handled by the outermost app;
    # Mount does not forward it to sub-applications. mcp_app's own lifespan
    # starts the StreamableHTTPSessionManager's task group, so without
    # forwarding it here every /mcp request fails with "Task group is not
    # initialized" as soon as it reaches the mounted app.
    return Starlette(
        lifespan=mcp_app.router.lifespan_context,
        routes=[
            Route("/app/health", application_health, methods=["GET"]),
            Route("/app/import", import_document, methods=["POST"]),
            Route(
                "/app/documents",
                documents_collection,
                methods=["GET", "POST"],
            ),
            Route(
                "/app/documents/{session_id:str}",
                document_item,
                methods=["GET", "PATCH"],
            ),
            Route(
                "/app/documents/{session_id:str}/review",
                document_review,
                methods=["GET", "POST"],
            ),
            Route(
                "/app/documents/{session_id:str}/decisions",
                document_decision,
                methods=["POST"],
            ),
            Route(
                "/app/documents/{session_id:str}/export",
                document_export,
                methods=["POST"],
            ),
            Route("/app/jobs/{job_id:str}", review_job, methods=["GET"]),
            Mount("/", app=mcp_app),
        ]
    )
