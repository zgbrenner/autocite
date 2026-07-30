from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any, Sequence

from .desktop import (
    SUPPORTED_SUFFIXES,
    application_version,
    default_export_path,
    friendly_error_message,
)
from .desktop_preservation import (
    PreservationDesktopReviewController,
    PreservationDesktopReviewState,
)
from .review_session import ReviewDecision, ReviewItem
from .review_view_model import DesktopReviewViewModel, ReviewFilter


_DECISION_LABELS = {
    ReviewDecision.ACCEPTED: "Accepted",
    ReviewDecision.REJECTED: "Rejected",
    ReviewDecision.PENDING: "Pending review",
}
_CORRECTION_LABELS = {
    "safe_auto_fix": "Safe mechanical change",
    "suggested_fix": "Suggested change",
    "review_required": "Human review required",
    "unsupported": "Outside current coverage",
}


def review_item_label(item: ReviewItem) -> str:
    decision = _DECISION_LABELS[item.decision]
    correction = _CORRECTION_LABELS.get(
        item.correction_level,
        item.correction_level.replace("_", " ").title(),
    )
    return f"{decision} | {correction} | {item.code}\n{item.message}"


def review_item_details(item: ReviewItem) -> str:
    position = (
        f"Characters {item.start} through {item.end}"
        if item.start >= 0 and item.end >= item.start
        else "Document location unavailable"
    )
    lines = [
        item.message,
        "",
        f"Decision: {_DECISION_LABELS[item.decision]}",
        f"Status: {_CORRECTION_LABELS.get(item.correction_level, item.correction_level)}",
        f"Severity: {item.severity}",
        f"Confidence: {item.confidence}",
        f"Location: {position}",
    ]
    if item.source_type:
        lines.append(f"Source type: {item.source_type}")
    if item.rule:
        lines.append(f"Rule family: {item.rule}")
    if item.original:
        lines.extend(("", f"Original: {item.original}"))
    if item.suggestion is not None:
        lines.append(f"Suggested text: {item.suggestion}")
    if item.missing_facts:
        lines.append("Missing facts: " + ", ".join(item.missing_facts))
    lines.extend(("", f"Provenance: {item.provenance}"))
    if item.correction_level == "unsupported":
        lines.extend(
            (
                "",
                "This item remains in the audit report even when marked reviewed, because it is outside AutoCite's current rule coverage.",
            )
        )
    elif item.kind.value == "annotation":
        lines.extend(
            (
                "",
                "Accept marks this review item resolved. Reject or Pending keeps it in the exported review record.",
            )
        )
    return "\n".join(lines)


def _local_model_runtime_available() -> bool:
    return bool(
        importlib.util.find_spec("torch")
        and importlib.util.find_spec("transformers")
    )


