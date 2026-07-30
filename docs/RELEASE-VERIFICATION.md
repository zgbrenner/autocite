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

## Desktop build verification

```bash
uv sync --extra desktop-build
uv run pyinstaller packaging/autocite-desktop.spec --clean --noconfirm
```

Run the packaged self-test:

```bash
# Linux and macOS
dist/AutoCite/AutoCite --self-test

# Windows PowerShell
.\dist\AutoCite\AutoCite.exe --self-test
```

The command must exit with status 0 after performing a deterministic citation correction and creating a nonempty reviewed DOCX.

## Portable archive verification

For every platform archive:

1. Recompute SHA-256 and compare it with the matching `.sha256` file.
2. Reject absolute archive paths, `..` traversal, duplicate paths, symlinks, and device paths.
3. Confirm `START HERE.txt`, `LICENSE.txt`, `BUILD-MANIFEST.json`, the executable, and required runtime files exist.
4. Confirm the external manifest identifies the exact version, commit, platform, archive hash, and these flags:
   - `portable: true`
   - `requires_installer: false`
   - `requires_python: false`
5. Extract to a new ordinary folder and run the packaged self-test from the extracted directory.

## Functional desktop acceptance

On Windows, test the release on a computer with 8 GB RAM and no dedicated GPU:

1. Extract the ZIP without installing Python or any runtime.
2. Launch AutoCite directly from the extracted folder.
3. Confirm Standard local review is the default and optional model mode is unavailable unless separately installed.
4. Review representative TXT, DOCX, and searchable PDF documents.
5. Confirm the UI remains responsive during review.
6. Export a reviewed DOCX and JSON audit report to new paths.
7. Confirm the source-file hash is unchanged.
8. Confirm missing, unsupported, oversized, image-only, and unreadable files produce clear recovery messages.
9. Confirm standard review works with network access disabled.

Record the laptop model, Windows version, RAM, processor, test-document sizes, startup time, review times, peak observed memory, and results in the release notes or an attached verification report.

## GitHub Actions interpretation

A workflow job that records ordinary steps and then fails is repository evidence. Read the failing step and its logs.

A workflow job that reaches a terminal failure state with **zero recorded steps** did not execute checkout, setup, tests, or build commands. That pattern indicates runner allocation, account billing, policy, or another Actions infrastructure failure. It is not evidence that repository tests failed. Resolve the Actions availability issue separately and use the complete clean-checkout verification above in the meantime.

Current PR #20 runs exhibited the zero-step pattern on the ordinary test matrix and on an intentionally minimal runner probe, which isolates the current failure outside the repository command sequence.

## Merge gate

Merge only after:

- the complete repository verification passes;
- the desktop build and packaged self-test pass;
- the Windows 8 GB acceptance test passes;
- an independent review finds no unresolved P0 or P1 defects;
- release version references agree across `pyproject.toml`, the desktop application, filenames, manifests, and release notes;
- the expected PR head SHA is supplied to the merge operation.

## Release gate

Do not announce completion until the published assets have been downloaded from the GitHub Release and independently reverified. State clearly whether binaries are signed and which legal verification questions remain outside AutoCite's scope.