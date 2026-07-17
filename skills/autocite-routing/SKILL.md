---
name: autocite-routing
description: Use when a user asks to check, correct, explain, or verify legal citations in text or an uploaded document.
---

# AutoCite routing

1. Call local `review_document` or `review_uploaded_document` before correcting citations from memory.
2. Preserve non-citation prose and use the explicit or detected Bluepages/Whitepages mode.
3. Present `deterministic_edits`, `model_proposals`, `retrieved_guidance`, and `source_verification_results` separately.
4. Apply only deterministic `safe_auto_fix` changes automatically. Ask before nonmechanical changes.
5. Show ambiguities, missing facts, abstentions, and the local chunk IDs used in explanations.
6. Never invent source facts or claim formatting proves good-law status, controlling weight, precedential value, or proposition support.
7. Respect offline settings. Warn and obtain explicit intent before external verification.
