# Phase 7 — Polished Local MCP Product

## Status

Complete for local stdio, loopback HTTP, Python, CLI, and sidecar-ready operation.

## Exactly what changed

- Added versioned review and health schemas.
- Added MCP `health_check` with privacy, network, model, and offline-readiness disclosure.
- Enforced loopback-only HTTP binding; stdio remains default.
- Added lightweight, standard, GPU, and offline installation profiles with no automatic downloads.
- Added local model list/install/verify/remove lifecycle with SHA-256 manifests and confirmed removal.
- Added CLI health, install-plan, model management, rule-index, and diagnostic review workflows.
- Documented privacy, temporary-file behavior, local host configuration, offline installation, and troubleshooting.
- Verified deterministic review without models or network access.

## Architectural decisions

- The existing core package is the direct Python API; CLI, MCP, and future desktop UI call it.
- Model installation accepts local directories only. Acquisition is a separate deliberate setup action.
- HTTP cannot bind publicly in the packaged server.
- Deterministic readiness makes the product offline-ready even when optional models are absent.

## Unresolved

- Platform-native signed installers are Phase 8/10 release work.
- Hash manifests verify installed local copies; a signed upstream model allowlist is not yet published.
- Desktop sidecar lifecycle and first-run UI are Phase 8 work.
