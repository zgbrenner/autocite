# AutoCite Evaluation Report

## Dataset

The Phase 6 corpus contains 15 document-level examples split into four train, four development, and seven isolated test documents. Every row is original synthetic CC0 material. Splits share no document IDs. Feature tags cover court filings, memoranda, law-review notes, seminar papers, cases, statutes, regulations, constitutions, publications, internet and court documents, administrative and foreign/international/Tribal material, short forms, signals, parentheticals, quotations, pincites, incompleteness, and invention traps.

Corpus fingerprint: `1944553fdff5e250206045a849451b2ce0e71d84a25f9d0055a9dd504a9af218`.

## Deterministic test baseline

The seven-document test run passed all critical safety gates:

- safe-fix precision: 1.00;
- unsafe automatic edits: 0;
- unsupported factual introductions: 0;
- non-citation prose modifications: 0;
- unresolved antecedent guesses: 0;
- local-mode network calls: 0;
- explicit ambiguity abstention recall: 1.00.

Measured quality exposed known gaps rather than hiding them: source-type accuracy was 0.67, authority-identity accuracy was 0.86, issue-family precision was 0.33, and issue-family recall was 0.50. These are baseline signals from a small synthetic corpus, not production-quality estimates.

## Ablations

The framework defines deterministic-only, deterministic+Qwen, deterministic+retrieval, deterministic+Qwen+retrieval, deterministic+Qwen+retrieval+reranker, experimental GLiNER, and deterministic+hybrid-passage-scorer configurations. Dependency-free deterministic and retrieval paths run in ordinary CI. Qwen, reranker, GPU, GLiNER, and hybrid-passage-scorer rows are explicitly `not_run` unless their local runtimes are deliberately installed; the report never substitutes fabricated measurements.

The hybrid-passage-scorer arm measures `evidence.HybridPassageScorer` (candidate-passage ranking blended with local-embedding cosine similarity, selectable via `AUTOCITE_PASSAGE_SCORER=hybrid`) against the deterministic-only lexical passage ranker described in [`SOURCE_REVIEW.md`](SOURCE_REVIEW.md). It requires the optional `retrieval` install extra and a locally cached sentence-transformers model, so it is measured only when that runtime is deliberately installed; otherwise passage ranking transparently falls back to lexical scoring and is never reported as hybrid.

## Failure taxonomy and retraining decision

Current failures fall under deterministic source classification, authority identity, and incomplete rule coverage. They are not evidence of deficient Qwen proposal generation. The decision is therefore: **do not retrain Qwen yet**. Retraining may begin only after an isolated local-Qwen ablation demonstrates proposal-generation failures on a fully held-out test set.

## Limits

The corpus is intentionally small and synthetic. Performance timing varies by hardware. Reranker and GPU metrics remain unmeasured without optional local installations. CourtListener/source verification is excluded from local-only runs. AutoCite does not claim complete Bluebook compliance.
