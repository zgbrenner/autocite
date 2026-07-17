# AutoCite Phase 3: Document-Wide Citation Graph Design

## Scope

Phase 3 builds citation memory as deterministic, inspectable data over `DocumentIR`. It creates conservative authority identities, occurrence nodes, structural relationships, and short-form resolution results. It does not delegate memory or antecedent selection to Qwen.

## Graph model

Authority nodes represent cases, statutes, regulations, constitutions, articles, books, court documents, administrative materials, internet sources, archival sources, foreign/international/Tribal sources, AI materials, and incomplete unknown sources. Identity keys use exact available citation facts and never semantic similarity.

Occurrence nodes represent every full citation and short form. Edges capture authority citation, short-form resolution, prior/later occurrences, immediate predecessor, same clause, same citation sentence, same note, note references, hereinafter aliases, quotations, parentheticals, and signals.

## Resolution

Resolution processes occurrences in document order. Later citations never validate an earlier short form. Deterministic candidate generation filters prior authorities by source type, exact citation components, structural context, document order, and rule profile. Scoring uses disclosed exact features. A unique, clearly supported candidate can resolve; close or legally ambiguous candidates remain unresolved and require review.

`Id.` handling distinguishes the previous occurrence, previous authority, previous citation group, intervening citation material, and multi-authority groups. `supra note` resolves through the referenced note only when it contains exactly one permitted authority. Cases and statutes cannot use `supra`. Short-case and statutory forms use separate identity and candidate rules.

## Output

Every short form returns a resolved authority or null, resolution method, complete plausible candidate list, confidence, disqualifying facts, rule profile, and human-review requirement. All conclusions identify deterministic or unresolved provenance.
