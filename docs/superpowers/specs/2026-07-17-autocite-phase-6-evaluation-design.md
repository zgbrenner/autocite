# AutoCite Phase 6: Evaluation Framework Design

Evaluation splits at document level and uses only original synthetic or expressly licensed material. A schema records document mode, citation spans/types, authority identities, short-form resolution, ambiguity, issues, safe fixes, retrieval targets, adversarial invention traps, and feature tags.

The runner measures extraction, classification, identity, resolution, ambiguity, issue detection, automatic-edit safety, abstention, retrieval, reranking, explanation faithfulness, latency, memory, and device context separately. Release gates make invented facts, non-citation prose changes, unresolved antecedent guessing, network activity in local mode, and irreproducibility hard failures.

Ablations are explicit configurations, not marketing labels. Retraining is recommended only for measured Qwen proposal-generation defects, never structural parsing, rule logic, authority identity, retrieval, or product ambiguity.
