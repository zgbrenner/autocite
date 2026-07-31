from __future__ import annotations

from pathlib import Path

import pytest

from autocite_mcp.application_sessions import (
    DocumentSessionStore,
    SessionConflictError,
    SessionNotFoundError,
)


def test_document_session_persists_and_updates_with_optimistic_revision(
    tmp_path: Path,
) -> None:
    database = tmp_path / "sessions.sqlite3"
    created = DocumentSessionStore(database).create_document(
        title="Motion to dismiss",
        text="See 42 USC § 1983.",
        source_format="markdown",
        file_name="motion.md",
        mode="bluepages",
        jurisdiction="federal",
    )

    reopened = DocumentSessionStore(database)
    loaded = reopened.get_document(created.session_id)

    assert loaded.title == "Motion to dismiss"
    assert loaded.text == "See 42 USC § 1983."
    assert loaded.revision == 1
    assert loaded.content_sha256

    updated = reopened.update_document(
        created.session_id,
        text="See 42 U.S.C. § 1983.",
        expected_revision=1,
    )
    assert updated.revision == 2
    assert updated.review_result is None
    assert updated.review_revision is None

    with pytest.raises(SessionConflictError, match="expected revision 1"):
        reopened.update_document(
            created.session_id,
            text="stale write",
            expected_revision=1,
        )


def test_document_sessions_are_paginated_without_exposing_content(
    tmp_path: Path,
) -> None:
    store = DocumentSessionStore(tmp_path / "sessions.sqlite3")
    for index in range(3):
        store.create_document(
            title=f"Document {index}",
            text=f"Private body {index}",
            source_format="text",
        )

    first = store.list_documents(limit=2)
    second = store.list_documents(limit=2, cursor=first.next_cursor)

    assert len(first.items) == 2
    assert first.next_cursor is not None
    assert len(second.items) == 1
    assert second.next_cursor is None
    assert all("text" not in item for item in first.as_dict()["items"])


def test_unknown_document_fails_closed(tmp_path: Path) -> None:
    store = DocumentSessionStore(tmp_path / "sessions.sqlite3")

    with pytest.raises(SessionNotFoundError, match="unknown document session"):
        store.get_document("missing")
