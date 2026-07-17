# Phase 9 — Skills and Host Integrations

## Status

Complete for generic local-skill packaging and officially configurable local stdio hosts.

## Exactly what changed

- Added general routing, court-filing, academic, short-form, source-verification, and explanation-review skills.
- Kept the local server as source of truth; no citation rules were duplicated.
- Added Claude Desktop and Codex stdio configuration examples.
- Added privacy, setup, troubleshooting, manual fallback, and uninstall guidance.
- Added adversarial prompt cases and automated guardrail/structure tests.

## Architectural decisions

- Skills are deliberately concise routing/process guards.
- Unsupported hosts receive documented CLI/desktop alternatives, not unofficial installation workarounds.
- External verification remains a distinct explicit-intent workflow.

## Unresolved

- Host-specific automatic skill installation varies and must be tested against each host's official current capability.
- Adversarial files validate required guidance statically; full host-model behavioral evaluation requires host test harnesses.
