from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Any, Iterable, Mapping


class ReviewDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"


class ReviewItemKind(str, Enum):
    TEXT_EDIT = "text_edit"
    ANNOTATION = "annotation"


@dataclass(frozen=True, slots=True)
class ReviewItem:
    item_id: str
    kind: ReviewItemKind
    code: str
    start: int
    end: int
    original: str
    suggestion: str | None
    message: str
    severity: str
    confidence: str
    correction_level: str
    provenance: str
    rule: str
    missing_facts: tuple[str, ...]
    source_type: str | None
    decision: ReviewDecision

    @property
    def is_safe_text_edit(self) -> bool:
        return (
            self.kind is ReviewItemKind.TEXT_EDIT
            and self.suggestion is not None
            and self.correction_level == "safe_auto_fix"
            and self.confidence == "high"
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        payload["decision"] = self.decision.value
        payload["missing_facts"] = list(self.missing_facts)
        return payload


@dataclass(frozen=True, slots=True)
class PlannedTextEdit:
    item_id: str
    code: str
    start: int
    end: int
    original: str
    replacement: str
    provenance: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PlannedAnnotation:
    item_id: str
    code: str
    start: int
    end: int
    original: str
    suggestion: str | None
    message: str
    severity: str
    confidence: str
    correction_level: str
    provenance: str
    rule: str
    missing_facts: tuple[str, ...]
    decision: ReviewDecision

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        payload["missing_facts"] = list(self.missing_facts)
        return payload


@dataclass(frozen=True, slots=True)
class ExportPlan:
    text_edits: tuple[PlannedTextEdit, ...]
    annotations: tuple[PlannedAnnotation, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "text_edits": [item.as_dict() for item in self.text_edits],
            "annotations": [item.as_dict() for item in self.annotations],
        }


def _sequence(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _integer(value: Any, *, default: int = -1) -> int:
    return value if isinstance(value, int) else default


def _text(value: Any, *, default: str = "") -> str:
    return str(value) if value is not None else default


def _item_id(
    *,
    kind: ReviewItemKind,
    code: str,
    start: int,
    end: int,
    original: str,
    suggestion: str | None,
) -> str:
    material = json.dumps(
        {
            "kind": kind.value,
            "code": code,
            "start": start,
            "end": end,
            "original": original,
            "suggestion": suggestion,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _normalise_item(raw: Mapping[str, Any], *, kind: ReviewItemKind) -> ReviewItem:
    code = _text(raw.get("issue_code") or raw.get("code"), default="REVIEW_ITEM")
    start = _integer(raw.get("start"))
    end = _integer(raw.get("end"))
    original = _text(raw.get("original"))
    suggestion_value = raw.get("suggestion")
    suggestion = _text(suggestion_value) if suggestion_value is not None else None
    correction_level = _text(
        raw.get("correction_level"),
        default="safe_auto_fix" if kind is ReviewItemKind.TEXT_EDIT else "review_required",
    )
    confidence = _text(raw.get("confidence"), default="unknown")
    decision = (
        ReviewDecision.ACCEPTED
        if kind is ReviewItemKind.TEXT_EDIT
        and suggestion is not None
        and correction_level == "safe_auto_fix"
        and confidence == "high"
        else ReviewDecision.PENDING
    )
    message = _text(
        raw.get("explanation") or raw.get("message"),
        default=(
            "AutoCite identified a supported mechanical edit."
            if kind is ReviewItemKind.TEXT_EDIT
            else "Review this citation item."
        ),
    )
    missing_facts = tuple(_text(item) for item in _sequence(raw.get("missing_facts")))
    source_type_value = raw.get("source_type")
    source_type = _text(source_type_value) if source_type_value is not None else None
    return ReviewItem(
        item_id=_item_id(
            kind=kind,
            code=code,
            start=start,
            end=end,
            original=original,
            suggestion=suggestion,
        ),
        kind=kind,
        code=code,
        start=start,
        end=end,
        original=original,
        suggestion=suggestion,
        message=message,
        severity=_text(raw.get("severity"), default="warning"),
        confidence=confidence,
        correction_level=correction_level,
        provenance=_text(raw.get("provenance"), default="deterministic_logic"),
        rule=_text(
            raw.get("rule_family_reference")
            or raw.get("rule")
            or raw.get("family")
        ),
        missing_facts=missing_facts,
        source_type=source_type,
        decision=decision,
    )


@dataclass(frozen=True, slots=True)
class ReviewSession:
    items: tuple[ReviewItem, ...]
    schema_version: str = "1.0"

    @classmethod
    def from_result(cls, result: Mapping[str, Any]) -> "ReviewSession":
        items: list[ReviewItem] = []
        seen: set[tuple[Any, ...]] = set()

        for raw in _sequence(result.get("applied_edits")):
            if not isinstance(raw, Mapping):
                continue
            item = _normalise_item(raw, kind=ReviewItemKind.TEXT_EDIT)
            key = (item.code, item.start, item.end, item.original, item.suggestion)
            if key in seen:
                continue
            seen.add(key)
            items.append(item)

        for collection_name in ("remaining_issues", "rule_findings"):
            for raw in _sequence(result.get(collection_name)):
                if not isinstance(raw, Mapping):
                    continue
                item = _normalise_item(raw, kind=ReviewItemKind.ANNOTATION)
                key = (item.code, item.start, item.end, item.original, item.suggestion)
                if key in seen:
                    continue
                seen.add(key)
                items.append(item)

        items.sort(
            key=lambda item: (
                item.start if item.start >= 0 else 2**63 - 1,
                0 if item.kind is ReviewItemKind.TEXT_EDIT else 1,
                item.end,
                item.code,
                item.item_id,
            )
        )
        return cls(tuple(items))

    def _replace_decision(
        self, item_id: str, decision: ReviewDecision
    ) -> "ReviewSession":
        found = False
        changed: list[ReviewItem] = []
        for item in self.items:
            if item.item_id == item_id:
                found = True
                changed.append(replace(item, decision=decision))
            else:
                changed.append(item)
        if not found:
            raise KeyError(f"unknown review item: {item_id}")
        return replace(self, items=tuple(changed))

    def accept(self, item_id: str) -> "ReviewSession":
        return self._replace_decision(item_id, ReviewDecision.ACCEPTED)

    def reject(self, item_id: str) -> "ReviewSession":
        return self._replace_decision(item_id, ReviewDecision.REJECTED)

    def reset(self, item_id: str) -> "ReviewSession":
        return self._replace_decision(item_id, ReviewDecision.PENDING)

    def accept_all_safe(self) -> "ReviewSession":
        return replace(
            self,
            items=tuple(
                replace(item, decision=ReviewDecision.ACCEPTED)
                if item.is_safe_text_edit
                else item
                for item in self.items
            ),
        )

    def export_plan(self) -> ExportPlan:
        text_edits = tuple(
            PlannedTextEdit(
                item_id=item.item_id,
                code=item.code,
                start=item.start,
                end=item.end,
                original=item.original,
                replacement=item.suggestion or "",
                provenance=item.provenance,
            )
            for item in self.items
            if item.kind is ReviewItemKind.TEXT_EDIT
            and item.decision is ReviewDecision.ACCEPTED
            and item.suggestion is not None
        )
        ordered_edits = tuple(sorted(text_edits, key=lambda item: (item.start, item.end)))
        previous: PlannedTextEdit | None = None
        for item in ordered_edits:
            if item.start < 0 or item.end < item.start:
                raise ValueError(f"accepted edit {item.item_id} has an invalid source range")
            if previous is not None and item.start < previous.end:
                raise ValueError(
                    f"accepted edits overlap: {previous.item_id} and {item.item_id}"
                )
            previous = item

        annotations: list[PlannedAnnotation] = []
        for item in self.items:
            include = item.kind is ReviewItemKind.ANNOTATION and (
                item.decision is not ReviewDecision.ACCEPTED
                or item.correction_level == "unsupported"
            )
            include = include or (
                item.kind is ReviewItemKind.TEXT_EDIT
                and item.decision is not ReviewDecision.ACCEPTED
            )
            if not include:
                continue
            annotations.append(
                PlannedAnnotation(
                    item_id=item.item_id,
                    code=item.code,
                    start=item.start,
                    end=item.end,
                    original=item.original,
                    suggestion=item.suggestion,
                    message=item.message,
                    severity=item.severity,
                    confidence=item.confidence,
                    correction_level=item.correction_level,
                    provenance=item.provenance,
                    rule=item.rule,
                    missing_facts=item.missing_facts,
                    decision=item.decision,
                )
            )
        annotations.sort(
            key=lambda item: (
                item.start if item.start >= 0 else 2**63 - 1,
                item.end,
                item.code,
                item.item_id,
            )
        )
        return ExportPlan(ordered_edits, tuple(annotations))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "items": [item.as_dict() for item in self.items],
        }

    def decisions(self) -> dict[str, ReviewDecision]:
        return {item.item_id: item.decision for item in self.items}

    def with_decisions(
        self, decisions: Mapping[str, ReviewDecision | str]
    ) -> "ReviewSession":
        session = self
        known = {item.item_id for item in self.items}
        unknown = set(decisions) - known
        if unknown:
            raise KeyError(f"unknown review item: {sorted(unknown)[0]}")
        for item_id, raw_decision in decisions.items():
            decision = (
                raw_decision
                if isinstance(raw_decision, ReviewDecision)
                else ReviewDecision(str(raw_decision))
            )
            session = session._replace_decision(item_id, decision)
        return session

    def __iter__(self) -> Iterable[ReviewItem]:
        return iter(self.items)
