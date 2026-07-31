from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


class SessionError(RuntimeError):
    """Base error for durable application-session operations."""


class SessionNotFoundError(SessionError, KeyError):
    """Raised when a document or review job does not exist."""


class SessionConflictError(SessionError):
    """Raised when an optimistic revision check fails."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dump_json(value: Mapping[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _load_json(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    loaded = json.loads(value)
    if not isinstance(loaded, dict):
        raise ValueError("stored session JSON must be an object")
    return loaded


@dataclass(frozen=True, slots=True)
class DocumentSession:
    session_id: str
    title: str
    text: str
    source_format: str
    file_name: str | None
    mime_type: str | None
    mode: str
    jurisdiction: str | None
    document_type: str
    revision: int
    content_sha256: str
    source_bytes: bytes | None
    review_result: dict[str, Any] | None
    review_session: dict[str, Any] | None
    review_revision: int | None
    created_at: str
    updated_at: str

    def as_dict(
        self,
        *,
        include_text: bool = True,
        include_review: bool = True,
        include_source_bytes: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "session_id": self.session_id,
            "title": self.title,
            "source_format": self.source_format,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "mode": self.mode,
            "jurisdiction": self.jurisdiction,
            "document_type": self.document_type,
            "revision": self.revision,
            "content_sha256": self.content_sha256,
            "review_revision": self.review_revision,
            "has_review": self.review_result is not None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_text:
            payload["text"] = self.text
        if include_review:
            payload["review_result"] = self.review_result
            payload["review_session"] = self.review_session
        if include_source_bytes:
            payload["source_bytes_base64"] = (
                base64.b64encode(self.source_bytes).decode("ascii")
                if self.source_bytes is not None
                else None
            )
        return payload

    def summary(self) -> dict[str, Any]:
        return self.as_dict(include_text=False, include_review=False)


@dataclass(frozen=True, slots=True)
class DocumentSessionPage:
    items: tuple[dict[str, Any], ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, Any]:
        return {"items": list(self.items), "next_cursor": self.next_cursor}


@dataclass(frozen=True, slots=True)
class ReviewJob:
    job_id: str
    session_id: str
    document_revision: int
    status: str
    options: dict[str, Any]
    result_summary: dict[str, Any] | None
    error: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class DocumentSessionStore:
    """SQLite-backed local document and review state.

    A connection is opened per operation so the store is safe to use from the
    desktop event loop and worker threads. Source text remains canonical. A text
    edit invalidates review state and clears original package bytes because they
    no longer map safely to the edited text.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS document_sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source_format TEXT NOT NULL,
                    file_name TEXT,
                    mime_type TEXT,
                    mode TEXT NOT NULL,
                    jurisdiction TEXT,
                    document_type TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    source_bytes BLOB,
                    review_result_json TEXT,
                    review_session_json TEXT,
                    review_revision INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_document_sessions_updated
                    ON document_sessions(updated_at DESC, session_id DESC);

                CREATE TABLE IF NOT EXISTS review_jobs (
                    job_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    document_revision INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    result_summary_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY(session_id) REFERENCES document_sessions(session_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_review_jobs_session
                    ON review_jobs(session_id, created_at DESC, job_id DESC);
                """
            )

    @staticmethod
    def _document_from_row(row: sqlite3.Row) -> DocumentSession:
        return DocumentSession(
            session_id=str(row["session_id"]),
            title=str(row["title"]),
            text=str(row["text"]),
            source_format=str(row["source_format"]),
            file_name=row["file_name"],
            mime_type=row["mime_type"],
            mode=str(row["mode"]),
            jurisdiction=row["jurisdiction"],
            document_type=str(row["document_type"]),
            revision=int(row["revision"]),
            content_sha256=str(row["content_sha256"]),
            source_bytes=row["source_bytes"],
            review_result=_load_json(row["review_result_json"]),
            review_session=_load_json(row["review_session_json"]),
            review_revision=(
                int(row["review_revision"])
                if row["review_revision"] is not None
                else None
            ),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> ReviewJob:
        return ReviewJob(
            job_id=str(row["job_id"]),
            session_id=str(row["session_id"]),
            document_revision=int(row["document_revision"]),
            status=str(row["status"]),
            options=_load_json(row["options_json"]) or {},
            result_summary=_load_json(row["result_summary_json"]),
            error=row["error"],
            created_at=str(row["created_at"]),
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )

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
        normalized_title = title.strip() or "Untitled document"
        normalized_format = source_format.strip().casefold() or "text"
        now = _utc_now()
        session_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO document_sessions (
                    session_id, title, text, source_format, file_name, mime_type,
                    mode, jurisdiction, document_type, revision, content_sha256,
                    source_bytes, review_result_json, review_session_json,
                    review_revision, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, NULL, NULL, NULL, ?, ?)
                """,
                (
                    session_id,
                    normalized_title,
                    text,
                    normalized_format,
                    file_name,
                    mime_type,
                    mode,
                    jurisdiction,
                    document_type,
                    _content_sha256(text),
                    source_bytes,
                    now,
                    now,
                ),
            )
        return self.get_document(session_id)

    def get_document(self, session_id: str) -> DocumentSession:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM document_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(
                f"unknown document session: {session_id}"
            )
        return self._document_from_row(row)

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
        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM document_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                connection.execute("ROLLBACK")
                raise SessionNotFoundError(
                    f"unknown document session: {session_id}"
                )
            actual_revision = int(row["revision"])
            if actual_revision != expected_revision:
                connection.execute("ROLLBACK")
                raise SessionConflictError(
                    f"expected revision {expected_revision}, found {actual_revision}"
                )
            connection.execute(
                """
                UPDATE document_sessions
                SET title = ?, text = ?, mode = ?, jurisdiction = ?,
                    document_type = ?, revision = ?, content_sha256 = ?,
                    source_bytes = NULL, review_result_json = NULL,
                    review_session_json = NULL, review_revision = NULL,
                    updated_at = ?
                WHERE session_id = ?
                """,
                (
                    (title.strip() or "Untitled document")
                    if title is not None
                    else row["title"],
                    text,
                    mode if mode is not None else row["mode"],
                    jurisdiction if jurisdiction is not None else row["jurisdiction"],
                    (
                        document_type
                        if document_type is not None
                        else row["document_type"]
                    ),
                    actual_revision + 1,
                    _content_sha256(text),
                    now,
                    session_id,
                ),
            )
            connection.execute("COMMIT")
        return self.get_document(session_id)

    def save_review(
        self,
        session_id: str,
        *,
        review_result: Mapping[str, Any],
        review_session: Mapping[str, Any],
        expected_revision: int,
    ) -> DocumentSession:
        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision FROM document_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                connection.execute("ROLLBACK")
                raise SessionNotFoundError(
                    f"unknown document session: {session_id}"
                )
            actual_revision = int(row["revision"])
            if actual_revision != expected_revision:
                connection.execute("ROLLBACK")
                raise SessionConflictError(
                    f"expected revision {expected_revision}, found {actual_revision}"
                )
            connection.execute(
                """
                UPDATE document_sessions
                SET review_result_json = ?, review_session_json = ?,
                    review_revision = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (
                    _dump_json(dict(review_result)),
                    _dump_json(dict(review_session)),
                    actual_revision,
                    now,
                    session_id,
                ),
            )
            connection.execute("COMMIT")
        return self.get_document(session_id)

    def save_review_session(
        self,
        session_id: str,
        *,
        review_session: Mapping[str, Any],
        expected_revision: int,
    ) -> DocumentSession:
        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT revision, review_result_json
                FROM document_sessions WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if row is None:
                connection.execute("ROLLBACK")
                raise SessionNotFoundError(
                    f"unknown document session: {session_id}"
                )
            actual_revision = int(row["revision"])
            if actual_revision != expected_revision:
                connection.execute("ROLLBACK")
                raise SessionConflictError(
                    f"expected revision {expected_revision}, found {actual_revision}"
                )
            if row["review_result_json"] is None:
                connection.execute("ROLLBACK")
                raise SessionConflictError("document has no current review")
            connection.execute(
                """
                UPDATE document_sessions
                SET review_session_json = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (_dump_json(dict(review_session)), now, session_id),
            )
            connection.execute("COMMIT")
        return self.get_document(session_id)

    @staticmethod
    def _encode_cursor(updated_at: str, session_id: str) -> str:
        raw = json.dumps([updated_at, session_id], separators=(",", ":"))
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[str, str]:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
            value = json.loads(raw)
            if (
                not isinstance(value, list)
                or len(value) != 2
                or not all(isinstance(item, str) for item in value)
            ):
                raise ValueError
            return value[0], value[1]
        except Exception as exc:
            raise ValueError("invalid document-session cursor") from exc

    def list_documents(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> DocumentSessionPage:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        parameters: list[Any] = []
        where = ""
        if cursor is not None:
            updated_at, session_id = self._decode_cursor(cursor)
            where = (
                "WHERE updated_at < ? OR "
                "(updated_at = ? AND session_id < ?)"
            )
            parameters.extend([updated_at, updated_at, session_id])
        parameters.append(limit + 1)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM document_sessions
                {where}
                ORDER BY updated_at DESC, session_id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        has_more = len(rows) > limit
        visible = rows[:limit]
        items = tuple(self._document_from_row(row).summary() for row in visible)
        next_cursor = None
        if has_more and visible:
            last = visible[-1]
            next_cursor = self._encode_cursor(
                str(last["updated_at"]),
                str(last["session_id"]),
            )
        return DocumentSessionPage(items=items, next_cursor=next_cursor)

    def create_review_job(
        self,
        session_id: str,
        *,
        document_revision: int,
        options: Mapping[str, Any] | None = None,
    ) -> ReviewJob:
        self.get_document(session_id)
        now = _utc_now()
        job_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO review_jobs (
                    job_id, session_id, document_revision, status,
                    options_json, result_summary_json, error,
                    created_at, started_at, completed_at
                ) VALUES (?, ?, ?, 'queued', ?, NULL, NULL, ?, NULL, NULL)
                """,
                (
                    job_id,
                    session_id,
                    document_revision,
                    _dump_json(dict(options or {})) or "{}",
                    now,
                ),
            )
        return self.get_review_job(job_id)

    def get_review_job(self, job_id: str) -> ReviewJob:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM review_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(f"unknown review job: {job_id}")
        return self._job_from_row(row)

    def update_review_job(
        self,
        job_id: str,
        *,
        status: str,
        result_summary: Mapping[str, Any] | None = None,
        error: str | None = None,
    ) -> ReviewJob:
        if status not in {"queued", "running", "completed", "failed"}:
            raise ValueError(f"unsupported review-job status: {status}")
        existing = self.get_review_job(job_id)
        now = _utc_now()
        started_at = existing.started_at
        completed_at = existing.completed_at
        if status == "running" and started_at is None:
            started_at = now
        if status in {"completed", "failed"}:
            completed_at = now
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE review_jobs
                SET status = ?, result_summary_json = ?, error = ?,
                    started_at = ?, completed_at = ?
                WHERE job_id = ?
                """,
                (
                    status,
                    _dump_json(dict(result_summary))
                    if result_summary is not None
                    else None,
                    error,
                    started_at,
                    completed_at,
                    job_id,
                ),
            )
        return self.get_review_job(job_id)

    def list_review_jobs(
        self,
        session_id: str,
        *,
        limit: int = 50,
    ) -> tuple[ReviewJob, ...]:
        self.get_document(session_id)
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM review_jobs
                WHERE session_id = ?
                ORDER BY created_at DESC, job_id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return tuple(self._job_from_row(row) for row in rows)
