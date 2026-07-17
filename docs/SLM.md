# AutoCite Local SLM

AutoCite can optionally use a citation-specialized small language model based on `Qwen/Qwen3.5-0.8B`. The model supplements the deterministic engine; it does not replace it.

The published LoRA adapter is [`foolish-bandit/AutoCite-0.8B`](https://huggingface.co/foolish-bandit/AutoCite-0.8B), which AutoCite uses by default when `--slm` is enabled.

## What the model does

The SLM receives one bounded citation task at a time. It identifies the source type and issue, explains the formatting concern, proposes a correction when the required facts are already present, or abstains and lists missing facts. Its output must be a strict JSON object.

AutoCite then validates the output. A proposal is rejected if its citation span does not match the source document, its mode or source type conflicts with the task, its issue code is unknown, it conflicts with deterministic findings, it adds material facts, it changes non-citation prose, it relies on an unattributed rule chunk, or it claims good-law status, controlling authority, precedential value, or proposition support.

The model never directly changes a document. Even when model-assisted application is explicitly enabled, a high-confidence proposal is eligible only if it exactly matches a high-confidence deterministic autofix for the same span and issue. Results keep deterministic edits, remaining deterministic issues, model proposals, retrieved guidance, and source-verification results in separate fields.

## Install and run

Install ML support, then explicitly download the two approved repositories into a self-contained directory:

```bash
uv sync --extra slm
uvx --from huggingface_hub hf download Qwen/Qwen3.5-0.8B \
  --local-dir models/autocite/base
uvx --from huggingface_hub hf download foolish-bandit/AutoCite-0.8B \
  --local-dir models/autocite/adapter
```

Review offline on CPU:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run autocite review-file memorandum.docx \
  --slm --local-model-directory models/autocite --model-device cpu
```

For a CUDA GPU, use `--model-device cuda`. `--model-device auto` lets Accelerate choose available hardware. Apple Silicon can use `--model-device mps`; 4-bit and 8-bit modes are not enabled on MPS.

For CUDA quantization, install both optional groups and select the mode explicitly:

```bash
uv sync --extra slm --extra slm-quantized
uv run autocite review-file memorandum.docx \
  --slm --local-model-directory models/autocite \
  --model-device cuda --model-quantization 4bit
```

Quantized loading requires `bitsandbytes` and a compatible CUDA environment. If memory is insufficient, use a shorter `--model-max-context-length`, use 4-bit mode, or fall back to deterministic-only review.

Use a local or alternate Hub model:

```bash
uv run autocite review-file memorandum.docx \
  --slm \
  --model-path foolish-bandit/AutoCite-0.8B
```

Hub downloads remain disabled unless `--allow-model-download` is passed. That flag is intended for setup, not for reviewing confidential material. Runtime controls also include `--base-model-id`, `--model-max-context-length`, `--model-max-generated-tokens`, `--model-timeout-seconds`, and `--model-seed`. Equivalent versioned arguments are exposed by `review_document` and `review_uploaded_document`, including `use_local_model` as the preferred name and `use_slm` as a compatibility alias.

Applying SLM edits is a separate opt-in:

```bash
uv run autocite review-file memorandum.docx --slm --apply-slm-fixes
```

`--slm-only` skips deterministic edits but still uses deterministic citation extraction to create bounded model tasks. It exists for evaluation and debugging, not as the recommended document-review mode.

## Failure behavior

If the model is absent, cannot load, times out, raises an exception, returns malformed JSON, or proposes an unsafe edit, AutoCite preserves the deterministic result. The `slm_review` object reports `completed`, `partial`, `fallback`, `no_citations`, or `not_requested` and includes rejected-proposal reasons. A disabled or failed model does not prevent deterministic-only operation.

## Privacy

Local Transformers inference does not send document text, citation text, metadata, embeddings, or prompts to an inference API. Offline-only model loading is the default. No model is silently downloaded while reviewing a document. CourtListener access is separate and occurs only when case verification or deep review is explicitly requested; its results are labeled separately from formatting and model inference.

After the `models/autocite/base` and `models/autocite/adapter` directories exist, disconnect the network and keep `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` set for an enforceable offline run.

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

Ordinary CI uses mocks and does not download the real adapter. To run the opt-in real smoke test against already cached model files:

```bash
AUTOCITE_REAL_MODEL=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run pytest -m real_model tests/test_real_adapter_smoke.py
```

The smoke test checks statute normalization, regulation normalization, abstention when case facts are missing, valid structured JSON, and rejection of an unsupported factual addition.

The full model evaluation reports valid-JSON rate, citation-span accuracy, issue classification macro F1, exact correction accuracy, abstention precision and recall, hallucinated-fact rate, and unsafe-auto-apply rate. A release must have zero unsafe automatic acceptances on the safety set.

## Limits

The first release focuses on English-language U.S. legal citations. AutoCite does not determine good-law status, controlling authority, precedential weight, proposition support, or compliance with every local rule or journal house style. Source verification and professional review remain necessary.
