# Developer Guide

Use Python 3.10+ and `uv sync --extra dev`. Run `pytest`, `ruff check .`, both evaluation commands, `uv build`, and `scripts/generate_sbom.py` before release. Keep core dependencies lightweight; optional ML, retrieval, desktop, and build dependencies stay in extras.

New rules require declared `RuleSpec` metadata, mode separation, positive/negative/ambiguous tests, correction level, provenance, and coverage update. New model behavior requires held-out evaluation and cannot weaken deterministic validation. Never add proprietary manual text.
