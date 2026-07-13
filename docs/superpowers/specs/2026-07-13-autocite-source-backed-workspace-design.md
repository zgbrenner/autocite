# AutoCite Source-Backed Workspace Design

## Goal

Extend AutoCite from a citation-formatting MCP into an evidence-backed citechecking system that retrieves primary authority, validates quotations and citation metadata, surfaces proposition-support evidence, accepts common legal-document formats, exports review artifacts, offers an interactive MCP App, supports jurisdiction profiles, and includes reproducible evaluations and public-release scaffolding.

## Release shape

This work ships as one backward-compatible v0.3 release with independently testable modules. Existing tools remain available. `review_document` stays the normal entry point and gains optional deep review; no network call occurs unless the user requests source verification.

## Architecture

1. **Deterministic citation layer:** Existing extraction, linting, fixing, generation, and mode detection remain isolated.
2. **Authority retrieval layer:** A CourtListener client performs citation lookup, retrieves cluster metadata and opinion text, observes authentication and rate limits, and caches only in memory for the duration of a request.
3. **Evidence layer:** Pure functions compare quotations, locate likely supporting passages, calculate transparent lexical scores, and classify what is verified, inferred, or unresolved. It never represents lexical similarity as a legal conclusion.
4. **Document layer:** Plain text, Markdown, DOCX, and text-based PDF inputs are normalized to text. Review exports include corrected DOCX and a tracked-change DOCX generated without retaining files server-side.
5. **Jurisdiction layer:** A registry supplies federal, California, and generic state profiles. Every U.S. state is addressable; only profiles with verified overrides claim jurisdiction-specific guidance. Others explicitly fall back to general guidance and require local-rule review.
6. **MCP App layer:** A sandboxed `ui://` resource renders a citation workspace with original/corrected text, filters, evidence excerpts, confidence labels, and accept/reject controls. Text-only clients receive meaningful structured and text results.
7. **Evaluation and release layer:** Gold fixtures test extraction, corrections, quote matching, evidence ranking, document conversion, and jurisdiction fallback. Release workflows build distributions and support PyPI Trusted Publishing after the owner configures the publisher.

## Primary workflow

`review_document` accepts the existing inputs plus:

- `deep_review`: retrieve source material and prepare evidence-backed findings.
- `include_source_text`: include bounded excerpts, never entire opinions.
- `jurisdiction_profile`: explicit profile override.

For each case citation, deep review returns:

- authority lookup status and canonical metadata;
- source URL and opinion identifiers;
- quotation status: exact, normalized, partial, absent, or not supplied;
- pincite status: confirmed by explicit page marker, passage found without reliable page marker, absent, or unverifiable;
- proposition evidence: the proposition preceding the citation, top source passages, lexical scores, and a mandatory `requires_legal_judgment` flag;
- later-citation metadata when available, explicitly labeled as not Shepardizing or KeyCiting;
- confidence provenance: deterministic, source-verified, model-inference-required, or unresolved.

## Document workflows

- `review_uploaded_document` accepts an authorized MCP file reference or base64 payload and supports `.txt`, `.md`, `.docx`, and text-based `.pdf`.
- `export_review_docx` returns a base64 DOCX artifact containing the corrected text and tracked revisions.
- Scanned PDFs return a clear unsupported/OCR-required result rather than silently producing incomplete text.
- Maximum input and output sizes are enforced.

## Interactive workspace

`open_citecheck_workspace` returns a concise summary and is bound to `ui://autocite/citecheck-v1.html` using the MCP Apps MIME type. The widget renders entirely from tool results, has no third-party scripts, and does not make network calls. Users can filter findings, inspect evidence, toggle proposed edits, and copy corrected text. The server still returns useful content for clients that do not render apps.

## Jurisdiction profiles

Profiles contain:

- profile ID and display name;
- preferred mode;
- controlling-style priority statement;
- source-order and local-rule review notes;
- official reference URLs;
- verified-overrides flag.

Federal and California receive curated profiles. All states receive a safe generic profile with their identity and an explicit warning that local rules have not been encoded.

## Security and privacy

- No server-side persistence of document text, source text, or generated files.
- Source excerpts are bounded.
- Network calls require explicit deep review and a configured CourtListener token.
- HTTP responses use `Cache-Control: no-store` where controlled by AutoCite.
- Hosted deployments must use OAuth, an authenticated reverse proxy, or a private tunnel. The bundled deployment remains suitable for local/private use and nonconfidential demos, not an unauthenticated multi-user legal service.
- Tool descriptions and outputs resist prompt injection from retrieved authorities by treating source text as quoted evidence, never instructions.

## Reliability contract

AutoCite may state that a citation exists, metadata matches, or a quotation appears in retrieved text when verified. It may rank candidate passages using disclosed lexical methods. It must not independently conclude that a source supports a legal proposition, remains good law, is controlling, or has positive/negative treatment. Those questions remain explicit legal-judgment items unless a future licensed citator integration provides the relevant evidence.

## Testing

Tests cover mocked CourtListener lookup, cluster and opinion retrieval; HTML-to-text normalization and bounded excerpts; exact and normalized quotation matching; transparent proposition-evidence ranking; pincite-marker detection; DOCX/PDF ingestion and tracked-change export; all-state profile availability and fallback; MCP tool/resource/prompt surface and workspace HTML; package contents; and no-network behavior unless deep review is requested.

## Distribution

The project adds a release workflow for GitHub releases and PyPI Trusted Publishing. Publishing remains gated on the repository owner creating the PyPI project or pending publisher. Documentation includes local Claude, remote Claude, ChatGPT, Docker, private-tunnel, and PyPI installation paths.
