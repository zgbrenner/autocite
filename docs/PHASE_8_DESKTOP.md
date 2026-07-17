# Phase 8 — Downloadable Desktop Application

## Status

Implemented as an initial local PySide6 application and signable cross-platform build pipeline. Advanced inspector views remain incomplete and are disclosed.

## Exactly what changed

- Added a UI-independent controller using the existing uploaded-review and DOCX-export APIs.
- Added drag/drop and picker workflow, mode/document/engine selection, side-by-side text, issue provenance/confidence, offline/privacy status, and caller-selected export.
- Added explicit original-preserving failure states.
- Added optional desktop and desktop-build dependency groups and executable entry point.
- Added PyInstaller spec and Windows/macOS/Linux artifact workflow with checksums.
- Added controller tests proving source preservation, core reuse, format rejection, and export.

## Architectural decisions

- Direct in-process calls avoid a second rules implementation and minimize local attack surface.
- PySide imports lazily, so deterministic core installation remains lightweight.
- Model use is offline-only from the desktop controller.
- Signing/notarization are release-environment operations; no credentials are stored in the repository.

## Unresolved

- Outline/footnote navigation, citation inventory, graph inspector, filters, per-change accept/reject, and first-run model repair UI require further UI work.
- Bundles are signable but not signed without platform credentials.
- Native installer/uninstaller and optional cache-removal UX need platform release testing.
