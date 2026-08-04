# Launch-site tests

- `home.spec.ts` verifies product positioning, primary conversion links, privacy proof, supported formats, and responsive navigation.
- `risk-scan.spec.ts` blocks and records post-load network APIs, verifies deterministic corrections, and confirms shared summaries contain no pasted document text.
- `routes.spec.ts` checks one H1, unique titles, descriptions, and absolute canonicals across core indexable routes.
- `claims.spec.ts` prevents unsupported accuracy, compliance, citator, endorsement, and legal-judgment claims.
- `src/lib/*.test.ts` verifies canonical metadata and the bounded scanner engine.
- `scripts/audit-seo.test.mjs` verifies that the static crawler catches missing metadata, invalid JSON-LD, noindex leakage, and broken internal links.
