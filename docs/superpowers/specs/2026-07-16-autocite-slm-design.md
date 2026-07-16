# AutoCite SLM Design

## Goal

Add an optional, locally runnable citation-analysis model based on `Qwen/Qwen3.5-0.8B` to AutoCite without weakening AutoCite's deterministic safety boundaries. The model improves classification, context-sensitive issue detection, explanations, and repair proposals for both practitioner documents (Bluepages) and academic legal writing (Whitepages).

## Architecture

AutoCite remains a hybrid system. The existing `CitationEngine` extracts citations and applies high-confidence mechanical edits. The SLM receives bounded citation context, deterministic findings, mode, and source type, then returns a strict structured proposal. A validation gate accepts only schema-valid proposals whose cited span matches the source text and whose correction does not add unsupported citation facts. Rejected proposals remain review items and never alter the document.

The SLM is optional. If it is disabled, missing, times out, raises an error, or returns invalid output, AutoCite returns the ordinary deterministic result with an explicit fallback status.

## Components

### SLM contract

Each proposal contains:

- `citation_text`, `start`, and `end` identifying the exact source span;
- `source_type` and `mode`;
- `issue_code`, `explanation`, and `confidence`;
- `proposed_citation`, or `null` when facts are insufficient;
- `missing_facts` and `facts_used`.

The runtime accepts JSON objects only. Unknown keys are ignored, but required keys, types, span boundaries, mode values, confidence values, and source-text equality are validated.

### Runtime adapter

The core package defines a dependency-light protocol and hybrid orchestrator. The optional `slm` dependency group supplies Transformers, Torch, and Accelerate for development inference. The adapter loads `Qwen/Qwen3.5-0.8B` or a configured local path lazily and requests deterministic JSON output. A callable test adapter makes behavior testable without downloading model weights.

### Safety validator

The validator rejects proposals when:

- the span is outside the document or does not equal `citation_text`;
- the mode or source type conflicts with the request;
- output is malformed or confidence is unsupported;
- the proposal adds numbers, years, URLs, reporter tokens, section identifiers, party-name words, or other material citation facts absent from the original citation and supplied context;
- the model claims verification, good-law status, controlling weight, or proposition support.

Only proposals marked high confidence and passing validation may be applied. Overlapping proposals are resolved conservatively. All others are returned as suggestions for human review.

## Data flow

1. AutoCite detects Bluepages or Whitepages mode.
2. The deterministic engine analyzes and optionally fixes the document.
3. When SLM review is enabled, AutoCite creates bounded tasks from remaining issues and citation inventory.
4. The runtime returns structured proposals.
5. The validator accepts, rejects, or downgrades each proposal.
6. Accepted high-confidence edits are applied from right to left.
7. The deterministic engine re-analyzes the result.
8. The response includes deterministic edits, SLM proposals, rejected proposals, fallback status, and the final citation inventory.

## Training

Use supervised fine-tuning with LoRA on `Qwen/Qwen3.5-0.8B`. Training examples use conversational prompt-completion records and strict JSON completions. The dataset combines AutoCite's deterministic gold cases, template-generated transformations, adversarial hallucination cases, and human-reviewed examples for cases, statutes, regulations, constitutions, books, journals, internet sources, signals, short forms, quotations, and pincites.

Bluepages and Whitepages examples are balanced. At least twenty percent of examples require abstention or identify missing facts. Split groups by citation template before train/evaluation partitioning to reduce leakage. The public dataset and model card do not reproduce copyrighted Bluebook text.

Training uses TRL `SFTTrainer`, PEFT LoRA, Trackio, a fixed seed, evaluation during training, and Hub persistence. A separate export script merges the adapter and documents GGUF quantization for local deployment.

## Interfaces

CLI review commands gain:

- `--slm` to enable hybrid review;
- `--model-path` to select a Hub identifier or local model;
- `--slm-only` for evaluation and debugging, never as the default document-editing path.

MCP `review_document` and `review_uploaded_document` gain equivalent optional parameters. Existing calls remain compatible and do not download a model.

## Evaluation

Evaluation reports separate metrics for the base Qwen model, the fine-tuned model, the deterministic engine, and the hybrid system. Primary metrics are citation-span accuracy, issue classification macro F1, exact correction accuracy, valid-JSON rate, abstention precision/recall, hallucinated-fact rate, and unsafe-auto-apply rate. The release gate requires zero unsafe automatic edits on the safety set; other performance thresholds are reported rather than overstated.

## Scope

The first release supports English-language U.S. legal citations in text-based documents. It does not determine good-law status, controlling authority, proposition support, precedential weight, or compliance with every court's local rules or journal house style. CourtListener remains an optional and separately requested source-verification service.
