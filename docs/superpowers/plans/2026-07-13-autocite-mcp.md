# AutoCite MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable MCP server that checks, safely fixes, generates, converts, and optionally verifies legal citations in Bluepages and Whitepages workflows.

**Architecture:** Use a pure-Python deterministic core for extraction and formatting, an optional CourtListener client for case verification, and a thin FastMCP server for tools, resources, and prompts. Keep the reference corpus outside the packaged wheel and never infer missing source facts.

**Tech Stack:** Python 3.10+, MCP Python SDK v1 (`mcp>=1.28,<2`), `eyecite>=2.7.8,<3`, `httpx`, `pytest`, `pytest-asyncio`, Hatchling, GitHub Actions.

## Global Constraints

- Default MCP transport is `stdio`.
- Supported modes are exactly `bluepages` and `whitepages`.
- Automatic edits require high confidence and must not invent metadata.
- CourtListener verification requires `COURTLISTENER_TOKEN` and is limited to 64,000 input characters.
- Third-party reference files remain outside the Python wheel.

---

### Task 1: Deterministic citation model and extraction

**Files:**
- Create: `src/autocite_mcp/models.py`
- Create: `src/autocite_mcp/extractors.py`
- Create: `src/autocite_mcp/engine.py`
- Create: `src/autocite_mcp/rules.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Produces: `CitationEngine.extract(text: str) -> list[CitationMatch]`
- Produces: `CitationEngine.analyze(text: str, mode: str) -> dict[str, Any]`

- [x] Write failing tests for case, statute, regulation, and short-form extraction.
- [x] Run the focused tests and confirm missing-module failures.
- [x] Implement dataclasses, eyecite-backed extraction and antecedent grouping, malformed-citation fallbacks, mode validation, and structured reports.
- [x] Run the focused and complete test suites.

### Task 2: Conservative autofix pipeline

**Files:**
- Modify: `src/autocite_mcp/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Produces: `CitationEngine.fix(text: str, mode: str) -> dict[str, Any]`

- [x] Write failing tests for reporter normalization, code normalization, section spacing, and `Id.` correction.
- [x] Implement issue-backed, non-overlapping reverse-order replacements.
- [x] Confirm context-sensitive issues remain unresolved.
- [x] Run all tests.

### Task 3: Structured citation generation

**Files:**
- Create: `src/autocite_mcp/formatters.py`
- Test: `tests/test_formatters.py`

**Interfaces:**
- Produces: `generate_citation(source_type, fields, mode, output_style) -> str`
- Produces: `supported_source_types() -> list[str]`

- [x] Write failing tests for case, statute, and journal generation and missing-field refusal.
- [x] Implement source-specific required-field contracts and formatting.
- [x] Add court-document, website, AI-content, book, constitution, regulation, and archival formatters.
- [x] Run all tests.

### Task 4: Optional CourtListener verification

**Files:**
- Create: `src/autocite_mcp/verifiers.py`
- Test: `tests/test_verifier.py`

**Interfaces:**
- Produces: `CourtListenerVerifier.verify_text(text: str) -> dict[str, Any]`

- [x] Write failing async tests using a fake HTTP client.
- [x] Implement token handling, request limits, normalized results, and network errors.
- [x] Confirm missing tokens produce structured unavailable results.
- [x] Run all tests.

### Task 5: Shared application tools and CLI

**Files:**
- Create: `src/autocite_mcp/tools.py`
- Create: `src/autocite_mcp/cli.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Produces: document check/fix, single-citation check, conversion, issue explanation, capability manifest, and verification functions.

- [x] Write failing tests for the shared tool contracts.
- [x] Implement shared functions independently of MCP registration.
- [x] Implement JSON CLI commands for check, fix, generate, and capabilities.
- [x] Run all tests.

### Task 6: MCP server, packaging, CI, and documentation

**Files:**
- Create: `src/autocite_mcp/server.py`
- Create: `pyproject.toml`
- Create: `.github/workflows/ci.yml`
- Create: `examples/claude_desktop_config.json`
- Modify: `README.md`

**Interfaces:**
- Produces: `autocite-mcp` and `autocite` console scripts.
- Produces: eight MCP tools, two MCP resources, and three MCP prompts.

- [x] Register thin FastMCP wrappers over shared functions.
- [x] Pin the stable MCP v1 dependency line below v2.
- [x] Add multi-version test and package-build CI.
- [x] Document installation, client configuration, limitations, licensing, and development.
- [x] Compile every Python module and run the full test suite.
