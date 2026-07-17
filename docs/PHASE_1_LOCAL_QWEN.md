# Phase 1 — Safe Local Qwen Integration

## Status

Complete. The optional AutoCite Qwen adapter is integrated as a local proposal engine. Deterministic-only operation remains the default and does not import or install ML packages.

## Exact changes

- Added `CitationProposalModel`, `LocalQwenProposalModel`, `DisabledProposalModel`, and validated `ModelRuntimeConfig` interfaces.
- Added lazy base-model plus PEFT-adapter loading with explicit adapter ID, base-model ID, local directory, device, quantization, offline-only, context, generation, timeout, and seed controls.
- Kept Torch, Transformers, PEFT, Accelerate, and Torchvision in the optional `slm` dependency group. Added optional `slm-quantized` support for `bitsandbytes`.
- Expanded the normalized proposal schema with document mode, source type, exact offsets and source text, issue code, replacement, relied-on facts, missing facts, antecedent candidate, confidence, abstention, explanation, and retrieved rule-chunk IDs. Legacy adapter output is normalized into this stricter internal schema.
- Added rejection paths for invalid JSON, unknown issue codes, task and source-span mismatches, source-type and mode mismatches, unsupported rule profiles, unsupported factual additions, missing required facts, deterministic conflicts, low confidence, unattributed retrieved chunks, prohibited legal conclusions, and overlapping edits.
- Changed model-assisted application so a proposal can affect text only when it exactly agrees with a high-confidence deterministic autofix for the same issue and span. Model-only corrections remain suggestions.
- Added `use_local_model` and complete model runtime controls to both review MCP tools while retaining `use_slm` compatibility.
- Separated deterministic edits, remaining deterministic issues, model proposals, retrieved guidance, and source-verification results in review output.
- Corrected the fine-tuning configuration to use `TaskType.CAUSAL_LM`.
- Corrected the published adapter's `adapter_config.json` from a null task type to `CAUSAL_LM` after a metadata-corrected real-model smoke test. Adapter weights were not modified.
- Corrected runtime chat formatting to match the system/user message structure used during fine-tuning.
- Added mocked CI tests plus a separately marked, opt-in real adapter smoke test.
- Documented CPU, CUDA, MPS, 4-bit, 8-bit, explicit download, offline, privacy, timeout, failure, and smoke-test operation.

## Verification

- Complete test suite: 57 passed, 1 opt-in real-model test skipped during ordinary local CI.
- Ruff: passed.
- Real published-adapter GPU smoke: statute normalization passed; regulation normalization passed; incomplete-case abstention passed; structured JSON passed.
- Unsupported factual addition: deterministic validator rejection passed.
- Correct PEFT relationship: `Qwen/Qwen3.5-0.8B` + LoRA adapter + `AutoProcessor` + `AutoModelForImageTextToText` + `CAUSAL_LM` verified through generation.

## Architectural decisions

1. The adapter and base model are loaded separately with PEFT instead of treating the adapter repository as a standalone model.
2. Offline-only loading is the default. Downloads require an explicit setup action or `--allow-model-download`.
3. The published adapter's older output shape remains accepted only through normalization into the stricter internal schema; all safety checks operate on the normalized object.
4. The model prompt preserves the message structure used during fine-tuning. The first metadata smoke exposed that a single flattened user prompt materially degraded structured output.
5. Model proposals cannot become a second correction authority. Exact deterministic agreement is required before the existing edit path can apply one.
6. Quantization support is isolated so lightweight and standard ML installations do not require `bitsandbytes`.

## Unresolved limitations

- The adapter was trained on a narrow synthetic citation-normalization corpus. It is not yet validated for broad malformed-citation interpretation, contextual short-form resolution, or explanation quality.
- The adapter emits the original schema rather than all newly added fields. Compatibility normalization supplies `abstain`, `antecedent_candidate`, and retrieved chunk IDs until a later evaluation justifies retraining.
- CPU, MPS, and quantized modes are implemented and documented but were not benchmarked in this phase.
- The current timeout stops awaiting generation but cannot forcibly terminate a Python inference thread already executing inside Transformers.
- Broader document structure, citation graphs, expanded rule families, retrieval, serious evaluation, packaging, desktop UI, skills, and final release hardening remain assigned to Prompts 2–10 and were intentionally not started.
