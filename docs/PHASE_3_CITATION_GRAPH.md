# Phase 3 — Document-Wide Citation Graph

## Status

Complete. AutoCite now represents citation memory as deterministic, inspectable document state and abstains when short-form antecedents remain ambiguous.

## Exactly what changed

- Added versioned authority, occurrence, edge, candidate, and resolution schemas.
- Added conservative source-specific identity keys and repeated-occurrence indexing.
- Added document-order-aware handling for `Id.`, short cases, statutory short forms, `supra`, `supra note`, and `hereinafter`.
- Added structural edges for citation groups, sentences, footnotes, immediate/prior/later occurrences, signals, quotations, parentheticals, definitions, and later consistency review.
- Added citation graphs to ordinary and uploaded document reviews.
- Added direct Python and MCP tools for graph inspection and short-form resolution.
- Added tests for all Phase 3 completion scenarios, including multi-authority notes and the prohibition on retroactive validation.

## Architectural decisions

- Graph construction is local deterministic logic over `DocumentIR`; no model state is involved.
- Authorities merge only on conservative exact identity fields, never semantic similarity.
- Candidate scores expose exact features but do not override legal ambiguity.
- Note content is ordered at its body marker when that relationship is known.
- Later citations are consistency evidence only.

## Unresolved

- Deterministic extraction does not yet recognize every requested source family with equal depth; incomplete and unfamiliar sources remain distinct low-confidence identities.
- The graph identifies structural signal, quotation, and parenthetical relationships but does not judge substantive fit or proposition support.
- Expanded rule-family evaluation and correction levels are Phase 4 work.
