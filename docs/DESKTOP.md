# AutoCite Desktop

Install `autocite-mcp[desktop]` and run `autocite-desktop`. The application uses the same in-process Python core as CLI and MCP.

The desktop accepts TXT, Markdown, DOCX, and text PDF by file picker or drag/drop. Users choose document type, Bluepages/Whitepages, and deterministic-only or local-ML-enhanced review. Original and mechanically corrected text appear side by side with severity, confidence, issue code, and deterministic/model/retrieval provenance. The status bar always distinguishes mechanical review from legal verification.

Export writes a reviewed DOCX only to the selected location. The source file is never modified. Unsupported formats, scanned PDFs, insufficient memory, missing/corrupted models, malformed documents, ambiguous modes, incomplete metadata, and export errors return visible messages while preserving the original.

The current PySide shell exposes the core review and issue workflow. Deeper document-outline, footnote, citation-inventory, graph-inspector, per-change accept/reject, and first-run model setup views remain identified release work and should not be inferred from the initial shell.

`packaging/autocite-desktop.spec` and the desktop workflow build signable Windows, macOS, and Linux bundles plus SHA-256 checksums. Platform signing credentials and notarization are intentionally supplied only in a protected release environment.
