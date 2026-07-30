# AutoCite Production Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the unfinished 0.6.0 portable desktop safely, then establish the 0.7.0 foundations for preservation-first DOCX editing, review decisions, and real-document evaluation.

**Architecture:** Keep citation analysis deterministic and unchanged. Add an isolated review-session layer that turns analysis results into stable user decisions, plus an isolated DOCX package editor that applies accepted edits to a copy of the original Word package and refuses ambiguous mappings. The desktop controller chooses preservation export for DOCX sources and retains reconstructed export for text, Markdown, and PDF inputs.

**Tech Stack:** Python 3.10+, pytest, python-docx, lxml through python-docx, `zipfile`, PySide6, PyInstaller, GitHub Actions, existing AutoCite engine and DocumentIR.

## Global Constraints

- Standard desktop review must work offline on an 8 GB RAM Windows laptop without a dedicated GPU.
- Standard desktop review must not import or package PyTorch, Transformers, GLiNER, sentence-transformers, or model weights.
- No automatic change may depend solely on a model proposal.
- The source document must never be overwritten or modified.
- Exports must be atomic and fail closed.
- AutoCite must not claim good-law status, controlling authority, precedential weight, proposition support, or complete Bluebook compliance.
- New features require failing tests before production code.
- Do not add telemetry or mandatory cloud services.

---

### Task 1: Recover the 0.6.0 release branch and make verification evidence explicit

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/desktop.yml`
- Modify: `packaging/RELEASE-NOTES.md`
- Create: `docs/RELEASE-VERIFICATION.md`
- Test: workflow syntax and packaging smoke commands documented below

**Interfaces:**
- Consumes: existing version `0.6.0`, desktop self-test `autocite-desktop --self-test`, packaging script.
- Produces: a release workflow that separates repository test failures from runner-allocation failures and a reproducible local verification checklist.

- [ ] **Step 1: Add a failing workflow contract test**

Create `tests/test_release_workflows.py` that parses the workflow text and asserts:

```python
from pathlib import Path


def test_desktop_release_requires_test_build_smoke_and_checksum_stages():
    workflow = Path('.github/workflows/desktop.yml').read_text(encoding='utf-8')
    for required in ('verify:', 'build-desktop:', '--self-test', 'Verify release checksums'):
        assert required in workflow