def run_review_workspace(argv: Sequence[str] | None = None) -> int:
    try:
        from PySide6.QtCore import QObject, QSettings, QThread, Qt, Signal, Slot
        from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut, QTextCursor
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QFileDialog,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
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
            controller: PreservationDesktopReviewController,
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
            self.controller = PreservationDesktopReviewController()
            self.state: PreservationDesktopReviewState | None = None
            self.model: DesktopReviewViewModel | None = None
            self.source_path: Path | None = None
            self._thread: QThread | None = None
            self._worker: ReviewWorker | None = None
            self._close_when_finished = False
            self._settings = QSettings("AutoCite", "AutoCite Desktop")

            self.setWindowTitle(
                f"AutoCite {application_version()} | Local Citation Review"
            )
            self.resize(1380, 900)
            saved_geometry = self._settings.value("window/geometry")
            if saved_geometry:
                self.restoreGeometry(saved_geometry)

            root = QWidget()
            layout = QVBoxLayout(root)
            layout.setContentsMargins(18, 16, 18, 12)
            layout.setSpacing(10)

            heading = QLabel(
                "<h1>AutoCite</h1>"
                "<p>Review legal citations locally, inspect every change, and keep the source file unchanged.</p>"
            )
            heading.setWordWrap(True)
            layout.addWidget(heading)

            self.drop_hint = QLabel(
                "Drop a TXT, Markdown, DOCX, or searchable PDF here, or choose a document below."
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
            self.open_button.setAccessibleName("Choose a legal document")
            self.open_button.clicked.connect(self.open_document)
            self.review_button = QPushButton("Review again")
            self.review_button.setAccessibleName("Review the selected document again")
            self.review_button.setEnabled(False)
            self.review_button.clicked.connect(self.start_review)
            file_row.addWidget(self.file_label, 1)
            file_row.addWidget(self.open_button)
            file_row.addWidget(self.review_button)
            layout.addLayout(file_row)

            options = QGridLayout()
            self.mode = QComboBox()
            self.mode.addItem("Auto-detect (recommended)", "auto")
            self.mode.addItem("Bluepages: court and practice documents", "bluepages")
            self.mode.addItem("Whitepages: academic legal writing", "whitepages")
            self.mode.setAccessibleName("Citation style")

            self.doc_type = QComboBox()
            self.doc_type.addItem("Auto-detect", "auto")
            self.doc_type.addItem("Brief or motion", "brief")
            self.doc_type.addItem("Legal memorandum", "memorandum")
            self.doc_type.addItem("Law review or journal", "law_review")
            self.doc_type.addItem("Seminar paper", "seminar_paper")
            self.doc_type.setAccessibleName("Document type")

            self.jurisdiction = QComboBox()
            self.jurisdiction.addItem("Auto or general", None)
            self.jurisdiction.addItem("Federal courts", "federal")
            self.jurisdiction.addItem("California", "california")
            self.jurisdiction.setAccessibleName("Jurisdiction profile")

            self.engine = QComboBox()
            self.engine.addItem("Standard local review (recommended)", False)
            self.engine.addItem("Advanced local model", True)
            self.engine.setAccessibleName("Review engine")
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
                "Ready. Standard review works offline and is recommended for 8 GB computers."
            )
            self.summary_label.setWordWrap(True)
            self.summary_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self.summary_label.setAccessibleName("Review summary")
            layout.addWidget(self.summary_label)

            filters = QHBoxLayout()
            self.decision_filter = QComboBox()
            for label, value in (
                ("All review items", ReviewFilter.ALL),
                ("Accepted", ReviewFilter.ACCEPTED),
                ("Pending", ReviewFilter.PENDING),
                ("Rejected", ReviewFilter.REJECTED),
                ("Safe changes", ReviewFilter.SAFE),
                ("Human review required", ReviewFilter.REVIEW_REQUIRED),
                ("Outside coverage", ReviewFilter.UNSUPPORTED),
            ):
                self.decision_filter.addItem(label, value.value)
            self.decision_filter.setAccessibleName("Review item status filter")
            self.decision_filter.currentIndexChanged.connect(self.apply_filters)

            self.severity_filter = QComboBox()
            self.severity_filter.addItem("All severities", None)
            for value in ("error", "warning", "info"):
                self.severity_filter.addItem(value.title(), value)
            self.severity_filter.setAccessibleName("Severity filter")
            self.severity_filter.currentIndexChanged.connect(self.apply_filters)

            self.source_filter = QComboBox()
            self.source_filter.addItem("All source types", None)
            self.source_filter.setAccessibleName("Citation source type filter")
            self.source_filter.currentIndexChanged.connect(self.apply_filters)

            self.search = QLineEdit()
            self.search.setPlaceholderText("Search review items")
            self.search.setClearButtonEnabled(True)
            self.search.setAccessibleName("Search review items")
            self.search.textChanged.connect(self.apply_filters)

            filters.addWidget(self.decision_filter)
            filters.addWidget(self.severity_filter)
            filters.addWidget(self.source_filter)
            filters.addWidget(self.search, 1)
            layout.addLayout(filters)

            main_splitter = QSplitter(Qt.Orientation.Horizontal)
            self.main_splitter = main_splitter

            review_panel = QWidget()
            review_layout = QVBoxLayout(review_panel)
            review_layout.setContentsMargins(0, 0, 0, 0)
            review_layout.addWidget(QLabel("Review items"))
            self.items = QListWidget()
            self.items.setAccessibleName("Citation review items")
            self.items.currentItemChanged.connect(self.item_selected)
            review_layout.addWidget(self.items, 1)

            item_actions = QGridLayout()
            self.accept_button = QPushButton("Accept or mark reviewed")
            self.reject_button = QPushButton("Reject")
            self.reset_button = QPushButton("Reset to pending")
            self.accept_all_button = QPushButton("Accept all safe changes")
            self.previous_button = QPushButton("Previous")
            self.next_button = QPushButton("Next")
            self.undo_button = QPushButton("Undo")
            self.redo_button = QPushButton("Redo")
            for button, name in (
                (self.accept_button, "Accept the selected change or mark the selected item reviewed"),
                (self.reject_button, "Reject the selected review item"),
                (self.reset_button, "Reset the selected item to pending review"),
                (self.accept_all_button, "Accept every high-confidence safe mechanical change"),
                (self.previous_button, "Select the previous visible review item"),
                (self.next_button, "Select the next visible review item"),
                (self.undo_button, "Undo the last review decision"),
                (self.redo_button, "Redo the last review decision"),
            ):
                button.setAccessibleName(name)
                button.setEnabled(False)
            self.accept_button.clicked.connect(self.accept_current)
            self.reject_button.clicked.connect(self.reject_current)
            self.reset_button.clicked.connect(self.reset_current)
            self.accept_all_button.clicked.connect(self.accept_all_safe)
            self.previous_button.clicked.connect(self.previous_item)
            self.next_button.clicked.connect(self.next_item)
            self.undo_button.clicked.connect(self.undo)
            self.redo_button.clicked.connect(self.redo)
            item_actions.addWidget(self.accept_button, 0, 0, 1, 2)
            item_actions.addWidget(self.reject_button, 0, 2)
            item_actions.addWidget(self.reset_button, 0, 3)
            item_actions.addWidget(self.accept_all_button, 1, 0, 1, 2)
            item_actions.addWidget(self.previous_button, 1, 2)
            item_actions.addWidget(self.next_button, 1, 3)
            item_actions.addWidget(self.undo_button, 2, 0)
            item_actions.addWidget(self.redo_button, 2, 1)
            review_layout.addLayout(item_actions)
            main_splitter.addWidget(review_panel)

            self.tabs = QTabWidget()
            self.corrected = QTextEdit()
            self.corrected.setReadOnly(True)
            self.corrected.setPlaceholderText(
                "The corrected preview will reflect the changes you currently accept."
            )
            self.corrected.setAccessibleName("Corrected document preview")
            self.original = QTextEdit()
            self.original.setReadOnly(True)
            self.original.setPlaceholderText("The extracted original text will appear here.")
            self.original.setAccessibleName("Original document text")
            self.details = QTextBrowser()
            self.details.setPlaceholderText(
                "Select a review item to inspect its explanation, confidence, source range, and provenance."
            )
            self.details.setAccessibleName("Selected review item details")
            self.tabs.addTab(self.corrected, "Corrected preview")
            self.tabs.addTab(self.original, "Original text")
            self.tabs.addTab(self.details, "Item details")
            main_splitter.addWidget(self.tabs)
            main_splitter.setSizes([500, 820])
            saved_splitter = self._settings.value("window/main_splitter")
            if saved_splitter:
                main_splitter.restoreState(saved_splitter)
            layout.addWidget(main_splitter, 1)

            exports = QHBoxLayout()
            self.copy_button = QPushButton("Copy corrected text")
            self.save_button = QPushButton("Save reviewed Word document")
            self.report_button = QPushButton("Save audit report")
            self.final_review_button = QPushButton("Final review summary")
            self.copy_button.clicked.connect(self.copy_corrected)
            self.save_button.clicked.connect(self.save_docx)
            self.report_button.clicked.connect(self.save_report)
            self.final_review_button.clicked.connect(self.show_final_review)
            for button, name in (
                (self.copy_button, "Copy the corrected preview to the clipboard"),
                (self.save_button, "Save a reviewed Word document"),
                (self.report_button, "Save a JSON audit report"),
                (self.final_review_button, "Show the final review checklist"),
            ):
                button.setAccessibleName(name)
                button.setEnabled(False)
                exports.addWidget(button)
            exports.addStretch(1)
            layout.addLayout(exports)

            boundary = QLabel(
                "AutoCite checks supported citation mechanics. It does not determine good-law status, legal support, controlling authority, or compliance with every local rule."
            )
            boundary.setWordWrap(True)
            boundary.setAccessibleName("AutoCite accuracy boundary")
            layout.addWidget(boundary)

            self.setCentralWidget(root)
            self.setStatusBar(QStatusBar())
            self.statusBar().showMessage(
                "Offline | no telemetry | source file unchanged"
            )
            self.setAcceptDrops(True)

            self._open_shortcut = QShortcut(QKeySequence.StandardKey.Open, self)
            self._open_shortcut.activated.connect(self.open_document)
            self._save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
            self._save_shortcut.activated.connect(self.save_docx)
            self._undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
            self._undo_shortcut.activated.connect(self.undo)
            self._redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
            self._redo_shortcut.activated.connect(self.redo)
            self._next_shortcut = QShortcut(QKeySequence("F8"), self)
            self._next_shortcut.activated.connect(self.next_item)
            self._previous_shortcut = QShortcut(QKeySequence("Shift+F8"), self)
            self._previous_shortcut.activated.connect(self.previous_item)

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
            self._settings.setValue(
                "window/main_splitter", self.main_splitter.saveState()
            )
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
            self.model = None
            self.corrected.clear()
            self.original.clear()
            self.details.clear()
            self.items.clear()
            self.summary_label.setText(
                "Review in progress. The source file remains unchanged."
            )
            self._set_workspace_enabled(False)

        def _set_workspace_enabled(self, enabled: bool) -> None:
            for widget in (
                self.copy_button,
                self.save_button,
                self.report_button,
                self.final_review_button,
                self.accept_all_button,
                self.decision_filter,
                self.severity_filter,
                self.source_filter,
                self.search,
            ):
                widget.setEnabled(enabled)
            self._update_item_buttons()

        @Slot(object)
        def review_finished(self, state: PreservationDesktopReviewState) -> None:
            self.state = state
            if state.error_code or state.result is None:
                message = state.error_message or friendly_error_message(
                    state.error_code or "review_failed"
                )
                self.summary_label.setText(message)
                self.statusBar().showMessage(
                    "Review unavailable | source file unchanged"
                )
                QMessageBox.warning(self, "Review unavailable", message)
                return
            self.load_result(state)

        @Slot(str)
        def review_crashed(self, detail: str) -> None:
            message = friendly_error_message("review_failed", detail)
            self.summary_label.setText(message)
            self.statusBar().showMessage(
                "Review unavailable | source file unchanged"
            )
            QMessageBox.critical(self, "Review failed", message)

        @Slot()
        def thread_finished(self) -> None:
            self._thread = None
            self._worker = None
            self._set_busy(False)
            if self._close_when_finished:
                QApplication.instance().quit()

        def load_result(self, state: PreservationDesktopReviewState) -> None:
            assert state.result is not None
            if state.review_session is None:
                raise RuntimeError("completed desktop review has no review session")
            self.model = DesktopReviewViewModel(state.review_session)
            self.original.setPlainText(state.original_text)
            self._populate_source_types()
            self._set_workspace_enabled(True)
            self.refresh_workspace()
            warning = state.preservation_warning
            if warning:
                self.statusBar().showMessage(
                    "Review complete | DOCX preservation unavailable | source unchanged"
                )
                QMessageBox.warning(self, "DOCX preservation unavailable", warning)
            else:
                self.statusBar().showMessage(
                    "Review complete | processed locally | source file unchanged"
                )

        def _populate_source_types(self) -> None:
            assert self.model is not None
            current = self.source_filter.currentData()
            self.source_filter.blockSignals(True)
            self.source_filter.clear()
            self.source_filter.addItem("All source types", None)
            for source_type in sorted(
                {
                    item.source_type
                    for item in self.model.session.items
                    if item.source_type
                }
            ):
                self.source_filter.addItem(source_type.replace("_", " ").title(), source_type)
            index = self.source_filter.findData(current)
            self.source_filter.setCurrentIndex(index if index >= 0 else 0)
            self.source_filter.blockSignals(False)

        @Slot()
        def apply_filters(self) -> None:
            if self.model is None:
                return
            self.model.set_filter(str(self.decision_filter.currentData() or "all"))
            self.model.set_severity(self.severity_filter.currentData())
            self.model.set_source_type(self.source_filter.currentData())
            self.model.set_search(self.search.text())
            self.refresh_workspace()

        def refresh_workspace(self) -> None:
            if self.model is None or self.state is None or self.state.result is None:
                return
            try:
                preview = self.model.render_corrected_text(self.state.original_text)
            except ValueError as exc:
                preview = self.state.corrected_text
                self.statusBar().showMessage(
                    f"Preview fallback used: {exc} | source file unchanged"
                )
            self.corrected.setPlainText(preview)

            workspace = self.model.summary()
            detection = self.state.result.get("mode_detection")
            confidence = (
                str(detection.get("confidence") or "unknown")
                if isinstance(detection, dict)
                else "unknown"
            )
            mode = str(self.state.result.get("mode") or "unknown")
            self.summary_label.setText(
                f"{mode.title()} ({confidence} confidence) | "
                f"{workspace.total} review item(s) | "
                f"{workspace.accepted} accepted | {workspace.pending} pending | "
                f"{workspace.rejected} rejected | {workspace.unsupported} outside coverage."
            )

            current_id = (
                self.model.current_item.item_id
                if self.model.current_item is not None
                else None
            )
            self.items.blockSignals(True)
            self.items.clear()
            selected_row = -1
            for row_index, item in enumerate(self.model.visible_items):
                list_item = QListWidgetItem(review_item_label(item))
                list_item.setData(Qt.ItemDataRole.UserRole, item.item_id)
                list_item.setData(
                    Qt.ItemDataRole.AccessibleTextRole,
                    review_item_label(item).replace("\n", ". "),
                )
                list_item.setToolTip(review_item_details(item))
                self.items.addItem(list_item)
                if item.item_id == current_id:
                    selected_row = row_index
            if self.items.count() == 0:
                empty = QListWidgetItem(
                    "No review items match the current filters."
                )
                empty.setFlags(empty.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.items.addItem(empty)
            elif selected_row >= 0:
                self.items.setCurrentRow(selected_row)
            else:
                self.items.setCurrentRow(0)
            self.items.blockSignals(False)
            self._display_current_item()
            self._update_item_buttons()

        def _selected_item_id(self) -> str | None:
            current = self.items.currentItem()
            if current is None:
                return None
            value = current.data(Qt.ItemDataRole.UserRole)
            return str(value) if value else None

        @Slot(object, object)
        def item_selected(self, current, previous) -> None:
            del previous
            if self.model is None or current is None:
                self.details.clear()
                self._update_item_buttons()
                return
            item_id = current.data(Qt.ItemDataRole.UserRole)
            if not item_id:
                self.details.setPlainText(current.text())
                self._update_item_buttons()
                return
            try:
                self.model.select(str(item_id))
            except KeyError:
                return
            self._display_current_item()
            self._update_item_buttons()

        def _display_current_item(self) -> None:
            if self.model is None:
                self.details.clear()
                return
            item = self.model.current_item
            if item is None:
                self.details.setPlainText(
                    "No review items match the current filters."
                )
                return
            self.details.setPlainText(review_item_details(item))
            self._highlight_original(item)

        def _highlight_original(self, item: ReviewItem) -> None:
            if item.start < 0 or item.end < item.start:
                return
            text_length = len(self.original.toPlainText())
            start = min(item.start, text_length)
            end = min(item.end, text_length)
            cursor = self.original.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            self.original.setTextCursor(cursor)
            self.original.ensureCursorVisible()

        def _update_item_buttons(self) -> None:
            has_model = self.model is not None
            current = self.model.current_item if has_model else None
            enabled = current is not None
            self.accept_button.setEnabled(enabled)
            self.reject_button.setEnabled(enabled)
            self.reset_button.setEnabled(enabled)
            self.previous_button.setEnabled(enabled)
            self.next_button.setEnabled(enabled)
            self.undo_button.setEnabled(bool(has_model and self.model.can_undo))
            self.redo_button.setEnabled(bool(has_model and self.model.can_redo))
            self.accept_all_button.setEnabled(has_model)

        def _apply_current_decision(self, decision: ReviewDecision) -> None:
            if self.model is None or self.model.current_item is None:
                return
            item_id = self.model.current_item.item_id
            if decision is ReviewDecision.ACCEPTED:
                self.model.accept(item_id)
            elif decision is ReviewDecision.REJECTED:
                self.model.reject(item_id)
            else:
                self.model.reset(item_id)
            self.refresh_workspace()

        @Slot()
        def accept_current(self) -> None:
            self._apply_current_decision(ReviewDecision.ACCEPTED)

        @Slot()
        def reject_current(self) -> None:
            self._apply_current_decision(ReviewDecision.REJECTED)

        @Slot()
        def reset_current(self) -> None:
            self._apply_current_decision(ReviewDecision.PENDING)

        @Slot()
        def accept_all_safe(self) -> None:
            if self.model is None:
                return
            self.model.accept_all_safe()
            self.refresh_workspace()

        @Slot()
        def undo(self) -> None:
            if self.model is None:
                return
            self.model.undo()
            self.refresh_workspace()

        @Slot()
        def redo(self) -> None:
            if self.model is None:
                return
            self.model.redo()
            self.refresh_workspace()

        @Slot()
        def next_item(self) -> None:
            if self.model is None:
                return
            item = self.model.next_item()
            if item is not None:
                self._select_list_item(item.item_id)

        @Slot()
        def previous_item(self) -> None:
            if self.model is None:
                return
            item = self.model.previous_item()
            if item is not None:
                self._select_list_item(item.item_id)

        def _select_list_item(self, item_id: str) -> None:
            for row in range(self.items.count()):
                candidate = self.items.item(row)
                if candidate.data(Qt.ItemDataRole.UserRole) == item_id:
                    self.items.setCurrentRow(row)
                    return
            self.refresh_workspace()

        @Slot()
        def copy_corrected(self) -> None:
            if self.model is None:
                return
            QApplication.clipboard().setText(self.corrected.toPlainText())
            self.statusBar().showMessage(
                "Corrected preview copied to the clipboard"
            )

        def _confirm_unresolved(self) -> bool:
            if self.model is None:
                return False
            summary = self.model.summary()
            if summary.pending == 0 and summary.unsupported == 0:
                return True
            answer = QMessageBox.question(
                self,
                "Unresolved review items",
                f"{summary.pending} item(s) remain pending and {summary.unsupported} item(s) are outside current coverage. Export them in the review record anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return answer == QMessageBox.StandardButton.Yes

        @Slot()
        def save_docx(self) -> None:
            if (
                self.state is None
                or self.state.result is None
                or self.model is None
                or not self._confirm_unresolved()
            ):
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
                metadata = self.controller.export_docx(
                    self.state,
                    Path(filename),
                    decisions=self.model.decisions,
                )
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Export failed",
                    f"{exc}\n\nThe source file was not changed.",
                )
                return
            mode = str(metadata.get("preservation_mode") or "reviewed_text")
            self.statusBar().showMessage(
                f"Saved reviewed document using {mode}: {metadata['path']}"
            )

        @Slot()
        def save_report(self) -> None:
            if self.state is None or self.state.result is None or self.model is None:
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
                    self.state,
                    Path(filename),
                    decisions=self.model.decisions,
                )
            except Exception as exc:
                QMessageBox.critical(
                    self, "Report export failed", str(exc)
                )
                return
            self.statusBar().showMessage(
                f"Saved audit report: {metadata['path']}"
            )

        @Slot()
        def show_final_review(self) -> None:
            if self.model is None:
                return
            summary = self.model.summary()
            preservation = (
                "Original DOCX preservation is ready."
                if self.state is not None and self.state.source_bytes is not None
                else "A text-level reviewed DOCX will be produced for this source format."
            )
            QMessageBox.information(
                self,
                "Final review summary",
                "\n".join(
                    (
                        f"Accepted: {summary.accepted}",
                        f"Pending: {summary.pending}",
                        f"Rejected: {summary.rejected}",
                        f"Outside current coverage: {summary.unsupported}",
                        "",
                        preservation,
                        "The source file remains unchanged.",
                        "AutoCite has not determined good-law status or legal support.",
                    )
                ),
            )

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

    arguments = list(argv or ())
    existing = QApplication.instance()
    application = existing or QApplication([sys.argv[0], *arguments])
    application.setApplicationName("AutoCite Desktop")
    application.setOrganizationName("AutoCite")
    window = Window()
    window.show()
    if existing is not None:
        return 0
    return application.exec()
