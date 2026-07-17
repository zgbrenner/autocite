# AutoCite SLM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-safe Qwen3.5-0.8B citation-review layer, training pipeline, and evaluation tooling to AutoCite.

**Architecture:** The existing deterministic engine remains the only unconditional edit path. An optional SLM proposes structured citation findings, and a dependency-light validator rejects malformed, mismatched, unsupported, or hallucinated proposals before any edit can be applied.

**Tech Stack:** Python 3.10+, dataclasses, pytest, MCP, Transformers, TRL, PEFT, Trackio, Hugging Face Jobs.

## Global Constraints

- Default review behavior must remain unchanged and must not download model weights.
- The target model is `Qwen/Qwen3.5-0.8B`.
- Both Bluepages and Whitepages must be supported.
- Missing citation facts must never be invented.
- Model failure must fall back to deterministic results.
- Only validated high-confidence SLM proposals may be applied.
- English-language U.S. legal citations are the first-release scope.

---

### Task 1: Structured proposal contract and validator

**Files:**
- Create: `src/autocite_mcp/slm.py`
- Test: `tests/test_slm.py`

**Interfaces:**
- Produces: `SLMProposal.from_mapping(payload)`, `validate_proposal(proposal, text, expected_mode, expected_source_type)`, and `apply_validated_proposals(text, proposals)`.

- [ ] **Step 1: Write failing contract tests** for valid parsing, malformed JSON, mismatched spans, unsupported facts, prohibited legal-status claims, overlapping edits, and conservative application.
- [ ] **Step 2: Run `uv run pytest tests/test_slm.py -q`** and confirm import or assertion failures occur because the SLM module is absent.
- [ ] **Step 3: Implement immutable proposal and validation result dataclasses**, strict enum validation, source-span equality, material-token comparison, prohibited-claim checks, and right-to-left non-overlapping application.
- [ ] **Step 4: Run `uv run pytest tests/test_slm.py -q`** and require all contract tests to pass.

### Task 2: Runtime adapter and hybrid orchestrator

**Files:**
- Create: `src/autocite_mcp/slm_runtime.py`
- Modify: `src/autocite_mcp/tools.py`
- Test: `tests/test_slm_runtime.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: proposal validator from Task 1 and existing `CitationEngine` output.
- Produces: `SLMRuntime` protocol, `TransformersSLMRuntime`, `hybrid_review(text, mode, deterministic_result, runtime, apply_slm_fixes)` and `slm_review` response fields.

- [ ] **Step 1: Write failing runtime and fallback tests** using callable fake runtimes for successful output, invalid JSON, exceptions, low confidence, and unsupported-fact rejection.
- [ ] **Step 2: Run the focused tests** and confirm failures are caused by missing runtime integration.
- [ ] **Step 3: Implement lazy Transformers loading and hybrid orchestration** with bounded prompts, JSON-only decoding, explicit status values, proposal validation, and deterministic re-analysis after accepted edits.
- [ ] **Step 4: Extend `review_document` and uploaded-document forwarding** with optional `use_slm`, `model_path`, `slm_only`, and `apply_slm_fixes` arguments while preserving existing defaults.
- [ ] **Step 5: Run focused and existing tool tests** and require them to pass.

### Task 3: CLI and MCP exposure

**Files:**
- Modify: `src/autocite_mcp/cli.py`
- Modify: `src/autocite_mcp/server.py`
- Modify: `src/autocite_mcp/tools.py`
- Modify: `src/autocite_mcp/__init__.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: hybrid review parameters from Task 2.
- Produces: CLI flags `--slm`, `--model-path`, `--slm-only`, and `--apply-slm-fixes`; matching optional MCP parameters; capability metadata describing SLM boundaries.

- [ ] **Step 1: Extend parser and MCP signature tests first** and confirm they fail before implementation.
- [ ] **Step 2: Add CLI flags and pass them through both review commands.**
- [ ] **Step 3: Add optional MCP parameters and capability disclosures** without changing the tool list or default behavior.
- [ ] **Step 4: Run CLI, server, and tools tests** and require them to pass.

### Task 4: Dataset builder and gold safety set

**Files:**
- Create: `training/build_dataset.py`
- Create: `training/seed_examples.jsonl`
- Create: `evals/slm_safety.jsonl`
- Test: `tests/test_training_data.py`

**Interfaces:**
- Produces: deterministic JSONL records with `messages`, `metadata`, group-aware `split`, and abstention labels.

- [ ] **Step 1: Write failing dataset tests** for deterministic generation, schema, mode balance, abstention coverage, group separation, and copyrighted-text exclusion markers.
- [ ] **Step 2: Run the focused tests** and confirm the builder is missing.
- [ ] **Step 3: Implement template expansion and group-aware splitting** with a fixed seed and strict schema checks.
- [ ] **Step 4: Add reviewed seed and safety cases** covering both modes and all first-release citation families.
- [ ] **Step 5: Generate a temporary dataset and run the focused tests** to verify requirements.

### Task 5: LoRA training and evaluation scripts

**Files:**
- Create: `training/train_sft.py`
- Create: `training/evaluate_slm.py`
- Create: `training/export_gguf.md`
- Modify: `pyproject.toml`
- Test: `tests/test_training_scripts.py`

**Interfaces:**
- Consumes: dataset records from Task 4.
- Produces: a PEP 723-compatible TRL training entry point, Trackio reporting, Hub push configuration, baseline/hybrid metric reports, and local export instructions.

- [ ] **Step 1: Write failing static and unit tests** for the required base model, LoRA configuration, Trackio, fixed seed, Hub persistence, and metric keys.
- [ ] **Step 2: Run focused tests** and confirm scripts are absent.
- [ ] **Step 3: Implement SFT training with LoRA** using `Qwen/Qwen3.5-0.8B`, train/eval splits, completion-only supervision where supported, Trackio, and `push_to_hub=True`.
- [ ] **Step 4: Implement evaluation** for JSON validity, span accuracy, classification macro F1, exact correction accuracy, abstention, hallucination, and unsafe-apply rate.
- [ ] **Step 5: Add optional dependency groups and GGUF instructions**, then run focused tests.

### Task 6: Documentation and full verification

**Files:**
- Modify: `README.md`
- Create: `docs/SLM.md`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: installation, privacy, training, inference, evaluation, and limitation guidance plus CI coverage for dependency-light SLM tests.

- [ ] **Step 1: Document optional local inference and safety behavior** with exact commands and no claim that the model replaces source review.
- [ ] **Step 2: Add CI checks for dataset generation and SLM safety evaluation** without downloading model weights.
- [ ] **Step 3: Run `uv run ruff check src tests training`.**
- [ ] **Step 4: Run `uv run pytest`.**
- [ ] **Step 5: Run `uv run python -m py_compile src/autocite_mcp/*.py training/*.py`.**
- [ ] **Step 6: Run `uv run autocite eval --file evals/gold.jsonl` and the dependency-light SLM safety evaluator.**
- [ ] **Step 7: Run `uv build` and inspect the wheel to ensure reference and training corpora are excluded as intended.**
