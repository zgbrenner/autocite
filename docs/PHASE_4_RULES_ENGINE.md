# Phase 4 — Expanded Deterministic Rules Engine

## Status

Complete for the explicitly published partial coverage. AutoCite does not claim full Bluebook compliance.

## Exactly what changed

- Added immutable declared rule specifications and provenance-bearing findings.
- Added contextual families for `Id.`, case/statutory short forms, `supra`, `supra note`, `hereinafter`, signals, parentheticals, citation-group separators, pincites, quotations, and Whitepages internet-archive review.
- Added separate source-family coverage modules for cases, statutes, regulations, constitutions, administrative materials, books, journals, news, court documents, internet sources, archival sources, foreign/international/Tribal sources, and AI-generated materials.
- Added `safe_auto_fix`, `suggested_fix`, `review_required`, and `unsupported` levels; the edit engine now explicitly requires `safe_auto_fix`.
- Added contextual findings and correction-level counts to document review.
- Added a versionable machine-readable coverage matrix and local MCP coverage tool.
- Added mode-difference, ambiguity, quotation-pincite, signal, metadata-contract, and coverage tests.

## Architectural decisions

- Authority resolution stays in the citation graph; rules consume its results.
- Existing mechanical formatter fixes remain compatible but are now explicitly gated by correction level.
- Exact structural/textual checks may emit findings; substantive signal selection and parenthetical accuracy remain human/model review.
- Bluepages and Whitepages applicability are separate flags on every rule.
- Unsupported families are visible rather than implicitly treated as passing.

## Unresolved

- Coverage is partial for every implemented source family and explicitly unsupported for several uncommon families.
- Citation typography cannot be fully validated from plain text when italics or small caps are absent from the input representation.
- Substantive ordering, signal fit, explanatory accuracy, legal support, and source validity still require source or human review.
- Local rule retrieval is Phase 5 work.
