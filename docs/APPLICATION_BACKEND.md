# AutoCite Application Backend

AutoCite's application layer is the shared local backend for the MCP server, the Tauri desktop editor, and later Word, Google Docs, Outlook, and Gmail clients. It does not replace the deterministic citation engine. It adds durable document state and a narrow application protocol around that engine.

## Design guarantees

1. **The imported source is immutable.** Each session stores `original_text` separately from `working_text`.
2. **Autosaves cannot silently overwrite newer edits.** Every write supplies `expected_revision`; stale writes return a revision conflict.
3. **Automatic edits remain deterministic.** An issue can be applied only when it is marked as a safe automatic fix, contains an exact source span, still matches the current document, and supplies a replacement.
4. **Review state is revision-bound.** Editing the document invalidates the prior review rather than pretending offsets remain current.
5. **Context reduction is reversible and measured.** The reducer selects exact source ranges, protects legal anchors, reports savings, and bypasses reduction when savings are negligible. It never replaces full-document deterministic review.
6. **Desktop traffic stays local.** The application API binds to loopback by default and requires a bearer token for every endpoint other than health.
7. **The database is local.** Sessions, review jobs, decisions, and export audit records are stored in SQLite with WAL mode and foreign-key enforcement.

## Components

| Module | Responsibility |
|---|---|
| `application.models` | Session, job, status, and decision contracts. |
| `application.store` | SQLite persistence and optimistic revisions. |
| `application.context_reducer` | Conservative legal-aware range selection and compression metrics. |
| `application.engine_adapter` | Late-bound bridge to AutoCite's existing review engine. |
| `application.service` | Imports, reviews, issue decisions, and exports. |
| `application.mcp_server` | Stateful MCP tools registered on the existing FastMCP server when available. |
| `application.http_api` | Authenticated loopback JSON API for the Tauri shell. |
| `application.sidecar_entry` | PyInstaller-safe desktop sidecar entry point. |

## Run the canonical MCP server

From a source checkout:

```bash
uv run python -m autocite_mcp.application
```

The default transport is stdio. Streamable HTTP remains available through the existing transport setting:

```bash
AUTOCITE_TRANSPORT=streamable-http \
uv run python -m autocite_mcp.application
```

The application module reuses AutoCite's existing FastMCP server when it can resolve it, then adds the session tools. If a host exposes only FastMCP-compatible tools and not resources, `get_document_session` remains the complete fallback.

## Run the desktop loopback API

```bash
AUTOCITE_APPLICATION_MODE=desktop \
AUTOCITE_API_TOKEN="replace-with-a-random-local-token" \
uv run python -m autocite_mcp.application --port 8765
```

The server prints one machine-readable readiness line. A packaged Tauri shell supplies a random token and available port when it launches the sidecar. The token should not be stored in a document, log file, URL, or browser storage.

### Routes

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Process readiness and API version. |
| `GET` | `/sessions` | Compact recent-document list. |
| `POST` | `/sessions` | Create a text or Markdown session. |
| `POST` | `/sessions/import` | Import TXT, Markdown, DOCX, or searchable PDF by local path. |
| `GET` | `/sessions/{id}` | Full current session, review, and decisions. |
| `PATCH` | `/sessions/{id}` | Autosave text, title, or editor state with an expected revision. |
| `DELETE` | `/sessions/{id}` | Delete the local session and related audit state. |
| `POST` | `/sessions/{id}/review` | Run and persist a revision-bound AutoCite review. |
| `POST` | `/sessions/{id}/decision` | Accept, reject, or reset one review issue. |
| `POST` | `/sessions/{id}/apply-safe` | Apply a nonoverlapping batch of safe deterministic fixes. |
| `POST` | `/sessions/{id}/context-preview` | Measure and inspect reversible context selection. |
| `POST` | `/sessions/{id}/export` | Export DOCX, PDF, Markdown, or TXT. |
| `GET` | `/jobs/{id}` | Read durable review-job status. |

Send either header:

```text
Authorization: Bearer <token>
```

or:

```text
X-AutoCite-Token: <token>
```

The server rejects non-loopback binding unless `AUTOCITE_ALLOW_REMOTE=1` is explicitly configured. A remote bind also requires an explicitly supplied token.

## Stateful MCP tools

- `create_document_session`
- `import_document_session`
- `list_document_sessions`
- `get_document_session`
- `update_document_session`
- `review_document_session`
- `get_document_review_job`
- `decide_document_issue`
- `apply_safe_document_issues`
- `preview_document_context_reduction`
- `export_document_session`
- `delete_document_session`

These tools are intended for full applications and long-running editing workflows. AutoCite's existing stateless review tools remain appropriate for a one-off request.

## Context-reduction boundary

The first reducer is deliberately not a generic summary model. It works as follows:

1. Split the canonical text into exact paragraph ranges.
2. Protect explicit focus spans, citations, statutes, regulations, cross-reference terms, headings, quotations, page markers, and footnote markers.
3. Include bounded neighboring paragraphs so propositions and antecedents remain available.
4. Fit nonprotected neighbors to a configurable character budget.
5. Return the selected text, exact source ranges, source hash, savings ratio, and bypass reason.
6. Preserve full-document deterministic review regardless of the reduction result.

This creates the interface needed for a later Headroom-compatible implementation without making lossy compression a hidden prerequisite for citation extraction.

## Storage location

Set `AUTOCITE_SESSION_DB` to choose an explicit SQLite path. Otherwise AutoCite uses the platform application-data directory:

- Windows: `%LOCALAPPDATA%/AutoCite/sessions.sqlite3`
- macOS: `~/Library/Application Support/AutoCite/sessions.sqlite3`
- Linux: `$XDG_DATA_HOME/AutoCite/sessions.sqlite3`, or `~/.local/share/AutoCite/sessions.sqlite3`

Deleting a session cascades to its jobs, decisions, and export audit rows. Exported files themselves are not deleted.

## Import and export limits

DOCX import converts headings, paragraphs, list styles, and tables to conservative Markdown. Searchable PDFs retain page comments. Image-only PDFs fail explicitly and require OCR instead of returning incomplete text.

DOCX export preserves document structure at the text level. It does not yet reproduce every original Word style, field, footnote, or pagination choice. The backend PDF exporter is a dependency-free text-safe fallback. The Tauri editor can use the operating system print pipeline for layout-faithful PDF output.

## Tests

```bash
uv run pytest \
  tests/test_application_store.py \
  tests/test_application_context_reducer.py \
  tests/test_application_service.py
```

The tests cover persistence, optimistic conflicts, job state, decisions, source-range reconstruction, context bypass behavior, safe-application gates, DOCX import, and all four portable export formats.
