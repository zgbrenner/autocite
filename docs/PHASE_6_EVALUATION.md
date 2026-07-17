# Phase 6 — Serious Evaluation Framework

## Status

Complete as a reproducible document-level framework and initial deterministic baseline. Qwen retraining is not justified by the measured failure taxonomy.

## Exactly what changed

- Added disjoint document-level train/development/test corpus with original CC0 examples and adversarial invention traps.
- Added all required quality, safety, abstention, retrieval, faithfulness, latency, memory, CPU, and GPU-status metrics.
- Added hard release gates for unsupported facts, non-citation prose, unsafe edits, antecedent guessing, local network activity, precision, and reproducibility.
- Added deterministic and retrieval ablation execution plus explicit unavailable statuses for Qwen, reranker, GPU, and GLiNER.
- Added reproducible corpus fingerprinting and split/feature/license validation.
- Added automatic failure taxonomy and a guarded retraining recommendation.
- Fixed no-citation review so unsupported test documents return a report instead of failing knowledge-pack selection.
- Added `autocite eval-system` with optional `--ablations`.

## Architectural decisions

- Documents, not citation transformations, are the split unit.
- Missing optional runtimes produce `not_run`, never synthetic metrics.
- Safety gates are independent of aggregate quality scores.
- Qwen retraining requires measured Qwen proposal failures; deterministic gaps cannot trigger it.

## Unresolved

- The initial corpus is too small for production claims and must grow with licensed/original examples.
- Qwen, reranker, GLiNER, and GPU ablations remain unmeasured in lightweight CI.
- Several deterministic classification, identity, and rule-family metrics are below desired release quality.
- Source-verification evaluation needs a separately authorized, reproducible fixture strategy.
