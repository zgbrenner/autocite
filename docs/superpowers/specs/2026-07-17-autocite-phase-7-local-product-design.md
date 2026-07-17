# AutoCite Phase 7: Local Product Packaging Design

The MCP server remains local-first: stdio is default, HTTP is opt-in and loopback-only by default, and the same Python core powers CLI and direct API calls. Installation profiles declare dependencies and model expectations without silently downloading during review.

Model management uses explicit local directories, SHA-256 manifests, and deliberate install/remove commands. Privacy diagnostics disclose every network-capable component, telemetry/logging defaults, temporary-file policy, and offline readiness. Tool schemas are versioned.
