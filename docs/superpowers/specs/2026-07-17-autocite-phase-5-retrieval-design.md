# AutoCite Phase 5: Local Rule Retrieval Design

Phase 5 treats approved Markdown as a local, licensed reference library, not training data. An explicit manifest controls inclusion. Stable heading-scoped chunks retain filename, heading, rule family, mode, source type, jurisdiction, revision, license, and redistribution metadata.

Metadata filtering happens before ranking. The lightweight installation uses deterministic lexical ranking. Optional local embeddings and a cross-encoder implement dependency-isolated protocols and remain offline-capable after installation. Scores rank context only and never become legal conclusions.

Retrieval runs on explicit triggers such as review-required findings, ambiguity, uncommon source type, uncertain mode, user explanation requests, or low confidence. Clean citations do not retrieve context. Qwen receives only bounded citation context, graph facts, deterministic findings, approved chunk summaries and IDs, and the existing strict schema. Validation remains final.
