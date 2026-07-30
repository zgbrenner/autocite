# AutoCite Release Verification

This checklist is the evidence required before merging a release branch or describing a desktop release as complete.

## Environment

Use Python 3.12 for the primary local release build and retain CI compatibility checks for Python 3.10, 3.11, 3.12, and 3.13.

```bash
uv sync --extra dev
```

## Repository verification

Run every command from the repository root in a clean checkout:

```bash
uv run ruff check src tests training scripts
uv run pytest
uv run python -m compileall -q src/autocite_mcp training scripts
uv run autocite eval --file evals/gold.jsonl
uv run autocite eval-system --file evals/system/documents.jsonl --split test --ablations
uv build
```

A release is blocked by any unsafe automatic edit, non-citation prose modification, unsupported factual introduction, unresolved antecedent guess, local-mode network call, invalid package boundary, or failing mandatory deterministic gate.

Optional model, reranker, GPU, GLiNER, and hybrid-embedding evaluations may report `not_run` when their deliberately optional runtimes are absent. They must never be reported as passing without being run.

## Focused preservation and workspace verification

Run the high-risk desktop suites explicitly so failures are easy to isolate:

```bash
uv run pytest \
  tests/test_review_session.py \
  tests/test_review_view_model.py \
  tests/test_desktop_review_ui.py \
  tests/test_docx_preservation.py \
  tests/test_desktop_export.py \
  tests/test_desktop_preservation.py \
  tests/test_desktop_console.py \
  tests/test_real_document_eval.py \
  tests/test_release_workflows.py
```

These tests must prove:

- stable review IDs and deterministic accept, pending, and reject decisions;
- bounded undo and redo behavior;
- filters, search, navigation, and decision-aware preview generation;
- UTF-16-correct Qt source highlighting for non-BMP characters;
- refusal of overlapping or ambiguously mapped edits;
- tracked and untracked Word edits;
- Word-comment anchoring and audit-only fallback for unsafe annotation mappings;
- byte preservation for untouched DOCX parts;
- internal relationship and XML validation;
- source-fingerprint checks and atomic export;
- permissioned real-document manifest boundaries and mandatory release gates.

## Desktop build verification

```bash
uv sync --extra desktop-build
uv run pyinstaller packaging/autocite-desktop.spec --clean --noconfirm
```

Run both packaged self-tests:

```bash
# Linux and macOS
dist/AutoCite/AutoCite --self-test
dist/AutoCite/AutoCite --self-test-preservation

# Windows PowerShell
.\dist\AutoCite\AutoCite.exe --self-test
.\dist\AutoCite\AutoCite.exe --self-test-preservation
```

The ordinary self-test must exit with status 0 after performing a deterministic citation correction and creating a nonempty reviewed DOCX.

The preservation self-test must exit with status 0 after reviewing a structured original DOCX, applying the preservation export, validating the resulting Word package, confirming a header and table remain intact, and confirming that the source hash is unchanged.

## Portable archive verification

For every platform archive:

1. Recompute SHA-256 and compare it with the matching `.sha256` file.
2. Reject absolute archive paths, `..` traversal, duplicate paths, symlinks, and device paths.
3. Confirm `START HERE.txt`, `LICENSE.txt`, `BUILD-MANIFEST.json`, the executable, and required runtime files exist.
4. Confirm the external manifest identifies the exact version, commit, platform, archive hash, and these flags:
   - `portable: true`
   - `requires_installer: false`
   - `requires_python: false`
5. Extract to a new ordinary folder and run both packaged self-tests from the extracted directory.

## Functional desktop acceptance

On Windows, test the release on a computer with 8 GB RAM and no dedicated GPU:

1. Extract the ZIP without installing Python or any runtime.
2. Launch AutoCite directly from the extracted folder.
3. Confirm Standard local review is the default and optional model mode is unavailable unless separately installed.
4. Review representative TXT, DOCX, and searchable PDF documents.
5. Confirm the UI remains responsive during review.
6. Exercise accept, reject, reset, accept-all-safe, undo, redo, search, every status filter, severity filtering, source-type filtering, rule-family filtering, previous and next navigation, and exact original-text selection.
7. Confirm the corrected preview changes when a safe edit is rejected and restores when it is accepted again.
8. Export a reviewed DOCX and JSON audit report using non-default decisions.
9. For an original DOCX, confirm the export reports `original_docx`, preserves representative headers, footers, tables, styles, numbering, comments, footnotes, and endnotes that were not modified, and applies only accepted mapped edits.
10. For TXT, Markdown, and PDF, confirm the export is clearly labeled `reconstructed_text`.
11. Confirm the source-file hash is unchanged.
12. Confirm missing, unsupported, oversized, image-only, unreadable, changed-after-review, and unsafe-DOCX-mapping cases produce clear recovery messages.
13. Confirm standard review works with network access disabled.
14. Confirm keyboard-only operation reaches all review and export controls.
15. Confirm screen-reader names are meaningful for file selection, review options, filters, review list, item actions, previews, and exports.

Record the laptop model, Windows version, RAM, processor, test-document sizes, startup time, review times, peak observed memory, and results in the release notes or an attached verification report.

## Permissioned real-document evaluation

When authorized documents are available, run:

```bash
uv run autocite-eval-real \
  --manifest /secure/autocite-eval/manifest.jsonl \
  --documents-root /secure/autocite-eval/documents \
  --output outputs/real-document-evaluation.json
```

A report may be described as real-document evidence only when every document has an explicit permission basis and the evaluated sources remain outside the repository. The report must not contain source text or absolute paths.

The real-document release gate fails on citation or issue-code disagreement, corrected-text disagreement where gold text is provided, unsafe automatic edits, guessed antecedents, unexpected local-mode network activity, source mutation, invalid DOCX output, or review exceptions.

Do not imply that the synthetic corpus has been replaced by real-world evidence until this command has actually been run against a permissioned test or holdout set.

## GitHub Actions interpretation

A workflow job that records ordinary steps and then fails is repository evidence. Read the failing step and its logs.

A workflow job that reaches a terminal failure state with **zero recorded steps** did not execute checkout, setup, tests, or build commands. That pattern indicates runner allocation, account billing, policy, or another Actions infrastructure failure. It is not evidence that repository tests failed. Resolve the Actions availability issue separately and use the complete clean-checkout verification above in the meantime.

Current PR #20 runs exhibited the zero-step pattern on the ordinary test matrix and on an intentionally minimal runner probe, which isolates the current failure outside the repository command sequence.

## Merge gate

Merge only after:

- the complete repository verification passes;
- both packaged self-tests pass on every supported release platform;
- the Windows 8 GB acceptance test passes;
- an independent review finds no unresolved P0 or P1 defects;
- release version references agree across `pyproject.toml`, the desktop application, filenames, manifests, documentation, and release notes;
- the expected PR head SHA is supplied to the merge operation.

## Release gate

Do not announce completion until the published assets have been downloaded from the GitHub Release and independently reverified. State clearly whether binaries are signed, whether permissioned real-document evaluation ran, which hardware was tested, and which legal verification questions remain outside AutoCite's scope.