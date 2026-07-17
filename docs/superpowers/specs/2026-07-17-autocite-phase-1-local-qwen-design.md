# AutoCite Phase 1: Safe Local Qwen Adapter Design

## Scope

Phase 1 integrates `foolish-bandit/AutoCite-0.8B` as an optional local proposal engine. It does not change document parsing, introduce retrieval, expand the rule engine, or retrain the adapter. Deterministic review remains fully usable without ML dependencies and remains the final authority for automatic edits.

## Architecture

The model boundary is a `CitationProposalModel` protocol with two implementations:

- `DisabledProposalModel` returns no proposals and loads no ML packages.
- `LocalQwenProposalModel` lazily loads the Qwen base model and AutoCite PEFT adapter only after model-enhanced review is requested.

`ModelRuntimeConfig` holds adapter, base model, local directory, device, quantization, offline, context, generation, timeout, and seed controls. Local files override Hub identifiers. Offline mode passes local-only loading flags and rejects configurations that would require a download.

The model receives one bounded citation task at a time and returns a strict `CitationProposal`. Model proposals are recorded separately from deterministic edits. A dependency-light validator verifies the schema, source span, rule profile, issue code, facts, deterministic conflicts, confidence, abstention state, and prohibited legal claims. Only validated, high-confidence, mechanical proposals that agree with the deterministic engine are eligible to become deterministic candidate edits; the model never mutates document text.

## Proposal Contract

Every proposal contains:

- document mode and source type;
- absolute start and end offsets;
- exact original citation text;
- known issue code;
- replacement text or `null`;
- facts relied upon and missing facts;
- optional antecedent candidate;
- confidence and explicit abstention state;
- explanation;
- retrieved rule-chunk identifiers.

The parser rejects extra ambiguity in field types, invalid enum values, inconsistent abstention/replacement combinations, malformed JSON, and unknown issue codes.

## Safety Model

The validator rejects proposals that:

- do not match the exact source span;
- introduce material facts not present in the citation or supplied deterministic components;
- conflict with deterministic findings or propose an unsupported issue family;
- change text outside the citation span or add non-citation prose;
- fall below the configured automatic-action confidence threshold;
- claim good-law status, controlling or precedential weight, or proposition support;
- cite retrieved chunks that were not provided to the task;
- attempt an automatic change while abstaining or reporting missing facts.

The review response keeps `deterministic_edits`, `remaining_deterministic_issues`, `model_proposals`, `retrieved_guidance`, and `source_verification` as distinct provenance-bearing fields.

## Adapter Metadata

The adapter is a LoRA adapter for `Qwen/Qwen3.5-0.8B`, loaded with `AutoProcessor` and `AutoModelForImageTextToText`. Because it performs autoregressive JSON generation, its PEFT task type is `CAUSAL_LM`. Phase 1 verified a corrected local configuration through real generation before publishing the metadata-only repair. Adapter weights were not modified.

## Testing

Ordinary CI uses fakes and import isolation so it never downloads model weights. Tests cover lazy loading, disabled operation, every validator rejection path, timeouts, offline flags, response separation, and deterministic-only installation. A separately marked real smoke test loads the published adapter and checks statute normalization, regulation normalization, incomplete-case abstention, valid JSON, and rejection of an unsupported factual addition.

## Operational Boundaries

The core install remains lightweight. The `slm` extra contains Torch, Transformers, PEFT, Accelerate, and Torchvision. Model downloads are explicit setup operations, never implicit confidential-document review operations. After approved files are present, offline-only review performs no network access.
