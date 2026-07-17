# Contributing to AutoCite

## Development setup

AutoCite uses [`uv`](https://docs.astral.sh/uv/) for environment and dependency management.

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Equivalently, `uv sync --extra dev` will create and populate `.venv` in one step. Add `slm`, `retrieval`, or `desktop` extras only if you are working on those subsystems; the deterministic core has no ML dependencies.

## Running checks

```bash
uv run pytest
uv run ruff check src tests training
uv run python -m py_compile src/autocite_mcp/*.py
```

Some tests are opt-in. `real_model`-marked tests load the full local model and are skipped by default; see `pyproject.toml` for the marker declaration.

Before proposing changes that touch citation rules or the evaluator, also run:

```bash
uv run autocite eval --file evals/gold.jsonl
```

## Project layout

- `src/autocite_mcp/` — the package.
  - `server.py` — MCP tool, resource, and prompt declarations (FastMCP).
  - `hosting.py` — transport selection, bearer-token gate, and loopback/remote bind policy.
  - `tools.py` — implementations behind the MCP tool surface.
  - `engine.py`, `deterministic_rules.py`, `rules.py`, `rule_families/` — the deterministic citation checker and its declared rule catalog, grouped by source family (cases, statutes, journals, and so on).
  - `document_ir.py`, `documents.py`, `extractors.py` — document parsing into a structure-preserving intermediate representation for DOCX, Markdown, and text PDF.
  - `citation_graph.py` — authority identity, occurrence, and short-form resolution graph.
  - `deep_review.py`, `sources.py`, `verifiers.py`, `evidence.py` — CourtListener-backed source retrieval and quotation/pincite comparison.
  - `retrieval.py`, `reference_library/` — local rule-context retrieval over approved Markdown summaries.
  - `jurisdictions.py` — federal, California, and generic state jurisdiction profiles.
  - `slm.py`, `slm_runtime.py`, `proposal_models.py` — optional local SLM classification and proposal layer.
  - `formatters.py`, `knowledge.py`, `workspace.py`, `models.py`, `local_product.py`, `cli.py`, `desktop.py`, `setup_clients.py` — citation formatting, knowledge packs, the MCP Apps workspace, model lifecycle management, the CLI, and host setup.
  - `evals.py`, `evaluation_framework.py` — the gold-corpus and document-level evaluation harnesses.
- `tests/` — pytest suite, mirroring the module layout above.
- `docs/` — architecture, security, hosting, evaluation, and phase-history documentation.
- `skills/` — routing and workflow skill packages for compatible hosts.
- `training/` — dataset construction, SFT training, and evaluation scripts for the optional local SLM adapter. This is a separate, opt-in track from the deterministic engine.
- `evals/` — the gold and system-level evaluation corpora.
- `reference/` — third-party reference materials under separate license; excluded from the wheel and never returned through MCP resources (see `THIRD_PARTY_NOTICES.md`).

## Safety philosophy

Deterministic validation controls every automatic edit. The optional local SLM layer can classify ambiguous issues and propose structured repairs, but a proposal is never applied on its own; it is only eligible when it exactly agrees with a high-confidence deterministic autofix. Only findings at the `safe_auto_fix` correction level are applied without explicit approval.

This has direct consequences for tests:

- New deterministic rules need a declared `RuleSpec` with mode separation, a correction level, and provenance.
- New rule behavior needs both positive tests (the fix applies correctly) and guardrail tests (the fix does *not* fire on inputs that only superficially resemble the pattern, and does not silently invent facts such as a reporter, court, year, author, pincite, or URL).
- Changes to the SLM proposal path need tests showing that disagreement with the deterministic layer is refused, not overridden.
- Changes to retrieval or deep review need tests confirming retrieved text is treated as untrusted quoted evidence, never as instructions.

AutoCite does not claim complete Bluebook compliance; exact supported, partial, and unsupported coverage is tracked in `docs/RULE_COVERAGE.json` and should be updated alongside any rule change.

## Pull request expectations

- `uv run pytest` passes.
- `uv run ruff check src tests training` is clean.
- Documentation and commit messages do not claim complete Bluebook compliance or resolve legal-judgment questions (good-law status, controlling authority, proposition support, or treatment) that AutoCite explicitly leaves to the reader.
- Changes to rule coverage, tool behavior, or security/hosting posture update the relevant doc in `docs/` in the same PR.
- Keep the core dependency set lightweight; optional ML, retrieval, and desktop dependencies belong in extras, not core `dependencies`.
