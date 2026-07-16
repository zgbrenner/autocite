# AutoCite Local SLM

AutoCite can optionally use a citation-specialized small language model based on `Qwen/Qwen3.5-0.8B`. The model supplements the deterministic engine; it does not replace it.

## What the model does

The SLM receives one bounded citation task at a time. It identifies the source type and issue, explains the formatting concern, proposes a correction when the required facts are already present, or abstains and lists missing facts. Its output must be a strict JSON object.

AutoCite then validates the output. A proposal is rejected if its citation span does not match the source document, its mode or source type conflicts with the task, it adds material facts, or it claims good-law status, controlling authority, or proposition support. Only an explicitly enabled, high-confidence proposal that passes validation can alter text.

## Install and run

```bash
uv sync --extra slm
uv run autocite review-file memorandum.docx --slm
```

Use a local or alternate Hub model:

```bash
uv run autocite review-file memorandum.docx \
  --slm \
  --model-path /models/autocite-0.8b
```

Applying SLM edits is a separate opt-in:

```bash
uv run autocite review-file memorandum.docx --slm --apply-slm-fixes
```

`--slm-only` skips deterministic edits but still uses deterministic citation extraction to create bounded model tasks. It exists for evaluation and debugging, not as the recommended document-review mode.

## Failure behavior

If the model is absent, cannot load, raises an exception, returns malformed JSON, or proposes an unsafe edit, AutoCite preserves the deterministic result. The `slm_review` object reports `completed`, `partial`, `fallback`, `no_citations`, or `not_requested` and includes rejected-proposal reasons.

## Privacy

Local Transformers inference does not send document text to an inference API. Model files may be downloaded from the configured Hub location on first use. CourtListener access is separate and occurs only when case verification or deep review is explicitly requested.

## Build the training dataset

```bash
uv run python training/build_dataset.py \
  --seeds training/seed_examples.jsonl \
  --output training/autocite_slm.jsonl
```

The generator produces balanced Bluepages and Whitepages prompt-completion records, keeps citation-template groups within one split, and includes abstention examples. The dataset contains synthetic or original transformations rather than excerpts from the citation manual.

## Fine-tune

The training script uses TRL supervised fine-tuning, PEFT LoRA, Trackio, a fixed seed, validation during training, and Hub persistence.

```bash
HF_TOKEN=... \
AUTOCITE_HUB_MODEL=your-account/AutoCite-0.8B \
uv run training/train_sft.py
```

Hugging Face Jobs can run the same PEP 723 script on a GPU. Training output must be pushed to the Hub because job storage is temporary.

## Evaluate

Run the dependency-light validation safety gate:

```bash
uv run python training/evaluate_slm.py --safety-file evals/slm_safety.jsonl
```

The full model evaluation reports valid-JSON rate, citation-span accuracy, issue classification macro F1, exact correction accuracy, abstention precision and recall, hallucinated-fact rate, and unsafe-auto-apply rate. A release must have zero unsafe automatic acceptances on the safety set.

## Limits

The first release focuses on English-language U.S. legal citations. AutoCite does not determine good-law status, controlling authority, precedential weight, proposition support, or compliance with every local rule or journal house style. Source verification and professional review remain necessary.
