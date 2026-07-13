# AutoCite Easy-Connect and LLM Knowledge Design

## Goal

Make AutoCite usable without requiring a user or host model to understand its internal tool set, while supporting local Claude Desktop and remote Claude/ChatGPT connections.

## Primary workflow

`review_document` is the canonical entry point. It detects Bluepages or Whitepages mode, analyzes the document, applies only deterministic fixes, rechecks the result, optionally verifies case citations, and returns a compact knowledge pack plus a strict response contract.

## Knowledge delivery

The server supplies original summaries rather than copyrighted rule text. The knowledge pack includes core guardrails, cross-cutting citation principles, mode-specific priorities, source templates, required facts, checks, and the relevant Bluepages or Whitepages rule family.

## Client experience

- Claude Desktop: `autocite setup-claude` safely updates the configuration and preserves existing servers.
- ChatGPT: Streamable HTTP at `/mcp`, with OpenAI Secure MCP Tunnel recommended for private documents.
- Claude web: the same HTTPS `/mcp` endpoint can be added as a custom connector.
- Container hosting: Docker, `/health`, and a Render Blueprint provide a direct deployment path.

## Safety and privacy

No missing citation facts are invented. “Complete” is always scoped to detected citation-format issues. Public no-auth hosting is documented as unsuitable for confidential legal text; local execution or a private tunnel is the default recommendation.
