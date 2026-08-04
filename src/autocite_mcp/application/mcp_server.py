from __future__ import annotations

import base64
import importlib
import json
import os
from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from .models import DecisionState
from .service import ApplicationService


@lru_cache(maxsize=1)
def get_service() -> ApplicationService:
    return ApplicationService()


def _resolve_existing_server() -> Any | None:
    """Reuse AutoCite's established MCP server when its module is available."""

    for module_name in (
        "autocite_mcp.server",
        "autocite_mcp.mcp",
        "autocite_mcp.tools_server",
    ):
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        for attribute in ("mcp", "server", "app"):
            candidate = getattr(module, attribute, None)
            if candidate is not None and callable(getattr(candidate, "tool", None)):
                return candidate
    return None


def register_application_tools(mcp: Any, service: ApplicationService | None = None) -> Any:
    """Add application tools to a FastMCP-compatible server exactly once."""

    if getattr(mcp, "_autocite_application_tools_registered", False):
        return mcp
    resolved_service = service

    def app_service() -> ApplicationService:
        return resolved_service or get_service()

    @mcp.tool(name="create_document_session")
    def create_document_session(
        title: str,
        text: str,
        source_format: str = "md",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a durable local editing session without altering the source text."""

        session = app_service().create_session(
            title=title,
            text=text,
            source_format=source_format,
            metadata=metadata,
        )
        return {"session": session.to_dict()}

    @mcp.tool(name="import_document_session")
    def import_document_session(path: str) -> dict[str, Any]:
        """Import TXT, Markdown, DOCX, or searchable PDF into canonical Markdown."""

        session = app_service().import_path(path)
        return {"session": session.to_dict()}

    @mcp.tool(name="list_document_sessions")
    def list_document_sessions(limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """List compact recent-session records for a document library or picker."""

        return app_service().list_sessions(limit=limit, offset=offset)

    @mcp.tool(name="get_document_session")
    def get_document_session(
        session_id: str,
        include_text: bool = True,
        include_review: bool = True,
    ) -> dict[str, Any]:
        """Read a session, its current revision, decisions, and optional review data."""

        session = app_service().get_session(session_id)
        if not include_text:
            session.pop("original_text", None)
            session.pop("working_text", None)
        if not include_review:
            session.pop("latest_review", None)
        return {"session": session}

    @mcp.tool(name="update_document_session")
    def update_document_session(
        session_id: str,
        expected_revision: int,
        text: str | None = None,
        title: str | None = None,
        editor_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Autosave an edit with optimistic revision protection."""

        session = app_service().update_session(
            session_id,
            expected_revision=expected_revision,
            text=text,
            title=title,
            editor_state=editor_state,
        )
        return {"session": session.to_dict()}

    @mcp.tool(name="review_document_session")
    async def review_document_session(
        session_id: str,
        expected_revision: int,
        mode: str | None = None,
        jurisdiction: str | None = None,
        deep_review: bool = False,
        use_local_model: bool = False,
    ) -> dict[str, Any]:
        """Review the complete current revision and persist normalized review issues."""

        job = await app_service().review_session(
            session_id,
            expected_revision=expected_revision,
            mode=mode,
            jurisdiction=jurisdiction,
            deep_review=deep_review,
            use_local_model=use_local_model,
        )
        return {"job": job.to_dict()}

    @mcp.tool(name="get_document_review_job")
    def get_document_review_job(job_id: str) -> dict[str, Any]:
        """Read durable review-job progress and its compact result summary."""

        return {"job": app_service().get_review_job(job_id)}

    @mcp.tool(name="decide_document_issue")
    def decide_document_issue(
        session_id: str,
        issue_id: str,
        decision: str,
        expected_revision: int,
        rationale: str | None = None,
    ) -> dict[str, Any]:
        """Accept or reject one issue. Only verified safe-auto-fix edits may apply."""

        return app_service().decide_issue(
            session_id,
            issue_id=issue_id,
            decision=DecisionState(decision),
            expected_revision=expected_revision,
            rationale=rationale,
        )

    @mcp.tool(name="apply_safe_document_issues")
    def apply_safe_document_issues(
        session_id: str,
        issue_ids: list[str],
        expected_revision: int,
        rationale: str | None = None,
    ) -> dict[str, Any]:
        """Apply a nonoverlapping batch of deterministic safe fixes atomically."""

        return app_service().apply_safe_issues(
            session_id,
            issue_ids=issue_ids,
            expected_revision=expected_revision,
            rationale=rationale,
        )

    @mcp.tool(name="preview_document_context_reduction")
    def preview_document_context_reduction(
        session_id: str,
        focus_spans: list[list[int]] | None = None,
        max_characters: int | None = None,
        include_text: bool = False,
    ) -> dict[str, Any]:
        """Measure reversible legal-aware context reduction without changing review input."""

        normalized_spans = None
        if focus_spans:
            normalized_spans = [(int(item[0]), int(item[1])) for item in focus_spans]
        return {
            "reduction": app_service().context_preview(
                session_id,
                focus_spans=normalized_spans,
                max_characters=max_characters,
                include_text=include_text,
            )
        }

    @mcp.tool(name="export_document_session")
    def export_document_session(
        session_id: str,
        output_format: str = "docx",
        destination: str | None = None,
        include_content: bool = False,
    ) -> dict[str, Any]:
        """Export a revision as DOCX, PDF, Markdown, or plain text."""

        artifact = app_service().export_session(
            session_id,
            output_format=output_format,
            destination=destination,
        )
        payload = artifact.summary()
        if include_content and artifact.path is None:
            payload["content_base64"] = base64.b64encode(artifact.content).decode("ascii")
        return {"artifact": payload}

    @mcp.tool(name="delete_document_session")
    def delete_document_session(session_id: str) -> dict[str, Any]:
        """Permanently delete one local application session and its audit state."""

        app_service().store.delete_session(session_id)
        return {"deleted": True, "session_id": session_id}

    try:
        mcp.resource("autocite://sessions/{session_id}")(
            lambda session_id: json.dumps(
                app_service().get_session(session_id), ensure_ascii=False
            )
        )
    except Exception:
        # Some older FastMCP-compatible hosts expose tools but not resources.
        # The get_document_session tool remains the canonical fallback.
        pass

    setattr(mcp, "_autocite_application_tools_registered", True)
    return mcp


mcp = register_application_tools(
    _resolve_existing_server() or FastMCP("AutoCite", instructions="Local legal citation review")
)


def main() -> None:
    transport = os.environ.get("AUTOCITE_TRANSPORT", "stdio").strip().lower()
    if transport in {"http", "streamable_http", "streamable-http"}:
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
