from __future__ import annotations

import pytest

from autocite_mcp.application.models import (
    DecisionState,
    ReviewDecision,
    ReviewJobState,
)
from autocite_mcp.application.store import RevisionConflict, SessionStore


def test_session_store_persists_and_protects_revisions(tmp_path) -> None:
    database = tmp_path / "sessions.sqlite3"
    store = SessionStore(database)
    created = store.create_session(
        title="Motion to Dismiss",
        source_format="docx",
        original_text="See 42 USC §1983.",
        metadata={"matter": "Example"},
    )

    updated = store.update_session(
        created.id,
        expected_revision=1,
        working_text="See 42 U.S.C. § 1983.",
        metadata_patch={"zoom": 110},
    )
    assert updated.revision == 2
    assert updated.original_text == "See 42 USC §1983."
    assert updated.working_text == "See 42 U.S.C. § 1983."
    assert updated.metadata == {"matter": "Example", "zoom": 110}

    with pytest.raises(RevisionConflict) as conflict:
        store.update_session(
            created.id,
            expected_revision=1,
            working_text="stale autosave",
        )
    assert conflict.value.actual == 2

    reopened = SessionStore(database).get_session(created.id)
    assert reopened.revision == 2
    assert reopened.working_text == updated.working_text
    assert SessionStore(database).list_sessions()[0].id == created.id


def test_review_jobs_and_decisions_are_durable(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.sqlite3")
    session = store.create_session(
        title="Brief",
        source_format="md",
        original_text="Id at 4.",
    )
    job = store.create_review_job(session.id, session.revision)
    running = store.update_review_job(
        job.id,
        state=ReviewJobState.RUNNING,
        progress=0.25,
    )
    assert running.started_at is not None
    completed = store.update_review_job(
        job.id,
        state=ReviewJobState.COMPLETED,
        progress=1.0,
        result_summary={"issue_count": 1},
    )
    assert completed.completed_at is not None
    assert completed.result_summary == {"issue_count": 1}

    decision = store.save_decision(
        ReviewDecision(
            session_id=session.id,
            issue_id="issue-1",
            state=DecisionState.REJECTED,
            expected_revision=session.revision,
            rationale="Needs human review",
        )
    )
    assert decision.state is DecisionState.REJECTED
    assert store.list_decisions(session.id)[0].rationale == "Needs human review"


def test_delete_session_cascades_related_state(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.sqlite3")
    session = store.create_session(
        title="Temporary",
        source_format="txt",
        original_text="Temporary text",
    )
    job = store.create_review_job(session.id, session.revision)
    store.delete_session(session.id)

    with pytest.raises(Exception):
        store.get_review_job(job.id)