def test_ci_uploads_diagnostics_even_after_failure():
    workflow = Path('.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'if: always()' in workflow
    assert 'pytest-results.xml' in workflow
```

- [ ] **Step 2: Run the workflow contract tests and confirm the intended failure**

Run: `python -m pytest tests/test_release_workflows.py -v`

Expected: at least one assertion fails if the workflow does not expose all required release stages.

- [ ] **Step 3: Make workflow diagnostics and local verification deterministic**

Keep ordinary CI on Python 3.10 through 3.13. Ensure each test command fails with `pipefail`, preserves logs, and uploads them under `if: always()`. Keep the desktop build matrix on Windows x64, macOS x64, and Linux x64; run the packaged self-test before packaging; verify every ZIP, checksum, and manifest before creating the immutable tag.

Document exact local commands in `docs/RELEASE-VERIFICATION.md`:

```bash
uv sync --extra dev
uv run ruff check src tests training scripts
uv run pytest
uv run python -m compileall -q src/autocite_mcp training scripts
uv run autocite eval --file evals/gold.jsonl
uv build
uv sync --extra desktop-build
uv run pyinstaller packaging/autocite-desktop.spec --clean --noconfirm
dist/AutoCite/AutoCite --self-test
```

The document must also state that a GitHub job with zero recorded steps is an infrastructure or runner-allocation failure, not evidence that repository tests failed.

- [ ] **Step 4: Re-run the workflow contract test**

Run: `python -m pytest tests/test_release_workflows.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml .github/workflows/desktop.yml packaging/RELEASE-NOTES.md docs/RELEASE-VERIFICATION.md tests/test_release_workflows.py
git commit -m "ci: make AutoCite release verification reproducible"
```

---

### Task 2: Add stable review-session decisions

**Files:**
- Create: `src/autocite_mcp/review_session.py`
- Create: `tests/test_review_session.py`
- Modify: `src/autocite_mcp/desktop.py`

**Interfaces:**
- Consumes: `review_document` result dictionaries containing `applied_edits`, `remaining_issues`, and `rule_findings`.
- Produces: `ReviewSession.from_result(result)`, `ReviewItem`, `ReviewDecision`, `ReviewSession.accept()`, `ReviewSession.reject()`, `ReviewSession.reset()`, `ReviewSession.accept_all_safe()`, and `ReviewSession.export_plan()`.

- [ ] **Step 1: Write failing decision tests**

```python
from autocite_mcp.review_session import ReviewDecision, ReviewSession


def test_review_session_defaults_safe_edits_to_accepted_and_review_items_to_pending():
    result = {
        'applied_edits': [
            {'code': 'STATUTE_CODE_ABBREVIATION', 'start': 7, 'end': 10,
             'original': 'USC', 'suggestion': 'U.S.C.',
             'correction_level': 'safe_auto_fix', 'confidence': 'high'}
        ],
        'remaining_issues': [
            {'code': 'PROPOSITION_PINCITE_REVIEW', 'start': 20, 'end': 30,
             'original': 'Smith', 'correction_level': 'review_required'}
        ],
        'rule_findings': [],
    }
    session = ReviewSession.from_result(result)
    assert session.items[0].decision is ReviewDecision.ACCEPTED
    assert session.items[1].decision is ReviewDecision.PENDING


def test_export_plan_contains_only_accepted_text_edits_and_all_unresolved_annotations():
    session = ReviewSession.from_result(FIXTURE_RESULT)
    session.reject(session.items[0].item_id)
    plan = session.export_plan()
    assert plan.text_edits == ()
    assert len(plan.annotations) == 1
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_review_session.py -v`

Expected: import failure because `review_session.py` does not exist.

- [ ] **Step 3: Implement immutable review models**

Use frozen dataclasses and enums. Stable item IDs must be SHA-256 hashes of the normalized item type, issue code, source range, original text, and suggestion. Reject overlapping accepted edits in `export_plan()` with a clear `ValueError`. Deduplicate findings that appear in both `remaining_issues` and `rule_findings`.

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest tests/test_review_session.py -v`

Expected: PASS.

- [ ] **Step 5: Integrate the session into desktop result loading**

`DesktopReviewState` gains `review_session: ReviewSession | None`. `state_from_result()` builds a session. Existing JSON audit reports include item IDs and decisions without including full local source paths.

- [ ] **Step 6: Run desktop and review-session tests**

Run: `python -m pytest tests/test_review_session.py tests/test_desktop.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/autocite_mcp/review_session.py src/autocite_mcp/desktop.py tests/test_review_session.py tests/test_desktop.py
git commit -m "feat: add stable citation review decisions"
```

---

### Task 3: Build preservation-first DOCX mapping and validation

**Files:**
- Create: `src/autocite_mcp/docx_preservation.py`
- Create: `tests/test_docx_preservation.py`
- Create: `tests/fixtures/docx/README.md`

**Interfaces:**
- Consumes: original DOCX bytes plus `ExportPlan` text edits and annotations.
- Produces: `index_docx_text(payload) -> DocxTextIndex`, `apply_docx_export_plan(payload, plan, *, tracked=True) -> PreservedDocxResult`, and `validate_docx_package(payload) -> DocxValidationReport`.

- [ ] **Step 1: Write failing preservation tests**

Construct DOCX fixtures in tests with `python-docx`; do not commit proprietary documents.

```python
def test_index_maps_body_table_header_footer_footnote_and_endnote_text():
    payload = make_structured_docx()
    index = index_docx_text(payload)
    assert '42 USC §1983' in index.text
    assert {location.part_name for location in index.locations} >= {
        'word/document.xml', 'word/header1.xml', 'word/footer1.xml'
    }


def test_apply_plan_preserves_unmodified_parts_byte_for_byte():
    payload = make_structured_docx()
    before = zip_parts(payload)
    result = apply_docx_export_plan(payload, one_safe_edit_plan(), tracked=True)
    after = zip_parts(result.payload)
    for name in before.keys() - result.modified_parts:
        assert before[name] == after[name]


def test_ambiguous_cross_node_edit_is_refused_instead_of_corrupting_document():
    with pytest.raises(DocxMappingError, match='unambiguous'):
        apply_docx_export_plan(make_split_run_docx(), crossing_edit_plan())
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_docx_preservation.py -v`

Expected: import failure because `docx_preservation.py` does not exist.

- [ ] **Step 3: Implement the package index**

Read the DOCX as OPC ZIP. Parse text-bearing Word parts in stable order: document, footnotes, endnotes, headers, footers, comments, and text boxes reachable in those parts. Index `w:t`, tabs, breaks, paragraph boundaries, and part-relative XML nodes. Reject DTD/entity content. Enforce existing document-size and decompressed-part limits.

- [ ] **Step 4: Implement fail-closed tracked text edits**

Initially accept only edits whose complete source range maps to one contiguous `w:t` node or an explicitly supported adjacent-run span within one paragraph. Wrap deletions in `w:del` and insertions in `w:ins`, with UTC timestamps and AutoCite as author. Preserve run properties. Refuse edits through fields, hyperlinks, bookmarks, existing tracked-change boundaries, drawings, or multiple package parts until dedicated tests support them.

- [ ] **Step 5: Implement review comments**

When an annotation maps to a supported range, create or extend `word/comments.xml`, allocate a collision-free comment ID, add comment range start/end and reference nodes, and update relationships and content types only when required. When mapping is unsafe, keep the annotation in the audit report and return it in `unanchored_annotations` instead of modifying the DOCX.

- [ ] **Step 6: Validate output packages**

Check ZIP integrity, `[Content_Types].xml`, root relationships, every internal relationship target, uniqueness of comment IDs, XML parseability, and presence of the main document part. Return a structured report and raise before writing if invalid.

- [ ] **Step 7: Run preservation tests**

Run: `python -m pytest tests/test_docx_preservation.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/autocite_mcp/docx_preservation.py tests/test_docx_preservation.py tests/fixtures/docx/README.md
git commit -m "feat: preserve original DOCX structure during review export"
```

---

### Task 4: Integrate preservation export into desktop, CLI, and MCP

**Files:**
- Modify: `src/autocite_mcp/desktop.py`
- Modify: `src/autocite_mcp/tools.py`
- Modify: `src/autocite_mcp/server.py`
- Modify: `src/autocite_mcp/output_models.py`
- Modify: `src/autocite_mcp/cli.py`
- Modify: `tests/test_desktop.py`
- Create: `tests/test_preserved_export_tools.py`

**Interfaces:**
- Consumes: original uploaded DOCX bytes retained in an authorized in-memory review envelope or explicitly supplied to an export call, plus a serialized `ExportPlan`.
- Produces: `export_preserved_review_docx` tool and CLI command; desktop automatically chooses preservation export for DOCX sources.

- [ ] **Step 1: Write failing integration tests**

```python
async def test_desktop_docx_export_preserves_original_table_and_header(tmp_path):
    source = write_structured_docx(tmp_path / 'brief.docx')
    state = await DesktopReviewController().review_file(source, mode='bluepages')
    output = tmp_path / 'review.docx'
    metadata = DesktopReviewController().export_docx(state, output)
    assert metadata['preservation_mode'] == 'original_docx'
    assert read_header(output) == 'Privileged Draft'
    assert read_table_cell(output, 0, 0) == 'Record citation'


async def test_preserved_export_refuses_missing_original_bytes():
    with pytest.raises(ValueError, match='original DOCX'):
        await export_preserved_review_docx(review_result=RESULT, original_docx_base64=None)
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest tests/test_preserved_export_tools.py tests/test_desktop.py -v`

Expected: missing API or wrong preservation mode.

- [ ] **Step 3: Retain source bytes safely for desktop state**

Store source bytes only in memory in `DesktopReviewState`, exclude them from repr and JSON reports, and release them when a new file is opened or the window closes. Do not place document bytes in settings or logs.

- [ ] **Step 4: Add preserved export API**

Expose a separate tool rather than silently changing the existing reconstruction contract. Return preservation mode, modified parts, unanchored annotations, validation summary, hash, and size. Keep the current `export_review_docx` behavior for text-only workflows.

- [ ] **Step 5: Add CLI support**

Add:

```bash
autocite review-file brief.docx --export-preserved reviewed.docx --audit-report reviewed.json
```

The command refuses to overwrite the source and exits nonzero on mapping or validation failure.

- [ ] **Step 6: Run integration tests**

Run: `python -m pytest tests/test_preserved_export_tools.py tests/test_desktop.py tests/test_server.py tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/autocite_mcp/desktop.py src/autocite_mcp/tools.py src/autocite_mcp/server.py src/autocite_mcp/output_models.py src/autocite_mcp/cli.py tests/test_desktop.py tests/test_preserved_export_tools.py tests/test_server.py tests/test_cli.py
git commit -m "feat: expose preservation-first reviewed DOCX export"
```

---

### Task 5: Add review controls and exact navigation to the desktop

**Files:**
- Modify: `src/autocite_mcp/desktop.py`
- Create: `tests/test_desktop_review_controls.py`

**Interfaces:**
- Consumes: `ReviewSession` and indexed source ranges.
- Produces: accept, reject, reset, accept-all-safe, filter, source navigation, undo, redo, and final-review checklist actions.

- [ ] **Step 1: Write failing UI-model tests without launching a visible window**

Extract a UI-independent `DesktopReviewViewModel` and test:

```python
def test_accept_reject_filter_and_undo_are_deterministic():
    model = DesktopReviewViewModel(session_fixture())
    first = model.visible_items[0]
    model.reject(first.item_id)
    assert model.item(first.item_id).decision.value == 'rejected'
    model.undo()
    assert model.item(first.item_id).decision.value == 'accepted'
    model.set_filter('pending')
    assert all(item.decision.value == 'pending' for item in model.visible_items)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_desktop_review_controls.py -v`

Expected: missing `DesktopReviewViewModel`.

- [ ] **Step 3: Implement the view model**

Keep UI state separate from Qt widgets. History stores immutable session snapshots with a bounded depth of 100. Filtering supports all, accepted, rejected, pending, unsupported, severity, source type, and rule family.

- [ ] **Step 4: Wire accessible Qt controls**

Add buttons and shortcuts for accept, reject, undo, redo, next item, previous item, accept all safe, and final review. Selecting an item highlights its range in original and corrected text when offsets are available. Every control receives an accessible name and tooltip.

- [ ] **Step 5: Run view-model and desktop tests**

Run: `python -m pytest tests/test_desktop_review_controls.py tests/test_desktop.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/autocite_mcp/desktop.py tests/test_desktop_review_controls.py tests/test_desktop.py
git commit -m "feat: add per-citation review controls and navigation"
```

---

### Task 6: Add a real-document evaluation harness without committing confidential documents

**Files:**
- Create: `evals/real_documents/README.md`
- Create: `evals/real_documents/schema.json`
- Create: `src/autocite_mcp/real_document_eval.py`
- Create: `tests/test_real_document_eval.py`
- Modify: `src/autocite_mcp/cli.py`
- Modify: `docs/EVALUATION_REPORT.md`

**Interfaces:**
- Consumes: a JSONL manifest and local document root supplied at runtime.
- Produces: per-document and aggregate metrics for extraction, safe fixes, abstention, unintended changes, DOCX preservation, runtime, and peak memory.

- [ ] **Step 1: Write failing manifest and metric tests**

```python
def test_manifest_rejects_paths_outside_document_root(tmp_path):
    with pytest.raises(ValueError, match='document root'):
        load_real_document_manifest(manifest_with('../secret.docx'), tmp_path)


def test_metrics_count_unsafe_edit_as_release_blocker():
    result = score_real_document(expected_fixture(), actual_with_prose_change())
    assert result.unsafe_automatic_edits == 1
    assert result.release_gate_passed is False
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_real_document_eval.py -v`

Expected: missing module.

- [ ] **Step 3: Implement strict local manifests**

Require document IDs, relative paths, licenses or permission notes, split, expected citations, expected findings, expected safe text, and optional DOCX structural assertions. Resolve paths beneath a caller-provided root and never include source text in aggregate reports by default.

- [ ] **Step 4: Implement metrics and CLI**

Add:

```bash
autocite eval-real --manifest evals/real_documents/local.jsonl --documents-root /secure/eval-documents --output outputs/real-eval.json
```

Use `tracemalloc` for Python memory and monotonic timing. Release gates fail on any unsafe automatic edit, non-citation prose modification, unresolved antecedent guess, source overwrite, invalid DOCX, or unexpected network call in local mode.

- [ ] **Step 5: Run evaluation-harness tests**

Run: `python -m pytest tests/test_real_document_eval.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add evals/real_documents src/autocite_mcp/real_document_eval.py src/autocite_mcp/cli.py tests/test_real_document_eval.py docs/EVALUATION_REPORT.md
git commit -m "feat: add permissioned real-document evaluation harness"
```

---

### Task 7: Complete repository verification and review

**Files:**
- Review all files changed by Tasks 1 through 6.
- Modify only files required by discovered defects.

**Interfaces:**
- Consumes: complete branch.
- Produces: fresh verification evidence and a reviewed PR.

- [ ] **Step 1: Run formatting and static checks**

```bash
uv run ruff check src tests training scripts
uv run python -m compileall -q src/autocite_mcp training scripts
```

Expected: exit 0.

- [ ] **Step 2: Run all tests**

```bash
uv run pytest
```

Expected: zero failures; opt-in real-model tests may be skipped only when explicitly marked.

- [ ] **Step 3: Run deterministic evaluations**

```bash
uv run autocite eval --file evals/gold.jsonl
uv run autocite eval-system --file evals/system/documents.jsonl --split test --ablations
```

Expected: every mandatory deterministic release gate passes; optional runtimes report `not_run` rather than fabricated scores.

- [ ] **Step 4: Build distributions and desktop bundle**

```bash
uv build
uv sync --extra desktop-build
uv run pyinstaller packaging/autocite-desktop.spec --clean --noconfirm
dist/AutoCite/AutoCite --self-test
```

On Windows use `dist\AutoCite\AutoCite.exe --self-test`.

Expected: all commands exit 0.

- [ ] **Step 5: Run clean-clone and low-memory acceptance**

Test from a clean checkout. On the target Windows laptop with 8 GB RAM and no dedicated GPU: extract the ZIP, launch without installing dependencies, review representative TXT, DOCX, and searchable PDF files, export preserved DOCX and JSON reports, and verify that the source hashes remain unchanged.

- [ ] **Step 6: Request independent code review**

Review specifically for Word package corruption, offset mapping errors, unsafe automatic edits, privacy leaks, archive traversal, XML entity processing, thread lifetime bugs, and release-workflow mistakes.

- [ ] **Step 7: Fix every validated P0 and P1 finding with a new failing regression test**

Run the focused regression, then the complete verification suite again.

- [ ] **Step 8: Commit final corrections**

```bash
git add -A
git commit -m "fix: resolve final AutoCite production review findings"
```

---

### Task 8: Merge and publish the verified release

**Files:**
- Modify: `pyproject.toml` only if the final release number changes.
- Modify: `packaging/RELEASE-NOTES.md`
- Modify: `CHANGELOG.md` if present.

**Interfaces:**
- Consumes: verified PR head SHA and portable release artifacts.
- Produces: merged `main`, immutable version tag, GitHub Release, Windows/macOS/Linux portable archives, checksums, manifests, wheel, and source distribution.

- [ ] **Step 1: Confirm branch and release metadata agree**

Verify `pyproject.toml`, application fallback version, filenames, release notes, and manifest version are identical.

- [ ] **Step 2: Merge with expected-head protection**

Use the PR head SHA when merging so GitHub refuses the operation if new commits appeared after verification.

- [ ] **Step 3: Build and inspect release artifacts**

The release must contain:

```text
AutoCite-windows-x64-v<version>.zip
AutoCite-windows-x64-v<version>.zip.sha256
AutoCite-windows-x64-v<version>.manifest.json
AutoCite-macos-x64-v<version>.zip
AutoCite-linux-x64-v<version>.zip
autocite_mcp-<version>-py3-none-any.whl
autocite_mcp-<version>.tar.gz
```

- [ ] **Step 4: Download the published Windows ZIP and verify it independently**

Recompute SHA-256, inspect ZIP paths for traversal, validate the embedded build manifest, confirm the executable and runtime files exist, and run the packaged self-test on Windows.

- [ ] **Step 5: Publish a truthful release summary**

State exactly which verification commands ran, which hardware was tested, which checks remain outside AutoCite's scope, and whether binaries are signed.

- [ ] **Step 6: Close the milestone only after release asset verification succeeds**

Do not describe the release as complete before this step.