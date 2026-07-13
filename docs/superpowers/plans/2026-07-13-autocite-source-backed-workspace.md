# AutoCite Source-Backed Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a backward-compatible v0.3 release that adds evidence-backed case citechecking, legal-document ingestion and DOCX review export, jurisdiction profiles, an interactive MCP App, evaluation fixtures, security guidance, and PyPI release scaffolding.

**Architecture:** Keep the deterministic citation engine unchanged. Add isolated authority-retrieval, evidence-analysis, document, jurisdiction, and workspace modules, then compose them in `review_document` and new MCP tools. Network work is opt-in, source excerpts are bounded, and every inference carries explicit provenance.

**Tech Stack:** Python 3.10+, MCP Python SDK/FastMCP, httpx, eyecite, BeautifulSoup4, python-docx, pypdf, pytest, Ruff, vanilla HTML/CSS/JavaScript.

## Global Constraints

- Existing tools and defaults remain backward compatible.
- No network calls unless `deep_review` or explicit verification is requested.
- Never represent lexical similarity as a legal conclusion.
- Never claim Shepardizing, KeyCiting, good-law status, controlling authority, or proposition support.
- Never persist uploaded documents, retrieved opinions, or generated artifacts server-side.
- Never bundle third-party reference materials into distributions or containers.
- Bound retrieved source excerpts and input file sizes.
- Scanned PDFs must return `ocr_required`, not incomplete silent output.

---

### Task 1: Authority retrieval client

**Files:**
- Create: `src/autocite_mcp/sources.py`
- Modify: `src/autocite_mcp/verifiers.py`
- Test: `tests/test_sources.py`

**Interfaces:**
- Produces `CourtListenerSourceClient.lookup_and_fetch(text: str) -> dict[str, Any]`.
- Produces normalized authority records containing lookup status, cluster metadata, opinion IDs, bounded plain text, and user-openable URLs.

- [ ] Write tests with a fake async HTTP client for citation lookup, cluster retrieval, and opinion retrieval.
- [ ] Verify tests fail because `CourtListenerSourceClient` does not exist.
- [ ] Implement authenticated citation lookup using `Authorization: Token`, then follow cluster `sub_opinions` URLs and select `html_with_citations` before fallback text fields.
- [ ] Strip HTML safely, cap each opinion at 200,000 characters internally, and expose no more than 12,000 characters per authority result.
- [ ] Return structured `missing_token`, `http_error`, `network_error`, `ambiguous`, and `not_found` states.
- [ ] Run `pytest tests/test_sources.py -v` and commit.

### Task 2: Evidence analysis

**Files:**
- Create: `src/autocite_mcp/evidence.py`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Produces `extract_proposition(text, citation_start)`, `extract_nearby_quotes(text, citation_start)`, `match_quote(quote, source_text)`, `rank_passages(proposition, source_text)`, and `analyze_case_evidence(...)`.

- [ ] Write tests for exact quote, normalized quote, partial quote, absent quote, proposition extraction, passage ranking, and page-marker detection.
- [ ] Verify tests fail because the module does not exist.
- [ ] Implement Unicode/whitespace normalization, transparent token-overlap and sequence-similarity scores, sentence-window passage ranking, and explicit `requires_legal_judgment=True` on proposition findings.
- [ ] Treat `*675`, `Page 675`, and `[675]` as explicit page markers; otherwise return `passage_found_page_unverified` or `unverifiable`.
- [ ] Run `pytest tests/test_evidence.py -v` and commit.

### Task 3: Deep review orchestration

**Files:**
- Create: `src/autocite_mcp/deep_review.py`
- Modify: `src/autocite_mcp/tools.py`
- Test: `tests/test_deep_review.py`
- Modify: `tests/test_tools.py`

**Interfaces:**
- Produces `DeepReviewer.review(text, citations, include_source_text=False) -> dict[str, Any]`.
- Extends `review_document` with `deep_review`, `include_source_text`, and `jurisdiction_profile` arguments.

- [ ] Write tests asserting no source client call when `deep_review=False` and evidence records when enabled.
- [ ] Verify the tests fail on missing arguments/module.
- [ ] Implement case-citation alignment by character span and canonical citation, source retrieval, bounded evidence excerpts, and honest later-citation metadata labeled `not_a_citator`.
- [ ] Add `deep_review_results` and `confidence_legend` to the primary workflow without changing existing keys.
- [ ] Run focused and full tests and commit.

### Task 4: Document ingestion and review export

**Files:**
- Create: `src/autocite_mcp/documents.py`
- Test: `tests/test_documents.py`
- Modify: `src/autocite_mcp/tools.py`

**Interfaces:**
- Produces `load_document_bytes(data, filename, mime_type) -> DocumentInput`.
- Produces `build_review_docx(original_text, corrected_text, tracked=True) -> bytes`.
- Produces `review_uploaded_document(file, ...)` and `export_review_docx(original_text, corrected_text, tracked=True)`.

