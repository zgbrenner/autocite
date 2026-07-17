# Phase 5 — Local Markdown Rule Retrieval

## Status

Complete for the approved original reference library and optional local ranking interfaces.

## Exactly what changed

- Added manifest-gated Markdown ingestion with licensing and redistribution checks.
- Added stable heading-scoped chunks with complete source and rule metadata.
- Added deterministic metadata-first lexical retrieval and reproducible JSON index save/load.
- Added lazy offline-only BGE embedding and cross-encoder reranker adapters as optional dependencies.
- Added explicit retrieval triggers so clean citations do not retrieve context.
- Added exact chunk attribution to review and a focused `get_rule_context` MCP/Python tool.
- Added bounded local chunks and permitted IDs to Qwen prompts; claimed unsupplied IDs are rejected.
- Added a disabled-by-default experimental GLiNER adapter.
- Added ingestion, exclusion, filtering, trigger, attribution, index, review, prompt, and disabled-path tests.

## Architectural decisions

- Original rule summaries are package data; proprietary manuals are not included.
- Metadata filtering precedes every ranking backend.
- The dependency-free lexical retriever is the default and keeps lightweight installation local.
- Embeddings and reranking are replaceable interfaces and do not decide rules or antecedents.
- Retrieval scores are never surfaced as legal conclusions.

## Unresolved

- The built-in original reference library is intentionally small and not a substitute for a licensed citation manual.
- Optional embedding/reranker quality will be measured in Phase 6 before either becomes a recommended default.
- The GLiNER path remains experimental and disabled pending evaluation.
- Qwen has not been retrained; Phase 6 must first identify specific proposal-generation failure classes.
