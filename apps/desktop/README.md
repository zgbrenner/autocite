# AutoCite Desktop

AutoCite Desktop is a Tauri 2 application with a React and TipTap document editor. It is a word processor first: users can draft and revise a full document, navigate headings, search text, review citation findings in context, accept deterministic safe fixes, inspect evidence, compare against the imported original, and export DOCX, PDF, Markdown, or plain text.

The interface takes interaction-design inspiration from Tolaria's calm, efficient workspace, but its implementation is original and the information architecture is deliberately closer to Microsoft Word than to a notes application.

## Architecture

```text
Tauri 2 native shell
  ├── React + TypeScript interface
  ├── TipTap document editor
  ├── native open/save dialogs
  └── managed AutoCite sidecar
        ├── authenticated loopback API
        ├── canonical application service
        ├── deterministic citation engine
        ├── optional local SLM
        └── SQLite document sessions
```

The backend token is generated on every launch and passed to the sidecar through an environment variable. It is never included in a URL or document. The server binds to `127.0.0.1`; the webview CSP permits connections only to the loopback API and Tauri IPC.

## Editor capabilities

- Word-style ribbon with File, Home, Insert, Layout, References, Review, and View tabs.
- Paged legal-document canvas with ruler, margins, zoom, print layout, page sizes, and focus mode.
- Rich formatting, headings, lists, links, quotations, code, checklists, alignment, and tables.
- Local recent-document library, heading outline, and full-document search.
- Debounced autosave with optimistic revision conflicts rather than last-write-wins overwrites.
- Bluepages and Whitepages controls, jurisdiction selection, optional local-model review, and explicit deep source review.
- Separate citation findings, exact source spans, provenance, context-routing metrics, and accept or reject decisions.
- Side-by-side original and current-revision comparison.
- Keyboard shortcuts and searchable command palette.
- Native DOCX, PDF, Markdown, and text exports.

## Local development

Prerequisites:

- Node.js 22
- Rust stable
- Python 3.10 or later
- `uv`

Install project dependencies from the repository root:

```bash
uv sync --extra desktop-build
cd apps/desktop
npm install
```

Build the target-triple sidecar:

```bash
cd ../..
uv run python scripts/build_tauri_sidecar.py
```

Run the desktop application:

```bash
cd apps/desktop
npm run tauri:dev
```

The browser-only interface can be developed against a manually started application API:

```bash
AUTOCITE_APPLICATION_MODE=desktop \
AUTOCITE_API_TOKEN=development-only-token \
uv run python -m autocite_mcp.application --port 8765
```

Then:

```bash
cd apps/desktop
VITE_AUTOCITE_API_URL=http://127.0.0.1:8765 \
VITE_AUTOCITE_API_TOKEN=development-only-token \
npm run dev
```

## Validation

```bash
cd apps/desktop
npm run typecheck
npm run lint
npm test
npm run build
cd src-tauri
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test
```

The repository CI also builds the Python sidecar, performs an authenticated health smoke test, and compiles desktop bundles on Windows, macOS, and Linux.

## Privacy and network behavior

Ordinary imports, editing, deterministic citation checks, session persistence, and exports are local. The sidecar sets Transformers and Hugging Face offline mode by default. Source-backed case review remains an explicit option and may contact CourtListener when a user has configured the required credentials.

The interface contains no analytics, advertising, remote fonts, telemetry SDKs, or document-content logging.
