# Privacy Guide

Review is local and in-memory by default. AutoCite has no telemetry and no document logging. The MCP server uses stdio or loopback only. Models and rule indexes load locally and are never silently downloaded during confidential review. Exports are written only where selected.

`verify_cases` or `deep_review` can send citation text to CourtListener only when explicitly enabled. Health output lists all network-capable components. Diagnostic logs must remain redacted. Model caches live in the configured local model directory and are removed only by explicit confirmed command.
