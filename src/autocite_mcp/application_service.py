from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from .application_sessions import DocumentSession, DocumentSessionStore
from .review_session import ReviewDecision, ReviewSession


Reviewer = Callable[..., Awaitable[dict[str, Any]]]
DocxExporter = Callable[..., dict[str, Any]]


class AutoCiteApplicationService:
    """Canonical local application service shared by MCP and desktop clients."""

    def __init__(
        self,
        store: DocumentSessionStore,
        *,
        reviewer: Reviewer | None = None,
        docx_exporter: DocxExporter | None = None,
    ) -> None:
        self.store = store
        self._reviewer = reviewer
        self._docx_exporter = docx_exporter

    def create_document(
        self,
        *,
        title: str,
        text: str,
        source_format: str,
        file_name: str | None = None,
        mime_type: str | None = None,
        mode: str = "auto",
        jurisdiction: str | None = None,
        document_type: str = "auto",
        source_bytes: bytes | None = None,
    ) -> DocumentSession:
        return self.store.create_document(
            title=title,
            text=text,
            source_format=source_format,
            file_name=file_name,
            mime_type=mime_type,
            mode=mode,
            jurisdiction=jurisdiction,
            document_type=document_type,
            source_bytes=source_bytes,
        )

    def update_document(
        self,
        session_id: str,
        *,
        text: str,
        expected_revision: int,
        title: str | None = None,
        mode: str | None = None,
        jurisdiction: str | None = None,
        document_type: str | None = None,
    ) -> DocumentSession:
        return self.store.update_document(
            session_id,
            text=text,
            expected_revision=expected_revision,
            title=title,
            mode=mode,
            jurisdiction=jurisdiction,
            document_type=document_type,
        )

    def get_document(
        self,
        session_id: str,
        *,
        include_text: bool = True,
        include_review: bool = False,
    ) -> dict[str, Any]:
        return self.store.get_document(session_id).as_dict(
            include_text=include_text,
            include_review=include_review,
        )

    def list_documents(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return self.store.list_documents(limit=limit, cursor=cursor).as_dict()

    @staticmethod
    def _decisions_from_payload(
        payload: Mapping[str, Any] | None,
    ) -> dict[str, str]:
        if payload is None:
            return {}
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            return {}
        decisions: dict[str, str] = {}
        for raw in raw_items:
            if not isinstance(raw, Mapping):
                continue
            item_id = raw.get("item_id")
            decision = raw.get("decision")
            if isinstance(item_id, str) and isinstance(decision, str):
                decisions[item_id] = decision
        return decisions

    def _review_session(
        self,
        document: DocumentSession,
    ) -> ReviewSession | None:
        if document.review_result is None:
            return None
        session = ReviewSession.from_result(document.review_result)
        decisions = self._decisions_from_payload(document.review_session)
        if decisions:
            known = {item.item_id for item in session.items}
            session = session.with_decisions(
                {key: value for key, value in decisions.items() if key in known}
            )
        return session

    async def review_document(
        self,
        session_id: str,
        **options: Any,
    ) -> dict[str, Any]:
        document = self.store.get_document(session_id)
        job = self.store.create_review_job(
            session_id,
            document_revision=document.revision,
            options=options,
        )
        self.store.update_review_job(job.job_id, status="running")
        arguments: dict[str, Any] = {
            "document_type": document.document_type,
            "mode": document.mode,
            "jurisdiction": document.jurisdiction,
            "apply_safe_fixes": True,
            **options,
        }
        if arguments["jurisdiction"] is None:
            arguments.pop("jurisdiction")
        try:
            reviewer = self._reviewer
            if reviewer is None:
                from .tools import review_document as reviewer
            result = await reviewer(document.text, **arguments)
            result_original = result.get("original_text")
            if result_original is not None and str(result_original) != document.text:
                raise ValueError(
                    "review result does not match the document revision"
                )
            review_session = ReviewSession.from_result(result)
            saved = self.store.save_review(
                session_id,
                review_result=result,
                review_session=review_session.as_dict(),
                expected_revision=document.revision,
            )
            accepted = sum(
                item.decision is ReviewDecision.ACCEPTED
                for item in review_session.items
            )
            summary = {
                "item_count": len(review_session.items),
                "accepted_count": accepted,
                "pending_count": sum(
                    item.decision is ReviewDecision.PENDING
                    for item in review_session.items
                ),
                "rejected_count": sum(
                    item.decision is ReviewDecision.REJECTED
                    for item in review_session.items
                ),
                "citation_count": len(result.get("citation_inventory", [])),
            }
            completed = self.store.update_review_job(
                job.job_id,
                status="completed",
                result_summary=summary,
            )
            return {
                "document": saved.summary(),
                "job": completed.as_dict(),
                "summary": summary,
            }
        except Exception as exc:
            self.store.update_review_job(
                job.job_id,
                status="failed",
                error=str(exc),
            )
            raise

    def get_review_items(
        self,
        session_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        if offset < 0:
            raise ValueError("offset must not be negative")
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        document = self.store.get_document(session_id)
        session = self._review_session(document)
        items = list(session.items) if session is not None else []
        visible = items[offset : offset + limit]
        next_offset = offset + len(visible)
        return {
            "session_id": session_id,
            "document_revision": document.revision,
            "review_revision": document.review_revision,
            "items": [item.as_dict() for item in visible],
            "offset": offset,
            "limit": limit,
            "total": len(items),
            "next_offset": (
                next_offset if next_offset < len(items) else None
            ),
        }

    def set_review_item_decision(
        self,
        session_id: str,
        *,
        item_id: str,
        decision: ReviewDecision | str,
        expected_revision: int,
    ) -> dict[str, Any]:
        document = self.store.get_document(session_id)
        session = self._review_session(document)
        if session is None:
            raise ValueError("document has no current review")
        normalized = (
            decision
            if isinstance(decision, ReviewDecision)
            else ReviewDecision(str(decision))
        )
        if normalized is ReviewDecision.ACCEPTED:
            changed = session.accept(item_id)
        elif normalized is ReviewDecision.REJECTED:
            changed = session.reject(item_id)
        else:
            changed = session.reset(item_id)
        self.store.save_review_session(
            session_id,
            review_session=changed.as_dict(),
            expected_revision=expected_revision,
        )
        return next(
            item.as_dict() for item in changed.items if item.item_id == item_id
        )

    def get_effective_text(self, session_id: str) -> str:
        document = self.store.get_document(session_id)
        session = self._review_session(document)
        if session is None:
            return document.text
        return session.export_plan().apply_to_text(document.text)

    @staticmethod
    def _safe_stem(document: DocumentSession) -> str:
        source = document.file_name or document.title or "autocite-document"
        stem = source.rsplit(".", 1)[0]
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._")
        return cleaned or "autocite-document"

    def export_document(
        self,
        session_id: str,
        *,
        export_format: str,
        tracked: bool = True,
    ) -> dict[str, Any]:
        document = self.store.get_document(session_id)
        effective_text = self.get_effective_text(session_id)
        normalized = export_format.strip().casefold().lstrip(".")
        stem = self._safe_stem(document)
        if normalized in {"txt", "text"}:
            payload = effective_text.encode("utf-8")
            filename = f"{stem}.txt"
            mime_type = "text/plain; charset=utf-8"
        elif normalized in {"md", "markdown"}:
            payload = effective_text.encode("utf-8")
            filename = f"{stem}.md"
            mime_type = "text/markdown; charset=utf-8"
        elif normalized == "pdf":
            from .pdf_export import build_text_pdf

            payload = build_text_pdf(effective_text, title=document.title)
            filename = f"{stem}-reviewed.pdf"
            mime_type = "application/pdf"
        elif normalized == "docx":
            exporter = self._docx_exporter
            if exporter is None:
                from .tools import export_review_docx as exporter
            return exporter(
                document.text,
                effective_text,
                tracked=tracked,
                filename=f"{stem}-reviewed.docx",
            )
        else:
            raise ValueError(
                "export_format must be one of txt, md, markdown, pdf, or docx"
            )
        return {
            "filename": filename,
            "mime_type": mime_type,
            "data_base64": base64.b64encode(payload).decode("ascii"),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "document_revision": document.revision,
            "review_revision": document.review_revision,
        }
