# Developer Guide

Use Python 3.10+ and `uv sync --extra dev`. Run `pytest`, `ruff check .`, both evaluation commands, `uv build`, and `scripts/generate_sbom.py` before release. Keep core dependencies lightweight; optional ML, retrieval, desktop, and build dependencies stay in extras.

New rules require declared `RuleSpec` metadata, mode separation, positive/negative/ambiguous tests, correction level, provenance, and coverage update. New model behavior requires held-out evaluation and cannot weaken deterministic validation. Never add proprietary manual text.

## MCP tool output schemas

Every `@mcp.tool` in `src/autocite_mcp/server.py` is annotated with a return type from `src/autocite_mcp/output_models.py` instead of `dict[str, Any]`. FastMCP (`mcp.server.fastmcp.utilities.func_metadata`) uses a `BaseModel` return annotation directly as the tool's output model: it validates the dict the tool function returns (`output_model.model_validate(result)`) and serializes that as `structuredContent`, and derives a real JSON `outputSchema` from the model instead of the near-empty `{"type": "object", "additionalProperties": true}` schema a bare `dict[str, Any]` annotation produces. Tool functions still build and return plain dicts — only the annotation changes — so the unstructured text content every existing client already parses is byte-for-byte unaffected.

When adding a tool or changing a tool's return shape:

- Add or update the corresponding model in `output_models.py`. Model stable, first-party fields precisely; keep genuinely open-ended or externally-owned sub-payloads (e.g. per-source-type citation `components`, retrieval chunk internals, deep-review internals) as `dict[str, Any]` / `list[dict[str, Any]]` rather than over-constraining them.
- If a function's payload shape genuinely varies at runtime based on an argument (see `CheckCitationsResult`, which covers both `CitationEngine.analyze` and `CitationEngine.fix` shapes), make the varying fields `Optional` on one combined model rather than forcing a single rigid shape.
- Run `pytest tests/test_server.py tests/test_output_models.py` — the former asserts every tool declares a non-trivial `outputSchema` and spot-checks `structuredContent` via the MCP client layer; the latter validates models directly against `tools.py` output.
