# AutoCite Phase 4: Composable Deterministic Rules Design

## Scope

Phase 4 adds declared rule-family specifications and contextual evaluation over `DocumentIR` and the citation graph. Parsing, authority resolution, evaluation, correction generation, validation, and explanation remain separate. Existing mechanical fixes stay compatible and are labeled `safe_auto_fix`; contextual rules abstain whenever required facts or legal judgment are missing.

## Architecture

`RuleSpec` is immutable metadata declaring code, mode applicability, source types, context and facts, deterministic condition summary, severity, correction permission, confidence, original summary, general rule-family reference, explanation template, and test cases. Family evaluators emit `RuleFinding` records with provenance and one of four correction levels.

The contextual engine consumes `DocumentIR` and `CitationGraph`. It never edits text. The existing formatter remains the correction generator for established mechanical fixes. The graph remains the authority-resolution source of truth.

## Safety

Only `safe_auto_fix` can reach the automatic edit path. Signal choice, explanatory accuracy, source support, legal weight, and good-law questions always require review or remain unsupported. Coverage is reported machine-readably without claiming complete Bluebook compliance.
