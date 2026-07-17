# Source-Backed Citechecking

AutoCite v0.3 separates four different levels of confidence so formatting results are not mistaken for legal conclusions.

## 1. Deterministic

A deterministic finding is produced by code from the submitted text. Examples include citation extraction, exact character spans, known abbreviation normalization, section-symbol spacing, and an exact quotation string match.

## 2. Source verified

A source-verified finding means retrieved primary text directly contains the relevant metadata, quotation, or explicit page marker. It does not mean the authority is current, controlling, precedential, or supportive of the user's legal proposition.

## 3. Candidate evidence

AutoCite extracts the proposition before a case citation and ranks short passages from the retrieved opinion using bounded sentence windows rather than generated summaries. Two passage scorers are available; every ranked passage is stamped with the `scorer` value that actually produced its `combined_score`, so a reviewer never has to guess how a number was made.

**Lexical (default, always available).** Disclosed, deterministic lexical methods only:

- token-set overlap weighted at 65%;
- sequence similarity weighted at 35%.

No network access, no model download, and no nondeterminism. `scorer` is reported as `lexical`.

**Hybrid (optional, local-embedding).** Set `AUTOCITE_PASSAGE_SCORER=hybrid`, or construct `evidence.HybridPassageScorer`/pass one into `DeepReviewer(passage_scorer=...)`, to blend the same lexical score (50%) with cosine similarity (50%) from a local sentence-transformers bi-encoder (default `BAAI/bge-small-en-v1.5`, the same lazy-loaded, offline-only model default used by `retrieval.LocalEmbeddingRuleRetriever`). This adds a semantic signal lexical overlap alone cannot capture — e.g. a paraphrase with little token overlap. It requires the optional `retrieval` install extra (`sentence-transformers`) and a locally cached model; it never calls a network embedding API. `scorer` is reported as `hybrid_local_embedding`, and each passage also carries `embedding_similarity`.

**Fallback (mandatory, not silent).** If `sentence-transformers` is not installed, the model is not locally cached, or the embedding backend raises for any other reason, AutoCite never raises and never pretends the hybrid path ran. It falls back to the lexical score for every passage and reports `scorer` as `lexical_fallback_hybrid_unavailable`, with a `fallback_reason` on each passage explaining why. The top-level `provenance.proposition` field reflects whichever of these three outcomes actually happened.

In every case the resulting passage list is evidence for a lawyer, editor, or host model to review. It is not a conclusion that the case supports the proposition, and blending in an embedding similarity score does not change that: semantic similarity is still not legal support. Every proposition result therefore contains `requires_legal_judgment: true` and `conclusion: not_determined`.

## 4. Unresolved

A question remains unresolved when the citation is ambiguous, the source cannot be retrieved, the retrieved source lacks reliable page markers, a short form has no clear antecedent, or a local rule or publication manual controls.

## Quotation statuses

- `exact`: normalized whitespace still preserves an exact source substring.
- `normalized`: punctuation or Unicode normalization produces a direct match.
- `partial`: a similar candidate passage was found but the quotation is not verified.
- `absent`: no sufficiently similar passage was found in the retrieved source text.
- `not_supplied`: no nearby quotation was detected.

## Pincite statuses

- `confirmed_by_page_marker`: the retrieved text contains an explicit marker such as `*675`, `Page 675`, or `[675]`.
- `passage_found_page_unverified`: relevant-looking text was found, but the source lacks a reliable page marker.
- `unverifiable`: neither a reliable marker nor a sufficiently relevant candidate passage was located.
- `not_supplied`: the citation contains no pincite.

## Treatment and later citations

CourtListener may expose a count of later citations. AutoCite reports this only as contextual metadata and labels it `not_a_citator`—in plain terms, it is **not a citator**. A citation count does not distinguish positive, negative, neutral, or precedential treatment and is not Shepardizing, KeyCiting, or a substitute for a licensed citator.

## Source limitations

- CourtListener coverage and opinion text availability vary.
- Retrieved HTML may omit official pagination or contain only one opinion within a cluster.
- Statutes, regulations, journal articles, `Id.`, and `supra` are not validated by CourtListener's case citation lookup.
- A source can accurately contain quoted language while not supporting the broader proposition asserted by the writer.
- A source can support a proposition while being noncontrolling, superseded, vacated, or otherwise unsuitable.

## Required human or model review

The final reviewer must independently decide:

1. whether the authority actually supports the proposition;
2. whether the quotation is accurate in context;
3. whether the pincite identifies the relevant material;
4. whether the source is current and good law;
5. whether it is controlling or persuasive in the applicable jurisdiction;
6. whether signals, parentheticals, source order, and local rules are correct.
