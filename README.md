# AutoCite MCP

AutoCite turns Claude or ChatGPT into a safer legal-citation specialist for both sides of legal writing:

- **Bluepages** — briefs, motions, pleadings, court filings, and practitioner memoranda.
- **Whitepages** — law reviews, student notes, seminar papers, and academic legal research.

The normal user experience is simple: connect AutoCite, give the model a document, and ask it to fix the citations. The model calls one primary tool—`review_document`—which detects the correct mode, applies safe mechanical fixes, and gives the model the source-specific rule knowledge it needs for everything that remains.

## Use it in three minutes

### Claude Desktop: local and private

```bash
uv tool install "git+https://github.com/zgbrenner/autocite.git"
autocite setup-claude
```

Completely quit and reopen Claude Desktop. Then ask:

> Use AutoCite to review and fix every citation in this document. Preserve all non-citation prose and list anything that still requires source review.

From a cloned checkout, use:

```bash
uv sync
uv run autocite setup-claude
```

### ChatGPT or Claude web: remote MCP

Run AutoCite as a Streamable HTTP server:

```bash
AUTOCITE_TRANSPORT=streamable-http autocite-mcp
```

The MCP endpoint is `/mcp`. ChatGPT and Claude web require an HTTPS-reachable endpoint. For confidential work in ChatGPT, use OpenAI Secure MCP Tunnel instead of exposing the server publicly. Complete connection steps are in [`docs/CONNECT.md`](docs/CONNECT.md).

## What makes it model-ready

AutoCite does not merely expose a regex checker. Its MCP server tells the host model to call `review_document` first rather than answer citation questions from memory. That tool returns:

- automatic Bluepages/Whitepages selection, confidence, and rationale;
- corrected text containing only deterministic citation edits;
- exact citation spans and source classifications;
- applied edits and unresolved issues;
- mode-specific and source-specific citation guidance;
- relevant rule families such as B10/Rule 10 for cases and B4/Rule 4 for short forms;
- guidance for signals, pincites, parentheticals, source ordering, quotations, and short forms;
- an explicit response contract forbidding invented facts and overclaims.

This hybrid approach separates work that software can perform safely from work that requires the LLM, the source, a local rule, or human legal judgment.

## Primary MCP tool

### `review_document`

Use this for almost every ordinary request. Inputs include:

- the document text;
- an optional document type;
- `mode="auto"`, `bluepages`, or `whitepages`;
- an optional jurisdiction;
- whether to apply safe fixes;
- whether to call CourtListener for case-citation verification.

It analyzes, fixes, rechecks, and packages the relevant citation knowledge in one call.

## Additional tools

| Tool | Purpose |
|---|---|
| `get_citation_guidance` | Return the model's compact rule playbook for a mode and source type. |
| `check_citations` | Audit a document and return structured issues. |
| `fix_citations` | Apply high-confidence mechanical fixes only. |
| `check_single_citation` | Review exactly one recognized citation. |
| `convert_citation` | Convert a recognized citation using only facts already present. |
| `generate_citation` | Build a citation from supplied source facts; fail when required facts are missing. |
| `verify_case_citations` | Optionally normalize and look up U.S. case citations through CourtListener. |
| `explain_issue` | Explain an issue code and its mode-specific rule family. |
| `list_capabilities` | Return coverage, limitations, and guardrails. |

## Supported citation knowledge

The server provides original guidance for:

- cases;
- statutes and session-law style sources;
- regulations and administrative codes;
- constitutions;
- journal articles and periodicals;
- books and nonperiodic materials;
- court and docket documents;
- internet sources;
- AI-generated content;
- archival materials;
- `Id.`, shortened case forms, `supra`, and `hereinafter`;
- foreign, international, and Tribal materials that require jurisdiction-specific review.

It also distinguishes practitioner typography and priorities from academic law-review conventions.

## Safe automatic fixes

AutoCite currently applies only high-confidence mechanical edits, including:

- common reporter abbreviation normalization;
- `U.S.C.` and `C.F.R.` abbreviation normalization;
- section-symbol spacing;
- `Id.` capitalization and punctuation.

It does not invent a reporter, court, year, author, title, page, pincite, date, URL, parenthetical, or archive link.

## Install and run

AutoCite requires Python 3.10 or later.

```bash
uv sync --extra dev
uv run autocite-mcp
```

Default local transport: `stdio`.

Hosted transport:

```bash
AUTOCITE_TRANSPORT=streamable-http \
AUTOCITE_HOST=0.0.0.0 \
AUTOCITE_PORT=8000 \
uv run autocite-mcp
```

Endpoints:

```text
GET  /health
MCP  /mcp
```

## Docker and hosted deployment

```bash
docker build -t autocite-mcp .
docker run --rm -p 8000:8000 autocite-mcp
```

The included `render.yaml` can deploy the same container on Render. Use the resulting HTTPS URL plus `/mcp` when adding the connector to ChatGPT or Claude.

A public deployment without authentication is appropriate only for demos or nonconfidential text. Use local Claude Desktop or OpenAI Secure MCP Tunnel for sensitive legal documents. Production multi-user hosting should add OAuth and access controls.

## Command line

The same workflow works without an MCP client.

Complete review:

```bash
uv run autocite review --file brief.txt
```

Explicit academic mode:

```bash
uv run autocite review --mode whitepages --file article.txt
```

Citation guidance:

```bash
uv run autocite guidance --mode bluepages --source-type case
```

Safe fix only:

```bash
uv run autocite fix "See 42 USC §1983. Id"
```

Structured generation:

```bash
uv run autocite generate case \
  --mode bluepages \
  --output-style markdown \
  --fields '{"case_name":"Obergefell v. Hodges","volume":"576","reporter":"U.S.","first_page":"644","pincite":"675","year":"2015"}'
```

## Optional CourtListener verification

Set `COURTLISTENER_TOKEN` to enable `verify_case_citations`. AutoCite contacts CourtListener only when verification is explicitly requested.

This lookup can help parse, normalize, and locate U.S. case citations. It is not Shepard's or KeyCite and does not establish that a case is good law, controlling, accurately quoted, or supportive of a proposition.

## Accuracy boundaries

“Mechanically clean” means no remaining citation-format issues detected within AutoCite's supported rules. It does **not** mean:

- every authority exists;
- every authority is current or good law;
- the authority supports the proposition;
- the quotation and pincite match the source;
- the authority is controlling;
- every local court rule or journal house rule has been applied.

AutoCite explicitly labels those questions for source review instead of pretending to resolve them.

## Development

```bash
PYTHONPATH=src pytest
ruff check src tests
python -m py_compile src/autocite_mcp/*.py
uv build
```

CI runs on Python 3.10, 3.12, and 3.13.

## Licensing and references

The AutoCite software is MIT licensed. The repository's `reference/` directory contains public and separately licensed citation materials governed by [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Those materials are not bundled in the Python wheel or returned through MCP resources.

AutoCite returns original summaries and rule-family identifiers. It is not affiliated with or endorsed by the publishers or editors of *The Bluebook*, and it does not replace the official manual, controlling local rules, journal style guides, source verification, or professional judgment.
