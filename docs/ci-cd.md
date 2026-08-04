# CI/CD policy

AutoCite uses separate validation and release lanes:

- `CI` runs Python compatibility tests across 3.10 through 3.13, while package, corpus, and training-pipeline checks run once on Python 3.12.
- `Desktop CI` validates frontend, browser, Rust, and sidecar behavior for pull requests that touch desktop code.
- `Dependency security` runs Python, JavaScript, Rust, and dependency-graph checks independently so one ecosystem cannot hide another ecosystem's result.
- `Desktop release` is reserved for updates to `main` and explicit manual dispatches. Pull requests validate desktop behavior without spending four-platform release minutes.

Workflows use concurrency cancellation for superseded validation runs, pinned tool versions where practical, short timeouts, and failure-only diagnostics. Release artifacts retain checksums, manifests, SBOMs, and platform provenance.
