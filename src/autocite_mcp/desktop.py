from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import os
import stat
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Sequence

from .documents import MAX_DOCUMENT_BYTES, DocumentLoadError
from .tools import export_review_docx, review_uploaded_document


SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".docx", ".pdf"}
APP_NAME = "AutoCite"
PACKAGE_NAME = "autocite-mcp"
FALLBACK_VERSION = "0.6.0"
ACCURACY_BOUNDARIES = (
    "AutoCite reviews supported citation-format and citation-structure issues. It does not determine whether an authority is good law.",
    "Source retrieval and lexical matching do not prove that an authority supports a legal proposition or is controlling.",
    "Local court rules, journal rules, quotations, pincites, and ambiguous short forms can still require human review.",
    "The source document is never modified. Reviewed DOCX exports preserve text-level changes, not the source file's complete layout.",
)
_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
_CORRECTION_LABELS = {
    "safe_auto_fix": "Safely fixed",
    "suggested_fix": "Suggested change",
    "review_required": "Needs review",
    "unsupported": "Outside current coverage",
}


def application_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return FALLBACK_VERSION


@dataclass(frozen=True)
class DesktopReviewState:
    original_text: str
    corrected_text: str
    result: dict[str, Any] | None
    error_code: str | None = None
    error_message: str | None = None
    source_path: Path | None = None


@dataclass(frozen=True)
class DesktopSummary:
    mode: str
    mode_confidence: str
    citations: int
    applied_edits: int
    review_items: int
    unsupported_items: int
    remaining_mechanical_issues: int
    mechanical_review_complete: bool


def _sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def summarize_review(result: dict[str, Any]) -> DesktopSummary:
    findings = _sequence(result.get("rule_findings"))
    remaining = _sequence(result.get("remaining_issues"))
    review_items = sum(
        str(item.get("correction_level", "review_required"))
        in {"review_required", "suggested_fix"}
        for item in findings
        if isinstance(item, dict)
    )
    review_items += sum(
        str(item.get("correction_level", "review_required"))
        in {"review_required", "suggested_fix"}
        for item in remaining
        if isinstance(item, dict)
    )
    unsupported_items = sum(
        str(item.get("correction_level")) == "unsupported"
        for item in findings
        if isinstance(item, dict)
    )
    detection = result.get("mode_detection")
    confidence = (
        str(detection.get("confidence", "unknown"))
        if isinstance(detection, dict)
        else "unknown"
    )
    return DesktopSummary(
        mode=str(result.get("mode") or "unknown"),
        mode_confidence=confidence,
        citations=len(_sequence(result.get("citation_inventory"))),
        applied_edits=len(_sequence(result.get("applied_edits"))),
        review_items=review_items,
        unsupported_items=unsupported_items,
        remaining_mechanical_issues=len(remaining),
        mechanical_review_complete=bool(result.get("mechanical_review_complete", False)),
    )


def _normalized_issue(item: dict[str, Any]) -> dict[str, Any]:
    code = str(item.get("issue_code") or item.get("code") or "REVIEW_ITEM")
    message = str(
        item.get("explanation")
        or item.get("message")
        or "Review this citation item."
    )
    start = item.get("start")
    end = item.get("end")
    return {
        "code": code,
        "message": message,
        "severity": str(item.get("severity") or "warning"),
        "confidence": str(item.get("confidence") or "unknown"),
        "correction_level": str(
            item.get("correction_level") or "review_required"
        ),
        "provenance": str(item.get("provenance") or "deterministic_logic"),
        "start": int(start) if isinstance(start, int) else -1,
        "end": int(end) if isinstance(end, int) else -1,
        "original": str(item.get("original") or ""),
        "suggestion": (
            str(item["suggestion"]) if item.get("suggestion") is not None else None
        ),
        "rule": str(
            item.get("rule_family_reference")
            or item.get("rule")
            or item.get("family")
            or ""
        ),
        "missing_facts": [str(value) for value in _sequence(item.get("missing_facts"))],
    }


