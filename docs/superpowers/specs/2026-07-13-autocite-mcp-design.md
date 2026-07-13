# AutoCite MCP Design

## Objective

Turn the existing citation-reference repository into a usable MCP server for both practitioner documents governed by Bluepages conventions and academic legal research governed by Whitepages conventions.

## Design principles

1. Never invent bibliographic facts.
2. Separate mechanical formatting from substantive legal validation.
3. Apply automatic edits only when the replacement is deterministic and high confidence.
4. Keep local checking available without network access.
5. Make external authority verification optional and explicit.
6. Do not expose or reproduce third-party reference-book text through MCP responses.

## Architecture

### Deterministic citation engine

`src/autocite_mcp/extractors.py` uses Free Law Project’s `eyecite` parser to recognize full, short, state, federal, and journal citations and group resolvable short forms with their antecedents. `src/autocite_mcp/engine.py` supplements that parser with malformed-citation fallbacks, records exact spans, emits issue codes, and applies non-overlapping high-confidence replacements in reverse document order. The output remains structured so an MCP host can explain, display, or apply edits.

### Structured citation formatters

`src/autocite_mcp/formatters.py` generates citations only from caller-supplied fields. Each source type has an explicit required-field contract. Formatting fails closed when required metadata is absent.

### Optional authority verification

`src/autocite_mcp/verifiers.py` integrates CourtListener's citation-lookup endpoint for U.S. case citations. The token is read from `COURTLISTENER_TOKEN`; the verifier returns an unavailable result rather than silently issuing unauthenticated production requests. Requests are capped at 64,000 characters.

### MCP interface

`src/autocite_mcp/server.py` exposes eight tools, two resources, and three prompts through the stable MCP Python SDK v1 line. `stdio` is the default transport, with SSE and Streamable HTTP selectable through `AUTOCITE_TRANSPORT`.

### Standalone CLI

`src/autocite_mcp/cli.py` exposes the same engine for users who do not need MCP or who want reproducible local checks in scripts and CI.

## Supported initial citation families

Extraction and linting support federal and state cases, federal and state statutes, federal regulations, U.S. constitutional provisions, journal citations, `Id.`, `supra`, short-case and reference citations, and URLs. Structured generation additionally supports books, websites, court documents, AI-generated content, and archival sources.

## Bluepages and Whitepages behavior

The caller must choose the mode. Bluepages mode is intended for briefs, motions, court filings, and practitioner memoranda. Whitepages mode is intended for academic legal writing and law-review citechecking. Issue responses include the corresponding rule family for the selected mode. Output-style transformations are deliberately limited to formatting supported by plain text, Markdown, or HTML.

## Error handling

Invalid modes, unknown issue codes, unsupported source types, empty input, ambiguous multi-citation input, and missing required fields raise explicit errors. Network failures and CourtListener status failures return structured unavailable responses. Context-sensitive questions remain issues without automatic suggestions.

## Security and privacy

The local engine performs no network requests. CourtListener receives text only when the caller invokes the verification tool. The server does not read arbitrary local paths, execute commands, or expose the repository's reference corpus as MCP resources.

## Testing

Unit tests cover eyecite-backed federal and state extraction, exact spans, short-form antecedents, malformed-citation fallbacks, safe edits, Whitepages URL review, citation generation, conversion, MCP registration, capability disclosure, and CourtListener result normalization. CI runs the suite on Python 3.10, 3.12, and 3.13 and builds the package.

## Explicit non-goals for v0.1

- Shepardizing or KeyCiting authorities.
- Determining whether a source supports a proposition.
- Validating quotations against source documents.
- Applying jurisdiction-specific local court rules.
- Editing binary PDF or DOCX files directly.
- Claiming complete implementation of every Bluebook rule or table.
