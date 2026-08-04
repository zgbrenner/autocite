"""Canonical application services shared by AutoCite's MCP and desktop clients.

The application layer deliberately sits above the citation engine.  It owns
persistent document sessions, optimistic revisions, review decisions, export
state, and conservative context reduction while leaving citation analysis to
the existing deterministic AutoCite engine.
"""

from .context_reducer import (
    ContextReducer,
    DeterministicLegalContextReducer,
    NoopContextReducer,
    ReducedContext,
    ReductionMetrics,
)
from .models import (
    DecisionState,
    DocumentSession,
    ReviewJob,
    ReviewJobState,
    SessionStatus,
)
from .service import ApplicationService
from .store import RevisionConflict, SessionNotFound, SessionStore

__all__ = [
    "ApplicationService",
    "ContextReducer",
    "DecisionState",
    "DeterministicLegalContextReducer",
    "DocumentSession",
    "NoopContextReducer",
    "ReducedContext",
    "ReductionMetrics",
    "ReviewJob",
    "ReviewJobState",
    "RevisionConflict",
    "SessionNotFound",
    "SessionStatus",
    "SessionStore",
]
