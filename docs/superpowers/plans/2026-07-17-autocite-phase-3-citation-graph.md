# AutoCite Phase 3 Citation Graph Implementation Plan

1. Add graph dataclasses for authority nodes, occurrence nodes, typed edges, candidates, and resolution results.
2. Build conservative exact authority identities for all required source families.
3. Index full citations and bounded custom short-form patterns in document order.
4. Add structural edges for notes, clauses, citation sentences, predecessor and prior/later occurrences, signals, quotations, and parentheticals.
5. Implement deterministic `Id.`, case short form, statutory short form, `supra`, `supra note`, and hereinafter candidate generation and resolution.
6. Add all required valid, invalid, ambiguous, distant-note, and later-citation tests.
7. Expose the graph through review output and a focused MCP tool without breaking existing schemas.
8. Document exact coverage and unresolved limits, run the complete verification suite, publish, and merge Phase 3.
