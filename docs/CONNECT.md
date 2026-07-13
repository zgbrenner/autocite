# Connect AutoCite to Claude or ChatGPT

AutoCite supports two connection models:

1. **Local Claude Desktop** — best for confidential documents because the citation engine stays on the computer.
2. **Remote HTTPS MCP** — works with ChatGPT and Claude web connectors through an HTTPS `/mcp` URL.

The primary tool is `review_document`. The model should call it before trying to repair citations from memory. It automatically selects Bluepages or Whitepages mode, applies deterministic fixes, and returns the relevant citation playbook for unresolved issues.

## Option A: Claude Desktop, local and private

### 1. Install AutoCite

With `uv`:

```bash
uv tool install "git+https://github.com/zgbrenner/autocite.git"
```

From a cloned checkout:

```bash
uv sync
```

### 2. Install it into Claude Desktop

For a tool installation:

```bash
autocite setup-claude
```

From a cloned checkout:

```bash
uv run autocite setup-claude
```

The installer:

- finds the normal Claude Desktop configuration location;
- preserves all existing MCP servers;
- creates a `.bak` backup when a configuration already exists;
- adds AutoCite using the exact Python executable that ran the installer.

Completely quit and reopen Claude Desktop. AutoCite will appear in the available tools/connectors.

Optional CourtListener verification:

```bash
autocite setup-claude --courtlistener-token "YOUR_TOKEN"
```

CourtListener is contacted only when the model explicitly calls `verify_case_citations`.

## Option B: ChatGPT through a private OpenAI MCP tunnel

This is the recommended ChatGPT route for legal documents that should not be exposed through a public server.

### 1. Start AutoCite locally over Streamable HTTP

```bash
AUTOCITE_TRANSPORT=streamable-http autocite-mcp
```

The local endpoint is:

```text
http://127.0.0.1:8000/mcp
```

### 2. Create an OpenAI Secure MCP Tunnel

Create the tunnel in OpenAI Platform tunnel settings, run `tunnel-client` on the same machine or network as AutoCite, and point its local target to `http://127.0.0.1:8000/mcp`.

OpenAI's current tunnel guide:

```text
https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
```

### 3. Add AutoCite in ChatGPT

1. Open ChatGPT **Settings → Security and login** and enable **Developer mode**.
2. Open **Settings → Plugins** or `https://chatgpt.com/plugins`.
3. Select **+** to create a developer-mode app.
4. Name it **AutoCite**.
5. Use this description:

   > Reviews and fixes legal citations in court filings and legal research. Always call `review_document` before answering citation-format questions.

6. Select the tunnel you created, or enter the hosted HTTPS `/mcp` URL.
7. Create the app and verify that `review_document` appears in the tool list.

In a chat, enable AutoCite through **+ → More**, then ask:

> Review and fix every citation in this document. Preserve all non-citation prose and separately list anything that still requires source review.

## Option C: Claude web through a remote MCP connector

AutoCite must be available at an internet-reachable HTTPS URL ending in `/mcp`.

For Claude Pro or Max:

1. Open **Customize → Connectors**.
2. Select **+ → Add custom connector**.
3. Enter the AutoCite HTTPS `/mcp` URL.
4. Add the connector, then enable it in a conversation through **+ → Connectors**.

For Team or Enterprise, an Owner first adds the URL under **Organization settings → Connectors**; members then connect it individually.

## Host AutoCite as an HTTPS MCP server

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

Place the container behind an HTTPS reverse proxy, or deploy it to a container platform.

### Render Blueprint

The repository includes `render.yaml` and a `Dockerfile`.

1. Create a new Render Blueprint from this repository.
2. Deploy the `autocite-mcp` service.
3. Use `https://YOUR-SERVICE.onrender.com/mcp` in Claude or ChatGPT.
4. Optionally add `COURTLISTENER_TOKEN` as a secret environment variable.

**Privacy warning:** a no-auth public deployment accepts citation-review requests from anyone who knows the URL. It is suitable for demos or nonconfidential text, not privileged or sensitive legal documents. For sensitive documents, use local Claude Desktop or OpenAI Secure MCP Tunnel. A production multi-user deployment should add OAuth and appropriate access controls before use.

## What the model receives

`review_document` returns:

- automatic Bluepages/Whitepages mode selection with confidence and reasons;
- corrected text containing only deterministic citation edits;
- exact citation spans and source classifications;
- applied edits and unresolved issues;
- source-specific templates, required facts, checks, and rule families;
- cross-cutting guidance for signals, pincites, parentheticals, source ordering, quotations, and short forms;
- an explicit response contract that prohibits fabricated citation facts and overclaims.

The model is instructed to use AutoCite rather than rely on general citation memory.

## Recommended prompts

### Whole document

> Use AutoCite to review and fix every citation in this document. Preserve all non-citation prose. Return the corrected document first, then a concise list of anything requiring source review.

### Court filing

> Citecheck this filing under the Bluepages and the filing court's local rules. Apply safe fixes, verify case citations when available, and flag every unresolved pincite, short-form, or local-rule issue.

### Law review or seminar paper

> Citecheck this document under the Whitepages. Review signals, parentheticals, short forms, source order, pincites, typography, and internet archives. Never invent missing bibliographic facts.

## Scope

AutoCite improves citation formatting and gives the host model a structured legal-citation playbook. It does not by itself determine that an authority is good law, controlling, accurately quoted, or supportive of the proposition. Those tasks require substantive source review and, where applicable, citator research.
