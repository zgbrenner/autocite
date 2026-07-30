from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .review_session import ReviewDecision, ReviewItem, ReviewSession


class ReviewFilter(str, Enum):
    ALL = "all"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"
    SAFE = "safe"
    REVIEW_REQUIRED = "review_required"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class ReviewWorkspaceSummary:
    total: int
    accepted: int
    rejected: int
    pending: int
    safe_text_edits: int
    review_required: int
    unsupported: int


class DesktopReviewViewModel:
    """UI-independent state and history for the desktop review workspace."""

    def __init__(
        self,
        session: ReviewSession,
        *,
        history_limit: int = 100,
    ) -> None:
        if history_limit < 1:
            raise ValueError("history_limit must be at least 1")
        self._session = session
        self._history_limit = history_limit
        self._undo: list[ReviewSession] = []
        self._redo: list[ReviewSession] = []
        self._filter = ReviewFilter.ALL
        self._severity: str | None = None
        self._source_type: str | None = None
        self._rule: str | None = None
        self._search = ""
        self._current_item_id: str | None = (
            session.items[0].item_id if session.items else None
        )

    @property
    def session(self) -> ReviewSession:
        return self._session

    @property
    def decisions(self) -> Mapping[str, ReviewDecision]:
        return self._session.decisions()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def active_filter(self) -> ReviewFilter:
        return self._filter

    @property
    def visible_items(self) -> tuple[ReviewItem, ...]:
        return tuple(item for item in self._session.items if self._matches(item))

    @property
    def current_item(self) -> ReviewItem | None:
        visible = self.visible_items
        if not visible:
            return None
        if self._current_item_id is not None:
            for item in visible:
                if item.item_id == self._current_item_id:
                    return item
        return visible[0]

    def item(self, item_id: str) -> ReviewItem:
        for item in self._session.items:
            if item.item_id == item_id:
                return item
        raise KeyError(f"unknown review item: {item_id}")

    def _matches(self, item: ReviewItem) -> bool:
        if self._filter is ReviewFilter.ACCEPTED and item.decision is not ReviewDecision.ACCEPTED:
            return False
        if self._filter is ReviewFilter.REJECTED and item.decision is not ReviewDecision.REJECTED:
            return False
        if self._filter is ReviewFilter.PENDING and item.decision is not ReviewDecision.PENDING:
            return False
        if self._filter is ReviewFilter.SAFE and not item.is_safe_text_edit:
            return False
        if (
            self._filter is ReviewFilter.REVIEW_REQUIRED
            and item.correction_level not in {"review_required", "suggested_fix"}
        ):
            return False
        if self._filter is ReviewFilter.UNSUPPORTED and item.correction_level != "unsupported":
            return False
        if self._severity is not None and item.severity.casefold() != self._severity:
            return False
        if self._source_type is not None and (item.source_type or "").casefold() != self._source_type:
            return False
        if self._rule is not None and item.rule.casefold() != self._rule:
            return False
        if self._search:
            haystack = "\n".join(
                value
                for value in (
                    item.code,
                    item.message,
                    item.original,
                    item.suggestion or "",
                    item.rule,
                    item.source_type or "",
                    item.provenance,
                )
                if value
            ).casefold()
            if self._search not in haystack:
                return False
        return True

    def _normalize_selection(self) -> None:
        visible = self.visible_items
        if not visible:
            self._current_item_id = None
            return
        if self._current_item_id not in {item.item_id for item in visible}:
            self._current_item_id = visible[0].item_id

    def _commit(self, session: ReviewSession) -> None:
        if session == self._session:
            return
        self._undo.append(self._session)
        if len(self._undo) > self._history_limit:
            del self._undo[: len(self._undo) - self._history_limit]
        self._session = session
        self._redo.clear()
        self._normalize_selection()

    def accept(self, item_id: str) -> None:
        self._commit(self._session.accept(item_id))

    def reject(self, item_id: str) -> None:
        self._commit(self._session.reject(item_id))

    def reset(self, item_id: str) -> None:
        self._commit(self._session.reset(item_id))

    def accept_all_safe(self) -> None:
        self._commit(self._session.accept_all_safe())

    def undo(self) -> None:
        if not self._undo:
            return
        previous = self._undo.pop()
        self._redo.append(self._session)
        self._session = previous
        self._normalize_selection()

    def redo(self) -> None:
        if not self._redo:
            return
        next_session = self._redo.pop()
        self._undo.append(self._session)
        if len(self._undo) > self._history_limit:
            del self._undo[: len(self._undo) - self._history_limit]
        self._session = next_session
        self._normalize_selection()

    def set_filter(self, value: ReviewFilter | str) -> None:
        self._filter = value if isinstance(value, ReviewFilter) else ReviewFilter(value)
        self._normalize_selection()

    def set_severity(self, value: str | None) -> None:
        cleaned = (value or "").strip().casefold()
        self._severity = cleaned or None
        self._normalize_selection()

    def set_source_type(self, value: str | None) -> None:
        cleaned = (value or "").strip().casefold()
        self._source_type = cleaned or None
        self._normalize_selection()

    def set_rule(self, value: str | None) -> None:
        cleaned = (value or "").strip().casefold()
        self._rule = cleaned or None
        self._normalize_selection()

    def set_search(self, value: str | None) -> None:
        self._search = (value or "").strip().casefold()
        self._normalize_selection()

    def select(self, item_id: str) -> ReviewItem:
        visible = self.visible_items
        for item in visible:
            if item.item_id == item_id:
                self._current_item_id = item_id
                return item
        raise KeyError(f"review item is not visible: {item_id}")

    def next_item(self) -> ReviewItem | None:
        visible = self.visible_items
        if not visible:
            self._current_item_id = None
            return None
        current = self.current_item
        if current is None:
            self._current_item_id = visible[0].item_id
            return visible[0]
        index = next(
            position
            for position, item in enumerate(visible)
            if item.item_id == current.item_id
        )
        selected = visible[min(index + 1, len(visible) - 1)]
        self._current_item_id = selected.item_id
        return selected

    def previous_item(self) -> ReviewItem | None:
        visible = self.visible_items
        if not visible:
            self._current_item_id = None
            return None
        current = self.current_item
        if current is None:
            self._current_item_id = visible[0].item_id
            return visible[0]
        index = next(
            position
            for position, item in enumerate(visible)
            if item.item_id == current.item_id
        )
        selected = visible[max(index - 1, 0)]
        self._current_item_id = selected.item_id
        return selected

    def render_corrected_text(self, original_text: str) -> str:
        rendered = original_text
        for edit in sorted(
            self._session.export_plan().text_edits,
            key=lambda item: (item.start, item.end),
            reverse=True,
        ):
            if rendered[edit.start : edit.end] != edit.original:
                raise ValueError(
                    f"review text no longer matches accepted edit {edit.item_id}"
                )
            rendered = (
                rendered[: edit.start]
                + edit.replacement
                + rendered[edit.end :]
            )
        return rendered

    def summary(self) -> ReviewWorkspaceSummary:
        items = self._session.items
        return ReviewWorkspaceSummary(
            total=len(items),
            accepted=sum(item.decision is ReviewDecision.ACCEPTED for item in items),
            rejected=sum(item.decision is ReviewDecision.REJECTED for item in items),
            pending=sum(item.decision is ReviewDecision.PENDING for item in items),
            safe_text_edits=sum(item.is_safe_text_edit for item in items),
            review_required=sum(
                item.correction_level in {"review_required", "suggested_fix"}
                for item in items
            ),
            unsupported=sum(item.correction_level == "unsupported" for item in items),
        )
