# Deterministic Rules Engine

AutoCite evaluates contextual citation rules over `DocumentIR` and the document-wide citation graph. Models cannot apply these rules or edit a document.

Each `RuleSpec` declares its issue code, Bluepages/Whitepages applicability, source types, required context and facts, exact deterministic conditions, severity, correction permission, confidence, original summary, general rule-family reference, explanation template, and named tests. Parsing, authority resolution, evaluation, correction generation, correction validation, and explanation remain separate stages.

Findings use four correction levels:

- `safe_auto_fix`: a high-confidence mechanical change may be applied;
- `suggested_fix`: a mechanically plausible change requires approval;
- `review_required`: facts, ambiguity, source checking, or legal judgment block correction;
- `unsupported`: AutoCite does not implement the rule.

Only `safe_auto_fix` enters the automatic edit path. Signal choice, explanatory-parenthetical accuracy, source support, legal weight, and good-law status are never inferred from formatting.

The machine-readable coverage endpoint/tool is `get_rule_coverage`. The packaged snapshot is [`RULE_COVERAGE.json`](RULE_COVERAGE.json). Every partial entry means a tested subset, not complete Bluebook compliance.
