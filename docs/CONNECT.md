# Connect AutoCite to Claude or ChatGPT

AutoCite supports two connection models:

1. **Local Claude Desktop** — best for confidential documents because ordinary citation review stays on the computer.
2. **Remote HTTPS MCP** — works with ChatGPT and Claude web through an authenticated HTTPS `/mcp` endpoint.

The primary tool is `review_document`. For uploaded TXT, Markdown, DOCX, or text-based PDF, use `review_uploaded_document`. Both automatically select Bluepages or Whitepages, apply deterministic fixes, and return the relevant citation playbook.

## Network behavior

Ordinary formatting review is local to the AutoCite process. AutoCite contacts CourtListener only when one of these is explicitly requested and `COURTLISTENER_TOKEN` is configured:

- `deep_review=true`;
- `verify_cases=true`;
- `verify_case_citations`.

Deep review may send citation-bearing document text to CourtListener's citation lookup endpoint to align citations with authorities. Retrieved opinion text is bounded, stripped of active HTML, and treated as untrusted quoted evidence—not instructions.

## Option A: Claude Desktop, local and private

### Install AutoCite

```bash
uv tool install "git+https://github.com/zgbrenner/autocite.git"
autocite setup-claude
```

From a cloned checkout:

```bash
uv sync
uv run autocite setup-claude
```

The installer finds the normal Claude Desktop configuration, preserves existing MCP servers, creates a `.bak` backup, and uses the exact Python executable that ran it.

Completely quit and reopen Claude Desktop. Then ask:

> Use AutoCite to review and fix every citation in this document. Preserve all non-citation prose and separately list anything requiring source review.

Optional source retrieval:

```bash
autocite setup-claude --courtlistener-token "YOUR_TOKEN"
```

Then ask:

> Run AutoCite's deep review on the case citations. Compare quotations and pincites with the retrieved opinions, show candidate passages, and do not claim proposition support or good-law status.

## Option B: ChatGPT through a private MCP tunnel

This is the recommended ChatGPT route for privileged or confidential documents.

### Start AutoCite locally

```bash
AUTOCITE_TRANSPORT=streamable-http autocite-mcp
```

Local endpoint:

```text
http://127.0.0.1:8000/mcp
```

Create an OpenAI Secure MCP Tunnel and target the local endpoint. Then in ChatGPT:

1. Enable Developer mode in settings.
2. Open Plugins/developer apps.
3. Create an app named **AutoCite**.
4. Select the tunnel or enter an authenticated HTTPS `/mcp` URL.
5. Confirm `review_document`, `review_uploaded_document`, and `open_citecheck_workspace` appear.

Recommended description:

> Reviews, fixes, and evidence-checks legal citations. Always call `review_document` or `review_uploaded_document` before answering citation questions from memory. Never treat candidate passages as a legal conclusion.

When a host supports MCP Apps, `open_citecheck_workspace` renders an interactive review surface. Text-only hosts still receive corrected text and structured findings.

## Option C: Claude web through a remote connector

AutoCite must be available at an authenticated internet-reachable HTTPS URL ending in `/mcp`.

For Claude Pro or Max:

1. Open **Customize → Connectors**.
2. Select **+ → Add custom connector**.
3. Enter the AutoCite HTTPS `/mcp` URL.
4. Add and enable it in the conversation.

For Team or Enterprise, an Owner first adds the URL under organization connector settings.

## Host AutoCite

### Docker

```bash
docker build -t autocite-mcp .
docker run --rm -p 8000:8000 autocite-mcp
```

Health check:

```text
http://localhost:8000/health
```

MCP endpoint:

```text
http://localhost:8000/mcp
```

Place the container behind TLS and an authenticated reverse proxy or private tunnel.

### Render Blueprint

The repository includes `render.yaml` and a `Dockerfile`.

1. Create a Render Blueprint from the repository.
2. Deploy the `autocite-mcp` service.
3. Put authentication in front of the service before using confidential documents.
4. Use the authenticated HTTPS URL plus `/mcp` in Claude or ChatGPT.
5. Add `COURTLISTENER_TOKEN` only through secret environment storage.

**Privacy warning:** an unauthenticated public endpoint accepts document-review requests from anyone who knows the URL. It is suitable only for nonconfidential demonstrations. Production hosting must add OAuth or an authenticated proxy, tenant isolation, request limits, secret management, access-log redaction, and no-store caching.

## File workflows

Connected hosts can pass authorized file references to `review_uploaded_document`. The tool expects a file object containing either:

- `data_base64`; or
- an authorized `download_url` supplied by the host.

Optional fields are `file_name` and `mime_type`. The MCP declaration includes ChatGPT's file-parameter metadata for `file`.

Supported formats:

- `.txt`;
- `.md` / Markdown;
- `.docx`;
- searchable/text-based `.pdf`.

Scanned PDFs return `ocr_required`. AutoCite does not retain the file server-side.

## Export workflow

After a review, call `export_review_docx` with `original_text` and `corrected_text`. The tool returns a base64 DOCX with optional tracked insertions and deletions. The export is text-oriented and does not preserve every original style, field, footnote, table, or page layout.

## Recommended prompts

### Whole document

> Use AutoCite to review and fix every citation. Preserve non-citation prose. Return the corrected document first, a concise change log second, and a source-review list third.

### Deep case review

> Use AutoCite deep review. Retrieve the cited cases, compare quotations and pincites, and show the strongest candidate passages. Independently assess whether those passages support the proposition; do not treat lexical scores as a legal conclusion and do not claim good-law status.

### California filing

> Citecheck this filing under AutoCite's California jurisdiction profile and Bluepages mode. Apply deterministic fixes and separately flag every California Style Manual, local-rule, record-citation, and authority-treatment issue requiring verification.

### Law review

> Citecheck this under the Whitepages. Review signals, parentheticals, short forms, source order, pincites, typography, and internet archives. Never invent bibliographic facts.

## Scope

AutoCite can verify that retrieved text contains specific metadata, language, or page markers. It can rank candidate passages for review. It cannot determine good-law status, controlling authority, legal proposition support, or treatment. See [`SOURCE_REVIEW.md`](SOURCE_REVIEW.md) and [`SECURITY.md`](SECURITY.md).
