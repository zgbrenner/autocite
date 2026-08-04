from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import (
    DecisionState,
    DocumentSession,
    ReviewDecision,
    ReviewJob,
    ReviewJobState,
    SessionStatus,
    utc_now_iso,
)


class SessionStoreError(RuntimeError):
    """Base error for application persistence."""


class SessionNotFound(SessionStoreError):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Document session not found: {session_id}")
        self.session_id = session_id


class ReviewJobNotFound(SessionStoreError):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"Review job not found: {job_id}")
        self.job_id = job_id


class RevisionConflict(SessionStoreError):
    def __init__(self, session_id: str, expected: int, actual: int) -> None:
        super().__init__(
            f"Revision conflict for {session_id}: expected {expected}, current {actual}"
        )
        self.session_id = session_id
        self.expected = expected
        self.actual = actual


def default_database_path() -> Path:
    configured = os.environ.get("AUTOCITE_SESSION_DB")
    if configured:
        return Path(configured).expanduser().resolve()

    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys_platform() == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "AutoCite" / "sessions.sqlite3"


def sys_platform() -> str:
    # Kept in a small function so platform-path behavior is easy to test.
    import sys

    return sys.platform


class SessionStore:
    """Durable, local-only application state.

    A connection is opened per operation so the same store can be used safely
    by MCP requests, a loopback HTTP server, and desktop worker threads.  Text
    edits use optimistic revisions to prevent an autosave from overwriting a
    newer editor state.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_database_path()
        self.path = self.path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_lock = threading.Lock()
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._schema_lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS document_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_format TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    working_text TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    latest_review_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_jobs (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    session_revision INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    result_summary_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES document_sessions(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS review_jobs_session_idx
                    ON review_jobs(session_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS review_decisions (
                    session_id TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    expected_revision INTEGER NOT NULL,
                    replacement TEXT,
                    rationale TEXT,
                    decided_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, issue_id),
                    FOREIGN KEY (session_id) REFERENCES document_sessions(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS exports (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    session_revision INTEGER NOT NULL,
                    format TEXT NOT NULL,
                    path TEXT,
                    sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES document_sessions(id)
                        ON DELETE CASCADE
                );
                """
            )

    @staticmethod
    def _decode_json(value: str | None, fallback: Any) -> Any:
        if value is None:
            return fallback
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return fallback

    @classmethod
    def _session_from_row(cls, row: sqlite3.Row) -> DocumentSession:
        return DocumentSession(
            id=row["id"],
            title=row["title"],
            source_format=row["source_format"],
            original_text=row["original_text"],
            working_text=row["working_text"],
            revision=int(row["revision"]),
            status=SessionStatus(row["status"]),
            metadata=cls._decode_json(row["metadata_json"], {}),
            latest_review=cls._decode_json(row["latest_review_json"], None),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @classmethod
    def _job_from_row(cls, row: sqlite3.Row) -> ReviewJob:
        return ReviewJob(
            id=row["id"],
            session_id=row["session_id"],
            session_revision=int(row["session_revision"]),
            state=ReviewJobState(row["state"]),
            progress=float(row["progress"]),
            result_summary=cls._decode_json(row["result_summary_json"], None),
            error=row["error"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )

    def create_session(
        self,
        *,
        title: str,
        source_format: str,
        original_text: str,
        working_text: str | None = None,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> DocumentSession:
        identifier = session_id or uuid4().hex
        now = utc_now_iso()
        session = DocumentSession(
            id=identifier,
            title=title.strip() or "Untitled document",
            source_format=(source_format.strip().lower() or "txt"),
            original_text=original_text,
            working_text=original_text if working_text is None else working_text,
            metadata=dict(metadata or {}),
            created_at=now,
            updated_at=now,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO document_sessions (
                    id, title, source_format, original_text, working_text,
                    revision, status, metadata_json, latest_review_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.title,
                    session.source_format,
                    session.original_text,
                    session.working_text,
                    session.revision,
                    session.status.value,
                    json.dumps(session.metadata, ensure_ascii=False),
                    None,
                    session.created_at,
                    session.updated_at,
                ),
            )
        return session

    def get_session(self, session_id: str) -> DocumentSession:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM document_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if row is None:
            raise SessionNotFound(session_id)
        return self._session_from_row(row)

    def list_sessions(self, *, limit: int = 50, offset: int = 0) -> list[DocumentSession]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM document_sessions
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (safe_limit, safe_offset),
            ).fetchall()
        return [self._session_from_row(row) for row in rows]

    def update_session(
        self,
        session_id: str,
        *,
        expected_revision: int,
        working_text: str | None = None,
        title: str | None = None,
        metadata_patch: dict[str, Any] | None = None,
        status: SessionStatus | None = None,
        clear_review: bool = False,
    ) -> DocumentSession:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM document_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                connection.execute("ROLLBACK")
                raise SessionNotFound(session_id)

            current = self._session_from_row(row)
            if current.revision != expected_revision:
                connection.execute("ROLLBACK")
                raise RevisionConflict(session_id, expected_revision, current.revision)

            next_text = current.working_text if working_text is None else working_text
            next_title = current.title if title is None else (title.strip() or current.title)
            next_metadata = dict(current.metadata)
            if metadata_patch:
                next_metadata.update(metadata_patch)
            next_status = status or (
                SessionStatus.READY if working_text is not None else current.status
            )
            next_revision = current.revision + 1
            now = utc_now_iso()
            latest_review_json = (
                None
                if clear_review or working_text is not None
                else json.dumps(current.latest_review, ensure_ascii=False)
                if current.latest_review is not None
                else None
            )
            cursor = connection.execute(
                """
                UPDATE document_sessions
                SET title = ?, working_text = ?, revision = ?, status = ?,
                    metadata_json = ?, latest_review_json = ?, updated_at = ?
                WHERE id = ? AND revision = ?
                """,
                (
                    next_title,
                    next_text,
                    next_revision,
                    next_status.value,
                    json.dumps(next_metadata, ensure_ascii=False),
                    latest_review_json,
                    now,
                    session_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                actual_row = connection.execute(
                    "SELECT revision FROM document_sessions WHERE id = ?", (session_id,)
                ).fetchone()
                connection.execute("ROLLBACK")
                actual = int(actual_row["revision"]) if actual_row else -1
                raise RevisionConflict(session_id, expected_revision, actual)
            connection.execute("COMMIT")
        return self.get_session(session_id)

    def save_review(
        self,
        session_id: str,
        *,
        expected_revision: int,
        review: dict[str, Any],
        status: SessionStatus = SessionStatus.REVIEWED,
    ) -> DocumentSession:
        now = utc_now_iso()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE document_sessions
                SET latest_review_json = ?, status = ?, updated_at = ?
                WHERE id = ? AND revision = ?
                """,
                (
                    json.dumps(review, ensure_ascii=False),
                    status.value,
                    now,
                    session_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                row = connection.execute(
                    "SELECT revision FROM document_sessions WHERE id = ?", (session_id,)
                ).fetchone()
                if row is None:
                    raise SessionNotFound(session_id)
                raise RevisionConflict(session_id, expected_revision, int(row["revision"]))
        return self.get_session(session_id)

    def set_status(
        self,
        session_id: str,
        status: SessionStatus,
        *,
        expected_revision: int | None = None,
    ) -> DocumentSession:
        parameters: list[Any] = [status.value, utc_now_iso(), session_id]
        where = "id = ?"
        if expected_revision is not None:
            where += " AND revision = ?"
            parameters.append(expected_revision)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE document_sessions SET status = ?, updated_at = ? WHERE {where}",
                tuple(parameters),
            )
            if cursor.rowcount != 1:
                row = connection.execute(
                    "SELECT revision FROM document_sessions WHERE id = ?", (session_id,)
                ).fetchone()
                if row is None:
                    raise SessionNotFound(session_id)
                if expected_revision is not None:
                    raise RevisionConflict(session_id, expected_revision, int(row["revision"]))
        return self.get_session(session_id)

    def create_review_job(self, session_id: str, session_revision: int) -> ReviewJob:
        self.get_session(session_id)
        job = ReviewJob(
            id=uuid4().hex,
            session_id=session_id,
            session_revision=session_revision,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO review_jobs (
                    id, session_id, session_revision, state, progress,
                    result_summary_json, error, created_at, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.session_id,
                    job.session_revision,
                    job.state.value,
                    job.progress,
                    None,
                    None,
                    job.created_at,
                    None,
                    None,
                ),
            )
        return job

    def update_review_job(
        self,
        job_id: str,
        *,
        state: ReviewJobState,
        progress: float | None = None,
        result_summary: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> ReviewJob:
        current = self.get_review_job(job_id)
        started_at = current.started_at
        completed_at = current.completed_at
        now = utc_now_iso()
        if state is ReviewJobState.RUNNING and started_at is None:
            started_at = now
        if state in {
            ReviewJobState.COMPLETED,
            ReviewJobState.FAILED,
            ReviewJobState.CANCELLED,
        }:
            completed_at = now
        next_progress = current.progress if progress is None else max(0.0, min(progress, 1.0))
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE review_jobs
                SET state = ?, progress = ?, result_summary_json = ?, error = ?,
                    started_at = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    state.value,
                    next_progress,
                    json.dumps(result_summary, ensure_ascii=False)
                    if result_summary is not None
                    else None,
                    error,
                    started_at,
                    completed_at,
                    job_id,
                ),
            )
        return self.get_review_job(job_id)

    def get_review_job(self, job_id: str) -> ReviewJob:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM review_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise ReviewJobNotFound(job_id)
        return self._job_from_row(row)

    def save_decision(self, decision: ReviewDecision) -> ReviewDecision:
        session = self.get_session(decision.session_id)
        if session.revision != decision.expected_revision:
            raise RevisionConflict(
                decision.session_id, decision.expected_revision, session.revision
            )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO review_decisions (
                    session_id, issue_id, state, expected_revision,
                    replacement, rationale, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, issue_id) DO UPDATE SET
                    state = excluded.state,
                    expected_revision = excluded.expected_revision,
                    replacement = excluded.replacement,
                    rationale = excluded.rationale,
                    decided_at = excluded.decided_at
                """,
                (
                    decision.session_id,
                    decision.issue_id,
                    decision.state.value,
                    decision.expected_revision,
                    decision.replacement,
                    decision.rationale,
                    decision.decided_at,
                ),
            )
        return decision

    def list_decisions(self, session_id: str) -> list[ReviewDecision]:
        self.get_session(session_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM review_decisions
                WHERE session_id = ? ORDER BY decided_at ASC
                """,
                (session_id,),
            ).fetchall()
        return [
            ReviewDecision(
                session_id=row["session_id"],
                issue_id=row["issue_id"],
                state=DecisionState(row["state"]),
                expected_revision=int(row["expected_revision"]),
                replacement=row["replacement"],
                rationale=row["rationale"],
                decided_at=row["decided_at"],
            )
            for row in rows
        ]

    def record_export(
        self,
        *,
        session_id: str,
        session_revision: int,
        output_format: str,
        sha256: str,
        path: str | None,
    ) -> str:
        export_id = uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO exports (
                    id, session_id, session_revision, format, path, sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    export_id,
                    session_id,
                    session_revision,
                    output_format,
                    path,
                    sha256,
                    utc_now_iso(),
                ),
            )
        return export_id

    def delete_session(self, session_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM document_sessions WHERE id = ?", (session_id,)
            )
        if cursor.rowcount != 1:
            raise SessionNotFound(session_id)
