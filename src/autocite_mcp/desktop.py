from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .documents import DocumentLoadError
from .tools import export_review_docx, review_uploaded_document


SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".docx", ".pdf"}


@dataclass(frozen=True)
class DesktopReviewState:
    original_text: str
    corrected_text: str
    result: dict[str, Any] | None
    error_code: str | None = None
    error_message: str | None = None


class DesktopReviewController:
    """UI-independent controller using the same core package as CLI and MCP."""

    async def review_file(
        self,
        path: Path,
        *,
        document_type: str = "auto",
        mode: str = "auto",
        jurisdiction: str | None = None,
        use_local_model: bool = False,
    ) -> DesktopReviewState:
        source = Path(path)
        if source.suffix.casefold() not in SUPPORTED_SUFFIXES:
            return DesktopReviewState(
                "",
                "",
                None,
                "unsupported_format",
                "Choose TXT, Markdown, DOCX, or text PDF.",
            )
        payload = source.read_bytes()
        try:
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
            return DesktopReviewState(
                str(result["original_text"]),
                str(result["corrected_text"]),
                result,
            )
        except DocumentLoadError as exc:
            return DesktopReviewState("", "", None, exc.code, str(exc))
        except (MemoryError, RuntimeError, ValueError) as exc:
            code = (
                "insufficient_memory"
                if isinstance(exc, MemoryError)
                else "review_failed"
            )
            return DesktopReviewState("", "", None, code, str(exc))

    def export_docx(
        self, state: DesktopReviewState, destination: Path
    ) -> dict[str, Any]:
        if state.result is None:
            raise ValueError("a completed review is required before export")
        artifact = export_review_docx(
            state.original_text,
            state.corrected_text,
            tracked=True,
            filename=Path(destination).name,
        )
        Path(destination).write_bytes(base64.b64decode(artifact["data_base64"]))
        return {key: value for key, value in artifact.items() if key != "data_base64"}


def _run_qt() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QFileDialog,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSplitter,
            QStatusBar,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Desktop mode requires the optional 'desktop' dependencies"
        ) from exc

    class Window(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.controller = DesktopReviewController()
            self.state: DesktopReviewState | None = None
            self.setWindowTitle("AutoCite — Local Citation Review")
            self.resize(1280, 820)
            root = QWidget()
            layout = QVBoxLayout(root)
            controls = QHBoxLayout()
            self.mode = QComboBox()
            self.mode.addItems(["auto", "bluepages", "whitepages"])
            self.doc_type = QComboBox()
            self.doc_type.addItems(
                ["auto", "brief", "memorandum", "law_review", "seminar_paper"]
            )
            self.engine = QComboBox()
            self.engine.addItems(["deterministic-only", "local-ML-enhanced"])
            open_button = QPushButton("Open document")
            open_button.clicked.connect(self.open_document)
            export_button = QPushButton("Export reviewed DOCX")
            export_button.clicked.connect(self.export_document)
            for widget in (
                QLabel("Mode"),
                self.mode,
                QLabel("Document type"),
                self.doc_type,
                QLabel("Review"),
                self.engine,
                open_button,
                export_button,
            ):
                controls.addWidget(widget)
            layout.addLayout(controls)
            splitter = QSplitter(Qt.Orientation.Horizontal)
            self.original = QTextEdit()
            self.original.setReadOnly(True)
            self.original.setPlaceholderText("Original document")
            self.corrected = QTextEdit()
            self.corrected.setReadOnly(True)
            self.corrected.setPlaceholderText("Mechanically corrected text")
            self.issues = QListWidget()
            self.issues.setAccessibleName("Citation issues and confidence")
            splitter.addWidget(self.original)
            splitter.addWidget(self.corrected)
            splitter.addWidget(self.issues)
            layout.addWidget(splitter)
            self.setCentralWidget(root)
            self.setStatusBar(QStatusBar())
            self.statusBar().showMessage(
                "Offline • no telemetry • not legally verified"
            )
            self.setAcceptDrops(True)

        def dragEnterEvent(self, event):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()

        def dropEvent(self, event):
            urls = event.mimeData().urls()
            if urls:
                self.run_review(Path(urls[0].toLocalFile()))

        def open_document(self):
            filename, _ = QFileDialog.getOpenFileName(
                self, "Open legal document", "", "Documents (*.txt *.md *.docx *.pdf)"
            )
            if filename:
                self.run_review(Path(filename))

        def run_review(self, path: Path):
            self.statusBar().showMessage("Reviewing locally…")
            state = asyncio.run(
                self.controller.review_file(
                    path,
                    document_type=self.doc_type.currentText(),
                    mode=self.mode.currentText(),
                    use_local_model=self.engine.currentIndex() == 1,
                )
            )
            self.state = state
            if state.error_code:
                QMessageBox.warning(
                    self,
                    "Review unavailable",
                    f"{state.error_code}: {state.error_message}\nThe original file was not changed.",
                )
                return
            self.original.setPlainText(state.original_text)
            self.corrected.setPlainText(state.corrected_text)
            self.issues.clear()
            for item in state.result.get("rule_findings", []):
                self.issues.addItem(
                    f"{item['severity']} • {item['confidence']} • {item['provenance']}\n{item['issue_code']}: {item['explanation']}"
                )
            self.statusBar().showMessage(
                "Mechanically reviewed locally • source/human review findings remain"
            )

        def export_document(self):
            if not self.state or not self.state.result:
                return
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export reviewed DOCX", "autocite-review.docx", "Word (*.docx)"
            )
            if filename:
                try:
                    self.controller.export_docx(self.state, Path(filename))
                except Exception as exc:
                    QMessageBox.critical(
                        self,
                        "Export failed",
                        f"{exc}\nThe original file was not changed.",
                    )

    application = QApplication([])
    window = Window()
    window.show()
    return application.exec()


def main() -> None:
    raise SystemExit(_run_qt())
