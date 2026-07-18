# AutoCite Evaluation Report

## Dataset

The corpus contains 71 document-level examples: 21 train, 18 development, and 32 isolated test documents (up from 15/4/4/7 in the Phase 6 baseline). Every row is original synthetic CC0 material and splits share no document IDs. Composition:

- Every one of the engine's nine issue families appears as an expected finding in at least four documents, including the previously uncovered `citation groups and ordering`, `parentheticals`, and `short forms: statutes and regulations`.
- Every extractable source type appears in gold citations at least six times (case 37, short form 23, statute 16, journal article 11, regulation 10, internet 8, constitution 6).
- 24 clean documents carry an empty expected-family list and zero ambiguous short forms; they measure false-positive behavior directly.
- 11 documents pair malformed citations with exact expected `safe_fixed_text`; 20+ documents contain genuinely ambiguous short forms with gold ambiguity counts.
- Registers include captioned court briefs, footnoted law-review apparatus, memoranda, and seminar papers, with several 500+ word multi-citation documents.

Gold labels are explicit: each document declares `expected_issue_families`, validated at load time against the taxonomy derived from `RULE_SPECS`, so corpus labels can never silently drift from the family names the engine emits. All case names, reporters' volume/page combinations, authors, and journals are synthetic; volumes for fictional federal-reporter citations are deliberately outside each reporter's real range so no gold citation collides with a published decision.

Corpus fingerprint: `625dd7c6be3633f5c3730790569175b4688ffa6ce9a979ae42ee83a11068f098`.

### Label integrity process

The corpus was authored against the rule definitions, then independently audited by an adversarial review pass that re-derived labels from `RULE_SPECS` and the Indigo Book rather than from engine output. That audit caught, and this corpus revision corrected: an engine over-restriction that had been copied into three documents' gold labels (textbook-valid `Id.` after intervening prose labeled ambiguous — the engine has since been corrected to Indigo R15.3 semantics, and the labels to match the rule, not the old engine), real reporter volume/page combinations reused under fictional case names, and one stale feature tag.

## Deterministic baseline (all splits)

The deterministic-only arm on the expanded corpus measures, for train, dev, and test alike:

- citation span precision/recall/F1: 1.00;
- source-type accuracy: 1.00 (0.67 on the old 7-document split, which was a gold-label artifact);
- authority-identity accuracy: 1.00 (was 0.86, same cause);
- issue-family precision/recall: 1.00/1.00 (was 0.33/0.50 — the old corpus expected a `short forms` family no rule ever emits);
- safe-fix precision: 1.00; unsafe automatic edits: 0; unsupported factual introductions: 0; non-citation prose modifications: 0; unresolved antecedent guesses: 0; local-mode network calls: 0;
- explicit ambiguity abstention precision/recall: 1.00;
- all release gates pass on every split.

Two engine defects the corpus exposed were fixed rather than papered over: eyecite's truncation of law citations at digit-letter subsection fusions (`17 C.F.R. § 240.10b-5` previously extracted as `§ 240`), and markdown-footnote documents never receiving note numbers, which made `supra note N` resolution structurally unreachable in the production parsing path. The unsupported-fact metric itself was also corrected: pure formatting fixes (`42 USC` → `42 U.S.C.`) no longer count as introducing material content.

Perfect scores on a synthetic corpus are a statement about this corpus, not about production documents: the corpus is adversarial in labeled ambiguity and malformedness but cannot represent the full variety of real filings. The next step change in evaluation quality requires licensed real-world documents, not more synthetic rows.

## Known gaps the corpus documents but cannot score

- Book, court-document, administrative, foreign/international/Tribal, and AI-material citations have no extraction support; documents containing them are scored only as clean-document probes. The `book` coverage stated for the pincite rules is therefore unexercised.
- Bare `Author, supra` in footnoted academic documents (Indigo R6.2.3 reserves it for non-footnoted work) is not flagged by any rule; the corpus uses the pattern only where resolution semantics, not formatting, are under test.

## Ablations

The framework defines deterministic-only, deterministic+Qwen, deterministic+retrieval, deterministic+Qwen+retrieval, deterministic+Qwen+retrieval+reranker, experimental GLiNER, and deterministic+hybrid-passage-scorer configurations. Dependency-free deterministic and retrieval paths run in ordinary CI. Qwen, reranker, GPU, GLiNER, and hybrid-passage-scorer rows are explicitly `not_run` unless their local runtimes are deliberately installed; the report never substitutes fabricated measurements.

The hybrid-passage-scorer arm measures `evidence.HybridPassageScorer` (candidate-passage ranking blended with local-embedding cosine similarity, selectable via `AUTOCITE_PASSAGE_SCORER=hybrid`) against the deterministic-only lexical passage ranker described in [`SOURCE_REVIEW.md`](SOURCE_REVIEW.md). It requires the optional `retrieval` install extra and a locally cached sentence-transformers model, so it is measured only when that runtime is deliberately installed; otherwise passage ranking transparently falls back to lexical scoring and is never reported as hybrid.

## Failure taxonomy and retraining decision

The previously reported deterministic failures (source classification, authority identity, issue-family scoring) traced to gold-label defects and two extraction bugs, all now corrected. No measured failure implicates Qwen proposal generation. The decision remains: **do not retrain Qwen**. Retraining may begin only after an isolated local-Qwen ablation demonstrates proposal-generation failures on a fully held-out test set.

## Limits

The corpus is synthetic; perfect metrics bound only what the corpus tests. Performance timing varies by hardware. Reranker and GPU metrics remain unmeasured without optional local installations. CourtListener/source verification is excluded from local-only runs. AutoCite does not claim complete Bluebook compliance.
