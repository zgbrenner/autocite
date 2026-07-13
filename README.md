# AutoCite MCP

AutoCite is a conservative legal-citation checker, fixer, generator, converter, and authority verifier exposed as a Model Context Protocol server. It supports two distinct workflows:

- **Bluepages mode** for court filings, briefs, motions, memoranda, and other practitioner documents.
- **Whitepages mode** for law-review articles, seminar papers, academic legal research, and editorial citechecking.

AutoCite is designed to help an AI system make citation work more reliable without allowing it to invent missing source facts. It automatically applies only high-confidence mechanical corrections. Questions that require source review, local rules, proposition checking, or editorial judgment remain clearly marked for human review.

## Core capabilities

- Extract citations from a block of legal writing and return exact character spans.
- Parse federal and state cases, federal and state statutes, federal regulations, constitutional provisions, journal citations, `Id.`, `supra`, short-case and reference citations, and internet URLs.
- Safely normalize common reporter abbreviations, `U.S.C.` and `C.F.R.`, section-symbol spacing, and `Id.` capitalization or punctuation.
- Generate citations from structured facts for cases, statutes, regulations, constitutions, journal articles, books, websites, court documents, AI-generated content, and archival sources.
- Convert recognized cases, statutes, regulations, and constitutional citations into a selected output style.
- Verify and normalize U.S. case citations through CourtListener when a token is configured.
- Provide separate MCP prompts for court-filing and law-review citechecks.
- Expose rule-family explanations without reproducing proprietary citation manuals.

## Why the architecture is hybrid

A pure regular-expression checker is too brittle for legal citation work. A pure LLM wrapper is too likely to guess missing authors, dates, reporters, pincites, or parentheticals. AutoCite therefore separates three responsibilities:

1. **Deterministic engine:** Free Law Project’s `eyecite` parser handles production-grade legal-citation extraction and short-form resolution; AutoCite adds malformed-citation fallbacks, issue detection, structured generation, and safe mechanical fixes.
2. **External verification:** optional CourtListener lookup for U.S. case citations.
3. **LLM judgment:** MCP prompts direct the host model to handle context-sensitive review while preserving unresolved questions.

A citation that is correctly formatted is not necessarily real, current, controlling, or supportive of the proposition for which it is cited.

## MCP tools

| Tool | Purpose |
|---|---|
| `check_citations` | Audit a document in Bluepages or Whitepages mode; optionally apply safe fixes. |
| `fix_citations` | Apply only high-confidence mechanical citation fixes. |
| `check_single_citation` | Return a focused report for exactly one recognized citation. |
| `convert_citation` | Convert a recognized citation using only facts already present. |
| `generate_citation` | Build a citation from structured source metadata. |
| `verify_case_citations` | Verify and normalize U.S. case citations through CourtListener. |
| `explain_issue` | Explain an AutoCite issue code and its relevant rule family. |
| `list_capabilities` | Return supported sources, fixes, verification coverage, and guardrails. |

## MCP resources and prompts

Resources:

- `autocite://capabilities`
- `autocite://rules/bluepages`
- `autocite://rules/whitepages`

Prompts:

- `court_filing_citecheck`
- `law_review_citecheck`
- `citation_repair`

## Installation

AutoCite requires Python 3.10 or later. The project pins the stable MCP Python SDK line below v2 because the v2 SDK remains pre-release as of this implementation.

Using `uv`:

```bash
uv sync --extra dev
uv run autocite-mcp
```

Using `pip`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
autocite-mcp
```

The default transport is `stdio`. To run Streamable HTTP instead:

```bash
AUTOCITE_TRANSPORT=streamable-http uv run autocite-mcp
```

The default MCP endpoint for the stable Python SDK is typically:

```text
http://localhost:8000/mcp
```

## Configure an MCP client

A Windows Claude Desktop example is included at [`examples/claude_desktop_config.json`](examples/claude_desktop_config.json). Update the repository path and token:

```json
{
  "mcpServers": {
    "autocite": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\autocite",
        "run",
        "autocite-mcp"
      ],
      "env": {
        "COURTLISTENER_TOKEN": "replace-with-your-token"
      }
    }
  }
}
```

Case verification is optional. Without `COURTLISTENER_TOKEN`, all local checking, fixing, generation, conversion, resources, and prompts continue to work.

## CourtListener verification scope

CourtListener's citation-lookup API can parse, normalize, and look up U.S. case citations. AutoCite uses it only when explicitly called and when `COURTLISTENER_TOKEN` is set.

CourtListener verification does **not** establish that:

- the case remains good law;
- the case supports the user's proposition;
- a quotation or pincite is accurate;
- the cited authority is controlling;
- statutes, journal articles, `Id.`, or `supra` citations are valid.

AutoCite also enforces CourtListener's documented 64,000-character request ceiling.

## Command-line use

The same deterministic engine works without an MCP client.

Audit text:

```bash
uv run autocite check "See 576 US 644 and 42 USC §1983."
```

Apply safe fixes:

```bash
uv run autocite fix --mode bluepages "See 576 US 644 and 42 USC §1983."
```

Audit a file:

```bash
uv run autocite check --mode whitepages --file article.txt
```

Generate a citation:

```bash
uv run autocite generate case \
  --mode bluepages \
  --output-style markdown \
  --fields '{"case_name":"Obergefell v. Hodges","volume":"576","reporter":"U.S.","first_page":"644","pincite":"675","year":"2015"}'
```

## Structured generation guardrail

`generate_citation` refuses to fill in missing required fields. For example, a case without a first page produces an error rather than a fabricated page number. Internet and AI-content citations can also require archive or on-file metadata depending on the supplied source type.

## Development

Run lint and the test suite:

```bash
uv run ruff check src tests
uv run pytest
```

Compile all modules:

```bash
python -m py_compile src/autocite_mcp/*.py
```

Build the package:

```bash
uv build
```

CI tests Python 3.10, 3.12, and 3.13 and builds the wheel and source distribution.

## Repository references and licensing

The repository contains public and third-party citation references under [`reference/`](reference/). The AutoCite software is MIT licensed. Some reference materials have separate restrictions described in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and are not relicensed under MIT.

The Python package is configured to include only `src/autocite_mcp`; the third-party reference corpus is not bundled into the wheel. MCP tools return original AutoCite explanations and rule-family identifiers rather than reproducing reference-book text.

AutoCite uses the BSD-licensed [`eyecite`](https://github.com/freelawproject/eyecite) parser maintained by Free Law Project. AutoCite is not affiliated with or endorsed by Free Law Project or by the editors or publishers of *The Bluebook*. It is not a substitute for the official manual, controlling court rules, local rules, journal style guides, source review, or attorney/editor judgment.
