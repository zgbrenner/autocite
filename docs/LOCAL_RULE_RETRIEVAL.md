# Local Rule Retrieval

AutoCite retrieves approved, original Markdown summaries locally. Retrieval is not training, does not contact a service, and does not make legal conclusions.

## Inclusion and licensing

The built-in library lives under `src/autocite_mcp/reference_library`. Its manifest explicitly records inclusion, license, redistribution permission, rule family, Bluepages/Whitepages applicability, source type, jurisdiction, and revision date. A source is excluded unless it is marked included, redistributable, and has a nonproprietary license.

Markdown is split by headings. Each chunk gets a stable content-derived ID plus its source filename and heading. AutoCite does not package proprietary citation manuals.

## Triggering

Retrieval runs only for an explicit trigger: review-required findings, ambiguous antecedents, competing rule families, uncertain mode, uncommon source type, signal/parenthetical review, a user explanation request, model-declared missing context, or confidence below the configured threshold. Clean, high-confidence review skips retrieval.

## Ranking

The core installation uses deterministic lexical ranking after metadata filtering. Install `autocite-mcp[retrieval]` to use the optional local `BAAI/bge-small-en-v1.5` adapter. The optional reranker uses `cross-encoder/ms-marco-MiniLM-L6-v2` only to reorder already bounded rule or antecedent candidates.

Models load lazily and offline-only by default. Predownload them during setup. No model is silently downloaded while reviewing a document. Scores are ranking evidence only, never a finding about legal validity, support, treatment, or weight.

Build a reproducible JSON index:

```bash
autocite build-rule-index --output ~/.local/share/autocite/rules.json
```

For another approved directory, provide `--source-dir`; it must contain `manifest.json`.

## Qwen and GLiNER

When Qwen is enabled, it receives only bounded citation context, graph facts, deterministic findings, the selected local summaries, and permitted chunk IDs. A proposal claiming an unsupplied chunk ID is rejected by the deterministic validator.

GLiNER is an evaluation-only adapter behind `experimental-gliner`. It is disabled by default and should remain disabled unless measured evaluation demonstrates improvement on missed authors, titles, institutions, or uncommon source types without worse safety.
