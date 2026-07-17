# Phase 10 — Final Hardening and Release Review

## Status

Complete for the 0.5.0 alpha release audit. Open platform and optional-runtime items are explicitly nonblocking only for an alpha local release.

## Exactly what changed

- Bumped package and runtime version to 0.5.0 and refreshed the lockfile.
- Added architecture, trust/safety, model card, privacy, developer, release notes, and release-audit documents.
- Added CycloneDX SBOM generation, release checksums, and a reproducible audit workflow.
- Added tests for required documentation, SBOM coverage, and prohibited compliance overclaims.
- Re-ran the full suite, static checks, compile checks, both legacy evaluation gates, document-level safety gates, and package builds.

## Architectural decisions

- Alpha readiness is separate from production hardening.
- Unmeasured optional-runtime/platform journeys remain open rather than receiving synthetic pass results.
- Exact tested partial coverage is the only compliance claim.

## Unresolved

See `RELEASE_AUDIT.md`: platform signing/notarization/installers, real optional-model hardware matrices, accessibility audit, advanced desktop inspectors, and counsel-level redistribution review remain open.
