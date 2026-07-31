# AutoCite Continuous Release Pipeline

AutoCite publishes a fresh cross-platform GitHub release for every commit merged into `main`. A release is created only after the repository's deterministic, application, editor, native-shell, and packaged-sidecar checks pass inside the release workflow.

## Pull-request gates

The `Quality` workflow runs on every pull request and on `main`:

- Python 3.10, 3.11, 3.12, and 3.13 test matrix.
- Ruff linting and Python bytecode compilation.
- Full pytest suite and deterministic gold evaluation.
- Wheel and source-distribution build with package-content inspection.
- React and TypeScript typechecking, ESLint, Vitest, production build, and high-severity npm audit.
- Rust formatting, Clippy with warnings denied, and Cargo tests.
- Focused canonical application and MCP contract tests.
- PyInstaller sidecar build plus authenticated and unauthenticated loopback smoke tests.
- Integrated Linux Tauri bundle build.

The `Security` workflow adds:

- GitHub dependency review on pull requests.
- CodeQL extended security and quality queries for Python and JavaScript or TypeScript.
- Python and Rust advisory audits.
- Full-history secret scanning.
- Weekly scheduled security runs.

Dependabot maintains Python, npm, Cargo, and GitHub Actions dependencies in grouped pull requests.

## Release builds

`Continuous Desktop Release` runs after every update to `main` and can also be started manually. It performs its own release validation before building:

| Platform | Architecture | Release formats |
|---|---:|---|
| Windows | x86-64 | NSIS installer, MSI installer, portable ZIP |
| macOS | Apple Silicon | DMG |
| macOS | Intel | DMG |
| Linux | x86-64 | AppImage, Debian package |
| Python | platform independent | wheel and source distribution |

Each matrix runner builds the Python sidecar locally with PyInstaller under Tauri's required target-triple filename. The workflow starts that exact frozen executable, verifies `/health`, confirms that `/sessions` rejects an unauthenticated request, and confirms that the same endpoint succeeds with the launch token before compiling the desktop bundle.

## Release identity

Continuous builds use immutable tags in this format:

```text
v0.7.0-build.<workflow-run>.<attempt>
```

The workflow marks each successful release as the latest release. Re-running a failed attempt creates a new tag rather than mutating a previously published successful build.

## Integrity artifacts

Every release contains:

- `SHA256SUMS.txt` covering all uploaded files;
- a CycloneDX source SBOM;
- GitHub build-provenance attestations for the release assets;
- the exact commit SHA in the generated release notes.

Release artifacts are also retained as GitHub Actions artifacts for fourteen days.

## Optional platform signing

The pipeline supports Apple signing and notarization when these repository secrets are configured:

- `APPLE_CERTIFICATE`, as a base64-encoded `.p12` file;
- `APPLE_CERTIFICATE_PASSWORD`;
- `APPLE_SIGNING_IDENTITY`;
- `APPLE_ID`;
- `APPLE_PASSWORD`, normally an app-specific password;
- `APPLE_TEAM_ID`.

Without those secrets, macOS bundles are built unsigned and the workflow states that explicitly in its log. Windows Authenticode signing requires a separately configured signing provider or certificate. The release pipeline never pretends an unsigned artifact is signed.

## Branch and merge order

Large product phases use isolated branches and pull requests. The backend phase is merged before the Tauri phase so the desktop pull request validates against the canonical session and sidecar API it will ship with.

## Failure behavior

A failed test, security gate, sidecar smoke test, Tauri compilation, missing bundle, checksum step, SBOM step, or provenance step prevents GitHub release creation. Matrix builds use `fail-fast: false` so failures from all supported platforms remain visible in one run.
