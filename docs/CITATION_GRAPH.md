# Citation Graph

AutoCite builds citation memory as ordinary, serializable data over `DocumentIR`. Qwen is not used to remember authorities or choose antecedents.

## Data model

The versioned graph contains:

- conservative authority nodes keyed by source-specific exact fields;
- an occurrence node for every recognized full citation and short form;
- structural and resolution edges with disclosed provenance;
- a resolution record for every `Id.`, short-case citation, statutory short form, `supra`, `supra note`, and `hereinafter` use.

Each occurrence retains absolute offsets, block-local offsets, note/page identity, document order, source type, and parsed components. Authority identity never merges sources merely because they are semantically similar. Incomplete identities remain separate when exact identifying fields are unavailable.

## Antecedent resolution

Resolution considers document order, source type, exact citation components, note identity, citation groups, intervening clauses, and whether the source family permits the form. A later full citation cannot make an earlier short form valid; it can only create a `later_consistency_match` edge for human review.

Every result states the resolved authority or `null`, method, candidate facts, confidence, disqualifying facts, rule profile, review requirement, and provenance. Ambiguity is an abstention. Eyecite extraction is evidence feeding the graph, not an unquestionable resolution decision.

## Public interfaces

`review_document` and `review_uploaded_document` include the complete graph under `citation_graph`. The direct Python API and local MCP server also expose `get_citation_graph` and `resolve_short_form`.

## Current boundaries

- Recognition breadth depends on the deterministic extractors; unrecognized prose references cannot yet become occurrence nodes.
- Identity is strongest for cases, statutes, regulations, journal articles, and URLs. Other source families use only exact parsed fields and may remain low-confidence or unknown.
- Signal, quotation, parenthetical, clause, sentence, note, prior/later, and hereinafter relationships are structural findings, not conclusions about legal support.
- No graph result establishes good-law status, precedential weight, controlling authority, or proposition support.