def iter_desktop_issues(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for collection_name in ("remaining_issues", "rule_findings"):
        for raw in _sequence(result.get(collection_name)):
            if not isinstance(raw, dict):
                continue
            row = _normalized_issue(raw)
            key = (row["code"], row["start"], row["end"], row["original"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    rows.sort(
        key=lambda item: (
            item["start"] if item["start"] >= 0 else sys.maxsize,
            _SEVERITY_ORDER.get(item["severity"].lower(), 9),
            item["code"],
        )
    )
    return rows


def default_export_path(source: Path, *, extension: str = ".docx") -> Path:
    source = Path(source)
    normalized_extension = extension if extension.startswith(".") else f".{extension}"
    return source.with_name(f"{source.stem} - AutoCite Review{normalized_extension}")


def build_desktop_report(state: DesktopReviewState) -> dict[str, Any]:
    if state.result is None:
        raise ValueError("a completed review is required before report export")
    result = state.result
    input_document = result.get("input_document")
    input_document = input_document if isinstance(input_document, dict) else {}
    filename = str(
        input_document.get("filename")
        or (state.source_path.name if state.source_path is not None else "document")
    )
    summary = summarize_review(result)
    slm_review = result.get("slm_review")
    retrieval = result.get("retrieval")
    return {
        "schema_version": "1.0",
        "product": "AutoCite Desktop",
        "product_version": application_version(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "filename": filename,
            "sha256": input_document.get("sha256"),
            "source_format": input_document.get("source_format"),
            "warnings": _sequence(input_document.get("warnings")),
        },
        "summary": asdict(summary),
        "mode_detection": result.get("mode_detection"),
        "jurisdiction": result.get("jurisdiction"),
        "applied_edits": _sequence(result.get("applied_edits")),
        "issues": iter_desktop_issues(result),
        "citation_inventory": _sequence(result.get("citation_inventory")),
        "correction_levels": result.get("correction_levels", {}),
        "local_model_status": (
            slm_review.get("status") if isinstance(slm_review, dict) else "not_requested"
        ),
        "local_rule_retrieval": {
            "triggered": bool(retrieval.get("triggered"))
            if isinstance(retrieval, dict)
            else False,
            "local_only": bool(retrieval.get("local_only", True))
            if isinstance(retrieval, dict)
            else True,
        },
        "accuracy_boundaries": list(ACCURACY_BOUNDARIES),
    }


def friendly_error_message(code: str, detail: str | None = None) -> str:
    templates = {
        "file_not_found": "The selected file could not be found. Choose the file again and retry.",
        "not_a_file": "The selected item is a folder. Choose one supported document file.",
        "permission_denied": "AutoCite cannot read this file. Close it in other programs or copy it to a folder you can access.",
        "unsupported_format": "Choose a TXT, Markdown, DOCX, or text-based PDF file.",
        "document_too_large": (
            f"This file is too large for one review. AutoCite accepts files up to "
            f"{MAX_DOCUMENT_BYTES // (1024 * 1024)} MB. Split the document and review each part."
        ),
        "ocr_required": "This PDF does not contain readable text. Run OCR or save it as a searchable PDF, then try again.",
        "insufficient_memory": "The review ran out of memory. Close other applications and use Standard local review.",
        "review_failed": "AutoCite could not complete this review. The source file was not changed.",
        "read_failed": "AutoCite could not read this file. The source file was not changed.",
    }
    base = templates.get(code, templates["review_failed"])
    cleaned = (detail or "").strip()
    if cleaned and cleaned.casefold() not in base.casefold():
        return f"{base}\n\nTechnical detail: {cleaned}"
    return base


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve(strict=False) == right.resolve(strict=False)
    except OSError:
        return os.path.abspath(left) == os.path.abspath(right)


def _atomic_write(destination: Path, payload: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


class DesktopReviewController:
    """UI-independent controller using the same core package as CLI and MCP."""

    @staticmethod
    def state_from_result(
        source: Path, result: dict[str, Any]
    ) -> DesktopReviewState:
        return DesktopReviewState(
            original_text=str(result.get("original_text") or ""),
            corrected_text=str(result.get("corrected_text") or ""),
            result=result,
            source_path=Path(source),
        )

    @staticmethod
    def _error(
        source: Path,
        code: str,
        detail: str | None = None,
    ) -> DesktopReviewState:
        return DesktopReviewState(
            "",
            "",
            None,
            code,
            friendly_error_message(code, detail),
            Path(source),
        )

    async def review_file(
        self,
        path: Path,
        *,
        document_type: str = "auto",
        mode: str = "auto",
        jurisdiction: str | None = None,
        use_local_model: bool = False,
    ) -> DesktopReviewState:
        source = Path(path).expanduser()
        try:
            file_stat = await asyncio.to_thread(source.stat)
        except FileNotFoundError:
            return self._error(source, "file_not_found")
        except PermissionError as exc:
            return self._error(source, "permission_denied", str(exc))
        except OSError as exc:
            return self._error(source, "read_failed", str(exc))

        if not stat.S_ISREG(file_stat.st_mode):
            return self._error(source, "not_a_file")
        if source.suffix.casefold() not in SUPPORTED_SUFFIXES:
            return self._error(source, "unsupported_format")
        if file_stat.st_size > MAX_DOCUMENT_BYTES:
            return self._error(source, "document_too_large")

        try:
            payload = await asyncio.to_thread(source.read_bytes)
            result = await review_uploaded_document(
                {
                    "file_name": source.name,
                    "data_base64": base64.b64encode(payload).decode("ascii"),
                },
                document_type=document_type,
                mode=mode,
                jurisdiction=jurisdiction,
                use_local_model=use_local_model,
                model_offline_only=True,
            )
            return self.state_from_result(source, result)
        except asyncio.CancelledError:
            raise
        except FileNotFoundError:
            return self._error(source, "file_not_found")
        except PermissionError as exc:
            return self._error(source, "permission_denied", str(exc))
        except DocumentLoadError as exc:
            return self._error(source, exc.code, str(exc))
        except MemoryError as exc:
            return self._error(source, "insufficient_memory", str(exc))
        except OSError as exc:
            return self._error(source, "read_failed", str(exc))
        except (RuntimeError, ValueError) as exc:
            return self._error(source, "review_failed", str(exc))

    @staticmethod
    def _require_result(state: DesktopReviewState) -> dict[str, Any]:
        if state.result is None:
            raise ValueError("a completed review is required before export")
        return state.result

    @staticmethod
    def _validate_destination(
        state: DesktopReviewState, destination: Path, suffix: str
    ) -> Path:
        target = Path(destination).expanduser()
        if target.suffix.casefold() != suffix:
            target = target.with_suffix(suffix)
        if state.source_path is not None and _same_path(state.source_path, target):
            raise ValueError(
                "Choose a different output name. AutoCite never overwrites the source document."
            )
        return target

    def export_docx(
        self, state: DesktopReviewState, destination: Path
    ) -> dict[str, Any]:
        self._require_result(state)
        target = self._validate_destination(state, destination, ".docx")
        artifact = export_review_docx(
            state.original_text,
            state.corrected_text,
            tracked=True,
            filename=target.name,
        )
        payload = base64.b64decode(str(artifact["data_base64"]), validate=True)
        _atomic_write(target, payload)
        return {
            **{key: value for key, value in artifact.items() if key != "data_base64"},
            "path": str(target),
        }

    def export_json_report(
        self, state: DesktopReviewState, destination: Path
    ) -> dict[str, Any]:
        self._require_result(state)
        target = self._validate_destination(state, destination, ".json")
        payload = (
            json.dumps(
                build_desktop_report(state),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n"
        ).encode("utf-8")
        _atomic_write(target, payload)
        return {"path": str(target), "size_bytes": len(payload)}


async def run_self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="autocite-self-test-") as directory:
        root = Path(directory)
        source = root / "self-test.txt"
        source.write_text("See 42 USC §1983.", encoding="utf-8")
        controller = DesktopReviewController()
        state = await controller.review_file(source, mode="bluepages")
        if state.error_code or state.result is None:
            raise RuntimeError(state.error_message or "self-test review failed")
        expected = "See 42 U.S.C. § 1983."
        if state.corrected_text != expected:
            raise RuntimeError(
                f"self-test correction mismatch: {state.corrected_text!r}"
            )
        destination = root / "self-test-review.docx"
        export = controller.export_docx(state, destination)
        if not destination.is_file() or destination.stat().st_size <= 0:
            raise RuntimeError("self-test export was not created")
        return {
            "status": "ok",
            "version": application_version(),
            "corrected_text": state.corrected_text,
            "export_size_bytes": int(export["size_bytes"]),
        }


def _local_model_runtime_available() -> bool:
    return bool(
        importlib.util.find_spec("torch") and importlib.util.find_spec("transformers")
    )


def _run_qt() -> int:
    try:
        from PySide6.QtCore import QObject, QSettings, QThread, Qt, Signal, Slot
        from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QFileDialog,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMessageBox,
            QProgressBar,
            QPushButton,
            QSplitter,
            QStatusBar,
            QTabWidget,
            QTextBrowser,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Desktop mode requires the optional 'desktop' dependencies"
        ) from exc

    class ReviewWorker(QObject):
        completed = Signal(object)
        failed = Signal(str)

        def __init__(
            self,
            controller: DesktopReviewController,
            source: Path,
            options: dict[str, Any],
        ) -> None:
            super().__init__()
            self.controller = controller
            self.source = source
            self.options = options

        @Slot()
        def run(self) -> None:
            try:
                state = asyncio.run(
                    self.controller.review_file(self.source, **self.options)
                )
            except Exception as exc:
                self.failed.emit(str(exc))
                return
            self.completed.emit(state)

    class Window(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.controller = DesktopReviewController()
            self.state: DesktopReviewState | None = None
            self.source_path: Path | None = None
            self._thread: QThread | None = None
            self._worker: ReviewWorker | None = None
            self._close_when_finished = False
            self._settings = QSettings("AutoCite", "AutoCite Desktop")

            self.setWindowTitle(
                f"AutoCite {application_version()} | Local Citation Review"
            )
            self.resize(1280, 840)
            saved_geometry = self._settings.value("window/geometry")
            if saved_geometry:
                self.restoreGeometry(saved_geometry)

            root = QWidget()
            layout = QVBoxLayout(root)
            layout.setContentsMargins(18, 16, 18, 12)
            layout.setSpacing(12)

            heading = QLabel(
                "<h1>AutoCite</h1>"
                "<p>Open a legal document. AutoCite reviews citations locally, "
                "applies only safe mechanical fixes, and keeps the source file unchanged.</p>"
            )
            heading.setWordWrap(True)
            layout.addWidget(heading)

            self.drop_hint = QLabel(
                "Drop a TXT, Markdown, DOCX, or searchable PDF here, or choose a file below."
            )
            self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.drop_hint.setFrameShape(QFrame.Shape.StyledPanel)
            self.drop_hint.setMinimumHeight(62)
            self.drop_hint.setAccessibleName("Document drop area")
            layout.addWidget(self.drop_hint)

            file_row = QHBoxLayout()
            self.file_label = QLabel("No document selected")
            self.file_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self.open_button = QPushButton("Choose document")
            self.open_button.clicked.connect(self.open_document)
            self.review_button = QPushButton("Review again")
            self.review_button.clicked.connect(self.start_review)
            self.review_button.setEnabled(False)
            file_row.addWidget(self.file_label, 1)
            file_row.addWidget(self.open_button)
            file_row.addWidget(self.review_button)
            layout.addLayout(file_row)

            options = QGridLayout()
            self.mode = QComboBox()
            self.mode.addItem("Auto-detect (recommended)", "auto")
            self.mode.addItem("Bluepages: court and practice documents", "bluepages")
            self.mode.addItem("Whitepages: academic legal writing", "whitepages")
            self.doc_type = QComboBox()
            self.doc_type.addItem("Auto-detect", "auto")
            self.doc_type.addItem("Brief or motion", "brief")
            self.doc_type.addItem("Legal memorandum", "memorandum")
            self.doc_type.addItem("Law review or journal", "law_review")
            self.doc_type.addItem("Seminar paper", "seminar_paper")
            self.jurisdiction = QComboBox()
            self.jurisdiction.addItem("Auto / general", None)
            self.jurisdiction.addItem("Federal courts", "federal")
            self.jurisdiction.addItem("California", "california")
            self.engine = QComboBox()
            self.engine.addItem("Standard local review (recommended)", False)
            self.engine.addItem("Advanced local model", True)
            if not _local_model_runtime_available():
                model_item = self.engine.model().item(1)
                if model_item is not None:
                    model_item.setEnabled(False)
                    model_item.setToolTip(
                        "The optional model runtime is not included in the portable build."
                    )
            options.addWidget(QLabel("Citation style"), 0, 0)
            options.addWidget(self.mode, 1, 0)
            options.addWidget(QLabel("Document type"), 0, 1)
            options.addWidget(self.doc_type, 1, 1)
            options.addWidget(QLabel("Jurisdiction"), 0, 2)
            options.addWidget(self.jurisdiction, 1, 2)
            options.addWidget(QLabel("Review engine"), 0, 3)
            options.addWidget(self.engine, 1, 3)
            layout.addLayout(options)

            self.progress = QProgressBar()
            self.progress.setRange(0, 0)
            self.progress.setTextVisible(False)
            self.progress.setAccessibleName("Review progress")
            self.progress.hide()
            layout.addWidget(self.progress)

            self.summary_label = QLabel(
                "Ready. Standard review works completely offline and is recommended for 8 GB computers."
            )
            self.summary_label.setWordWrap(True)
            self.summary_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            layout.addWidget(self.summary_label)

            self.tabs = QTabWidget()
            self.corrected = QTextEdit()
            self.corrected.setReadOnly(True)
            self.corrected.setPlaceholderText(
                "The mechanically corrected text will appear here."
            )
            self.original = QTextEdit()
            self.original.setReadOnly(True)
            self.original.setPlaceholderText("The extracted original text will appear here.")
            self.issues = QListWidget()
            self.issues.setAccessibleName("Citation review items")
            self.issue_details = QTextBrowser()
            self.issue_details.setPlaceholderText(
                "Select a review item to see its explanation, confidence, and suggestion."
            )
            self.issues.currentItemChanged.connect(self.show_issue_details)
            issue_splitter = QSplitter(Qt.Orientation.Horizontal)
            issue_splitter.addWidget(self.issues)
            issue_splitter.addWidget(self.issue_details)
            issue_splitter.setSizes([480, 720])
            self.tabs.addTab(self.corrected, "Corrected text")
            self.tabs.addTab(self.original, "Original text")
            self.tabs.addTab(issue_splitter, "Review items")
            layout.addWidget(self.tabs, 1)

            actions = QHBoxLayout()
            self.copy_button = QPushButton("Copy corrected text")
            self.copy_button.clicked.connect(self.copy_corrected)
            self.save_button = QPushButton("Save reviewed Word document")
            self.save_button.clicked.connect(self.save_docx)
            self.report_button = QPushButton("Save audit report")
            self.report_button.clicked.connect(self.save_report)
            for button in (self.copy_button, self.save_button, self.report_button):
                button.setEnabled(False)
                actions.addWidget(button)
            actions.addStretch(1)
            layout.addLayout(actions)

            boundary = QLabel(
                "AutoCite checks supported citation mechanics. It does not determine good-law status, "
                "legal support, controlling authority, or compliance with every local rule."
            )
            boundary.setWordWrap(True)
            layout.addWidget(boundary)

            self.setCentralWidget(root)
            self.setStatusBar(QStatusBar())
            self.statusBar().showMessage("Offline | no telemetry | source file unchanged")
            self.setAcceptDrops(True)

            self._open_shortcut = QShortcut(QKeySequence.StandardKey.Open, self)
            self._open_shortcut.activated.connect(self.open_document)
            self._save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
            self._save_shortcut.activated.connect(self.save_docx)

            self._restore_choices()

        def _restore_choices(self) -> None:
            for name, combo in (
                ("mode", self.mode),
                ("document_type", self.doc_type),
                ("jurisdiction", self.jurisdiction),
            ):
                stored = self._settings.value(f"choices/{name}")
                index = combo.findData(stored)
                if index >= 0:
                    combo.setCurrentIndex(index)

        def _save_settings(self) -> None:
            self._settings.setValue("window/geometry", self.saveGeometry())
            self._settings.setValue("choices/mode", self.mode.currentData())
            self._settings.setValue(
                "choices/document_type", self.doc_type.currentData()
            )
            self._settings.setValue(
                "choices/jurisdiction", self.jurisdiction.currentData()
            )

        def dragEnterEvent(self, event) -> None:
            urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
            if len(urls) == 1:
                path = Path(urls[0].toLocalFile())
                if path.suffix.casefold() in SUPPORTED_SUFFIXES:
                    event.acceptProposedAction()

        def dropEvent(self, event) -> None:
            urls = event.mimeData().urls()
            if urls:
                self.select_source(Path(urls[0].toLocalFile()), review=True)
                event.acceptProposedAction()

        @Slot()
        def open_document(self) -> None:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Open legal document",
                "",
                "Legal documents (*.txt *.md *.markdown *.docx *.pdf)",
            )
            if filename:
                self.select_source(Path(filename), review=True)

        def select_source(self, source: Path, *, review: bool) -> None:
            self.source_path = Path(source)
            self.file_label.setText(str(self.source_path))
            self.file_label.setToolTip(str(self.source_path))
            self.review_button.setEnabled(True)
            if review:
                self.start_review()

        @Slot()
        def start_review(self) -> None:
            if self.source_path is None or self._thread is not None:
                return
            self._clear_result()
            self._set_busy(True)
            self.statusBar().showMessage(
                "Reviewing locally. Larger documents can take a moment."
            )
            options = {
                "document_type": str(self.doc_type.currentData() or "auto"),
                "mode": str(self.mode.currentData() or "auto"),
                "jurisdiction": self.jurisdiction.currentData(),
                "use_local_model": bool(self.engine.currentData()),
            }
            thread = QThread(self)
            worker = ReviewWorker(self.controller, self.source_path, options)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.completed.connect(self.review_finished)
            worker.completed.connect(thread.quit)
            worker.completed.connect(worker.deleteLater)
            worker.failed.connect(self.review_crashed)
            worker.failed.connect(thread.quit)
            worker.failed.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(self.thread_finished)
            self._thread = thread
            self._worker = worker
            thread.start()

        def _set_busy(self, busy: bool) -> None:
            self.progress.setVisible(busy)
            for widget in (
                self.open_button,
                self.review_button,
                self.mode,
                self.doc_type,
                self.jurisdiction,
                self.engine,
            ):
                widget.setEnabled(not busy)
            if not busy:
                self.review_button.setEnabled(self.source_path is not None)

        def _clear_result(self) -> None:
            self.state = None
            self.corrected.clear()
            self.original.clear()
            self.issues.clear()
            self.issue_details.clear()
            self.summary_label.setText("Review in progress. The source file remains unchanged.")
            for button in (self.copy_button, self.save_button, self.report_button):
                button.setEnabled(False)

        @Slot(object)
        def review_finished(self, state: DesktopReviewState) -> None:
            self._set_busy(False)
            self.state = state
            if state.error_code or state.result is None:
                message = state.error_message or friendly_error_message(
                    state.error_code or "review_failed"
                )
                self.summary_label.setText(message)
                self.statusBar().showMessage("Review unavailable | source file unchanged")
                QMessageBox.warning(self, "Review unavailable", message)
                return
            self.load_result(state)

        @Slot(str)
        def review_crashed(self, detail: str) -> None:
            self._set_busy(False)
            message = friendly_error_message("review_failed", detail)
            self.summary_label.setText(message)
            self.statusBar().showMessage("Review unavailable | source file unchanged")
            QMessageBox.critical(self, "Review failed", message)

        @Slot()
        def thread_finished(self) -> None:
            self._thread = None
            self._worker = None
            if self._close_when_finished:
                QApplication.instance().quit()

        def load_result(self, state: DesktopReviewState) -> None:
            assert state.result is not None
            self.corrected.setPlainText(state.corrected_text)
            self.original.setPlainText(state.original_text)
            summary = summarize_review(state.result)
            style = {
                "bluepages": "Bluepages",
                "whitepages": "Whitepages",
            }.get(summary.mode, summary.mode.title())
            status = (
                "No remaining detected mechanical issues"
                if summary.mechanical_review_complete
                else f"{summary.remaining_mechanical_issues} detected mechanical issue(s) remain"
            )
            self.summary_label.setText(
                f"{style} ({summary.mode_confidence} confidence) | "
                f"{summary.citations} citation(s) | {summary.applied_edits} safe fix(es) | "
                f"{summary.review_items} review item(s) | {summary.unsupported_items} outside coverage. "
                f"{status}."
            )
            rows = iter_desktop_issues(state.result)
            self.issues.clear()
            for row in rows:
                label = _CORRECTION_LABELS.get(
                    row["correction_level"], row["correction_level"].replace("_", " ").title()
                )
                item = QListWidgetItem(
                    f"{label} | {row['code']}\n{row['message']}"
                )
                item.setData(Qt.ItemDataRole.UserRole, row)
                self.issues.addItem(item)
            if not rows:
                item = QListWidgetItem("No manual review items were detected.")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.issues.addItem(item)
            for button in (self.copy_button, self.save_button, self.report_button):
                button.setEnabled(True)
            self.tabs.setCurrentIndex(0)
            self.statusBar().showMessage(
                "Review complete | processed locally | source file unchanged"
            )

        @Slot(object, object)
        def show_issue_details(
            self, current: QListWidgetItem | None, previous: QListWidgetItem | None
        ) -> None:
            del previous
            if current is None:
                self.issue_details.clear()
                return
            row = current.data(Qt.ItemDataRole.UserRole)
            if not isinstance(row, dict):
                self.issue_details.setPlainText(current.text())
                return
            position = (
                f"Characters {row['start']} to {row['end']}"
                if row["start"] >= 0 and row["end"] >= 0
                else "Document location unavailable"
            )
            lines = [
                row["message"],
                "",
                f"Status: {_CORRECTION_LABELS.get(row['correction_level'], row['correction_level'])}",
                f"Severity: {row['severity']}",
                f"Confidence: {row['confidence']}",
                f"Location: {position}",
            ]
            if row["rule"]:
                lines.append(f"Rule family: {row['rule']}")
            if row["original"]:
                lines.extend(("", f"Original: {row['original']}"))
            if row["suggestion"]:
                lines.append(f"Suggestion: {row['suggestion']}")
            if row["missing_facts"]:
                lines.append(
                    "Missing facts: " + ", ".join(row["missing_facts"])
                )
            lines.extend(("", f"Provenance: {row['provenance']}"))
            self.issue_details.setPlainText("\n".join(lines))

        @Slot()
        def copy_corrected(self) -> None:
            if self.state is None or self.state.result is None:
                return
            QApplication.clipboard().setText(self.state.corrected_text)
            self.statusBar().showMessage("Corrected text copied to the clipboard")

        @Slot()
        def save_docx(self) -> None:
            if self.state is None or self.state.result is None:
                return
            source = self.state.source_path or Path.cwd() / "document.txt"
            suggested = default_export_path(source)
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save reviewed Word document",
                str(suggested),
                "Word document (*.docx)",
            )
            if not filename:
                return
            try:
                metadata = self.controller.export_docx(self.state, Path(filename))
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Export failed",
                    f"{exc}\n\nThe source file was not changed.",
                )
                return
            self.statusBar().showMessage(f"Saved reviewed document: {metadata['path']}")

        @Slot()
        def save_report(self) -> None:
            if self.state is None or self.state.result is None:
                return
            source = self.state.source_path or Path.cwd() / "document.txt"
            suggested = default_export_path(source, extension=".json")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save AutoCite audit report",
                str(suggested),
                "JSON report (*.json)",
            )
            if not filename:
                return
            try:
                metadata = self.controller.export_json_report(
                    self.state, Path(filename)
                )
            except Exception as exc:
                QMessageBox.critical(self, "Report export failed", str(exc))
                return
            self.statusBar().showMessage(f"Saved audit report: {metadata['path']}")

        def closeEvent(self, event: QCloseEvent) -> None:
            self._save_settings()
            if self._thread is not None and self._thread.isRunning():
                answer = QMessageBox.question(
                    self,
                    "Review in progress",
                    "AutoCite is still reviewing this document. Close automatically when the review finishes?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    self._close_when_finished = True
                    self.hide()
                event.ignore()
                return
            event.accept()

    application = QApplication(sys.argv)
    application.setApplicationName("AutoCite Desktop")
    application.setOrganizationName("AutoCite")
    window = Window()
    window.show()
    return application.exec()


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--version" in arguments:
        print(application_version())
        return 0
    if "--self-test" in arguments:
        try:
            result = asyncio.run(run_self_test())
        except Exception as exc:
            print(f"AutoCite self-test failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0
    return _run_qt()


if __name__ == "__main__":
    raise SystemExit(main())
