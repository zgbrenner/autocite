# AutoCite Usability Implementation Plan

**Goal:** Add a model-friendly primary workflow, richer legal-citation knowledge, one-command Claude setup, and remote MCP deployment support.

**Architecture:** Preserve the deterministic citation engine. Add a knowledge module and orchestration tool above it, expose those through FastMCP, and package local and hosted connection paths without bundling third-party reference files.

**Tech Stack:** Python 3.10+, MCP Python SDK, eyecite, httpx, Starlette, Docker.

## Completed tasks

- [x] Add tests for automatic mode selection and source-specific knowledge.
- [x] Implement `knowledge.py` with mode, source, rule-family, and cross-cutting guidance.
- [x] Add `review_document` and `get_citation_guidance`.
- [x] Improve MCP instructions, annotations, resources, and prompts.
- [x] Add a safe Claude Desktop configuration installer.
- [x] Fix title-case `Id` normalization discovered by the new workflow tests.
- [x] Add Streamable HTTP host/port configuration and `/health`.
- [x] Add Docker and Render deployment files.
- [x] Write local Claude, ChatGPT tunnel, and remote Claude connection documentation.
- [x] Run the full verification suite and inspect the built wheel.
- [ ] Publish the branch, pass CI, and merge the release PR.