- [ ] Write tests for TXT, Markdown, DOCX, text PDF, empty/scanned PDF, unsupported type, maximum size, and DOCX XML containing `w:ins`/`w:del`.
- [ ] Verify tests fail because document functions do not exist.
- [ ] Implement file decoding with a 15 MB limit; use python-docx and pypdf; reject PDFs below a minimum extracted-text threshold as `ocr_required`.
- [ ] Build a plain-layout DOCX and tracked revision XML using `difflib.SequenceMatcher`; preserve text content even when original formatting cannot be retained.
- [ ] Return base64 plus filename, MIME type, SHA-256, and an explicit formatting-preservation limitation.
- [ ] Run focused and full tests and commit.

### Task 5: Jurisdiction registry

**Files:**
- Create: `src/autocite_mcp/jurisdictions.py`
- Test: `tests/test_jurisdictions.py`
- Modify: `src/autocite_mcp/knowledge.py`

**Interfaces:**
- Produces `get_jurisdiction_profile(identifier)`, `list_jurisdiction_profiles()`, and `resolve_jurisdiction_profile(identifier, mode)`.

- [ ] Write tests for federal, California, every state name/postal code, unknown identifiers, and unverified fallback warnings.
- [ ] Verify tests fail because the registry does not exist.
- [ ] Implement curated federal and California summaries with official reference URLs, plus generated safe profiles for all other states with `verified_overrides=False`.
- [ ] Add resolved jurisdiction guidance to knowledge packs and deep review results.
- [ ] Run tests and commit.

### Task 6: Interactive MCP App

**Files:**
- Create: `src/autocite_mcp/workspace.py`
- Modify: `src/autocite_mcp/server.py`
- Test: `tests/test_workspace.py`
- Modify: `tests/test_server.py`

**Interfaces:**
- Produces `WORKSPACE_HTML` and `workspace_payload(review)`.
- Adds `open_citecheck_workspace` bound through `_meta.ui.resourceUri` to `ui://autocite/citecheck-v1.html`.

- [ ] Write tests for required HTML controls, no external scripts, MCP Apps MIME type, tool metadata, and meaningful non-UI fallback content.
- [ ] Verify tests fail because the workspace is absent.
- [ ] Implement a self-contained widget that renders summary cards, original/corrected text, issue/evidence filters, accept/reject toggles, and copy controls from `ui/notifications/tool-result`.
- [ ] Register the resource and tool while preserving support for text-only MCP clients.
- [ ] Run tests and commit.

### Task 7: CLI and MCP file workflows

**Files:**
- Modify: `src/autocite_mcp/cli.py`
- Modify: `src/autocite_mcp/server.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Adds `review-file`, `export-docx`, `jurisdictions`, and deep-review flags.
- Adds MCP tools `review_uploaded_document`, `export_review_docx`, `get_jurisdiction_profile`, and `open_citecheck_workspace`.

- [ ] Write parser and integration tests for each command and MCP schema.
- [ ] Verify failures for missing commands/tools.
- [ ] Implement commands and metadata, including ChatGPT file-parameter metadata on the uploaded-document tool.
- [ ] Run tests and commit.

### Task 8: Evaluation suite

**Files:**
- Create: `evals/gold.jsonl`
- Create: `src/autocite_mcp/evals.py`
- Create: `tests/test_evals.py`

**Interfaces:**
- Produces `run_gold_evaluation(path) -> dict[str, Any]` with extraction, fix, quote, and evidence-ranking metrics.

- [ ] Add representative correct/incorrect citations and quote/evidence fixtures with no copyrighted long passages.
- [ ] Write tests for deterministic metric calculation.
- [ ] Implement the evaluator and CLI entry `autocite eval`.
- [ ] Run tests and commit.

### Task 9: Packaging, CI, release, and security documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`
- Create: `docs/SECURITY.md`
- Create: `docs/SOURCE_REVIEW.md`
- Modify: `docs/CONNECT.md`
- Modify: `README.md`
- Modify: `Dockerfile`
- Test: `tests/test_package_boundaries.py`

**Interfaces:**
- Adds dependencies `beautifulsoup4`, `python-docx`, and `pypdf`.
- Adds PyPI Trusted Publishing on published GitHub releases.

- [ ] Write package-boundary and documentation-presence tests.
- [ ] Update version to `0.3.0`, dependency metadata, Docker build, CI, and distribution exclusions.
- [ ] Add a release workflow using `pypa/gh-action-pypi-publish@release/v1` with `id-token: write` and a configured `pypi` environment.
- [ ] Document CourtListener limits, retrieved-text prompt-injection handling, no-retention behavior, OAuth/private-proxy requirements, scanned-PDF limitations, and the distinction between evidence ranking and legal judgment.
- [ ] Run `ruff`, all tests, module compilation, wheel/sdist build, wheel inspection, MCP tool/resource smoke tests, and HTTP health checks.
- [ ] Open a PR, confirm the remote diff excludes `reference/`, wait for all Python-version jobs, and merge only after success.
