# AutoCite-0.8B Integration Model Card

AutoCite optionally uses `foolish-bandit/AutoCite-0.8B`, a PEFT causal-language-model adapter for `Qwen/Qwen3.5-0.8B`. It proposes JSON interpretations, corrections from existing facts, classifications, and explanations. It is not an editor, authority resolver, citator, or source verifier.

Inputs are bounded citation context, deterministic findings, graph facts, and permitted local rule chunks. Outputs pass strict schema, span, fact, issue-code, profile, confidence, legal-claim, and deterministic-conflict validation. Low confidence or missing facts abstain.

Phase 6 did not justify retraining. Real-model smoke testing remains opt-in because the weights are not downloaded in CI. Applicable upstream model/adapter licenses must be reviewed before redistribution.
