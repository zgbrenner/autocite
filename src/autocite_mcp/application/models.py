from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SessionStatus(StrEnum):
    READY = "ready"
    REVIEWING = "reviewing"
    REVIEWED = "reviewed"
    ERROR = "error"


class ReviewJobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DecisionState(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(slots=True)
class DocumentSession:
    id: str
    title: str
    source_format: str
    original_text: str
    working_text: str
    revision: int = 1
    status: SessionStatus = SessionStatus.READY
    metadata: dict[str, Any] = field(default_factory=dict)
    latest_review: dict[str, Any] | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(
        self,
        *,
        include_text: bool = True,
        include_review: bool = True,
    ) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        if not include_text:
            payload.pop("original_text", None)
            payload.pop("working_text", None)
        if not include_review:
            payload.pop("latest_review", None)
        return payload


@dataclass(slots=True)
class ReviewJob:
    id: str
    session_id: str
    session_revision: int
    state: ReviewJobState = ReviewJobState.QUEUED
    progress: float = 0.0
    result_summary: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    started_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload


@dataclass(slots=True)
class ReviewDecision:
    session_id: str
    issue_id: str
    state: DecisionState
    expected_revision: int
    replacement: str | None = None
    rationale: str | None = None
    decided_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload
