# AutoCite Phase 1 Local Qwen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the published AutoCite Qwen adapter as a configurable, optional, local-only proposal engine behind comprehensive deterministic safety gates.

**Architecture:** A dependency-light model protocol separates disabled and local Qwen implementations. Strict proposal parsing and deterministic validation prevent model output from mutating documents or introducing unsupported facts, while runtime configuration makes downloads, device use, quantization, timeouts, and offline behavior explicit.

**Tech Stack:** Python 3.10+, dataclasses, asyncio, Transformers, PEFT, Accelerate, Torch, pytest, MCP.

## Global Constraints

- Deterministic-only use must not import or require ML packages.
- The model is a proposal engine and never directly modifies document text.
- Bluepages and Whitepages remain separate rule profiles.
- Local-only and offline operation are the defaults.
- No copyrighted citation-manual text is added.
- The published adapter weights are not modified during metadata repair.

---

### Task 1: Proposal contract and deterministic validator

**Files:**
- Modify: `src/autocite_mcp/slm.py`
- Modify: `tests/test_slm.py`

**Interfaces:**
- Produces: `CitationProposal`, `ProposalValidation`, `validate_proposal(...)`, and `eligible_mechanical_proposals(...)`.

- [ ] Add failing tests for the complete schema and invalid abstention, issue-code, offset, prose, unsupported-fact, deterministic-conflict, confidence, legal-claim, rule-profile, and rule-chunk cases.
- [ ] Run the focused tests and confirm each new behavior fails for the intended reason.
- [ ] Implement strict dependency-light parsing and validation with explicit reason codes.
- [ ] Run focused tests and require all cases to pass.

### Task 2: Optional local model interface and runtime configuration

**Files:**
- Create: `src/autocite_mcp/proposal_models.py`
- Modify: `src/autocite_mcp/slm_runtime.py`
- Modify: `pyproject.toml`
- Create: `tests/test_proposal_models.py`

**Interfaces:**
- Produces: `CitationProposalModel`, `DisabledProposalModel`, `LocalQwenProposalModel`, and `ModelRuntimeConfig`.

- [ ] Add failing tests for disabled behavior, lazy imports, configuration validation, explicit downloads, adapter/base loading, offline flags, device selection, quantization, deterministic seeding, context limits, generation limits, and timeout fallback.
- [ ] Run focused tests and verify red state.
- [ ] Implement the protocol, implementations, configuration, and compatibility wrapper without importing ML libraries at module import time.
- [ ] Run focused tests and require green state.

### Task 3: Review and MCP provenance separation

**Files:**
- Modify: `src/autocite_mcp/tools.py`
- Modify: `src/autocite_mcp/server.py`
- Modify: `src/autocite_mcp/cli.py`
- Modify: `tests/test_tools.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes: Phase 1 proposal model and validator.
- Produces: `use_local_model` compatibility control and separately labeled deterministic, model, retrieval, and verification result sections.

- [ ] Add failing tests for the new option, backward-compatible `use_slm`, response provenance sections, and the rule that model output never bypasses deterministic correction validation.
- [ ] Implement CLI/MCP forwarding and stable separated result fields.
- [ ] Run focused tests and require all cases to pass.

### Task 4: Adapter metadata repair and smoke testing

**Files:**
- Modify: `training/train_sft.py`
- Create: `training/smoke_adapter.py`
- Create: `tests/test_real_adapter.py`
- Modify: `tests/test_training_scripts.py`

**Interfaces:**
- Produces: reproducible adapter verification and an opt-in `real_model` pytest marker.

- [ ] Add static and mocked tests requiring `TaskType.CAUSAL_LM`, correct Qwen classes, and five smoke-test outcomes.
- [ ] Verify the tests fail with the current null-task-type workflow.
- [ ] Update training metadata generation and implement the opt-in real smoke script.
- [ ] Test a corrected adapter configuration against the real model before publishing metadata only.
- [ ] Re-run real smoke verification after metadata publication.

### Task 5: Documentation and full Phase 1 verification

**Files:**
- Modify: `README.md`
- Modify: `docs/SLM.md`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: CPU, GPU, quantized, offline, privacy, setup, smoke-test, and failure-mode instructions.

- [ ] Document explicit model installation and confirm that document review never silently downloads models.
- [ ] Document runtime controls and provenance-separated output.
- [ ] Add ordinary mocked CI coverage while excluding the real-model marker.
- [ ] Run Ruff, the complete unit suite, compile checks, deterministic gold evaluation, SLM safety evaluation, and package build.
- [ ] Inspect the wheel to confirm ML dependencies remain optional and training/reference corpora remain excluded.
