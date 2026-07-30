# AutoCite Production Roadmap Design

## Status

Approved by the repository owner on July 30, 2026. This document turns the approved roadmap into an executable product design.

## Objective

Move AutoCite from a capable citation-analysis engine and early desktop shell into a dependable legal citechecking product that is safe on real documents, usable by nontechnical users, efficient on an 8 GB CPU-only Windows laptop, and honest about what it can and cannot verify.

## Delivery sequence

The work is deliberately staged so each release is independently useful and verifiable.

### Release 0.6.0: recover and ship the portable desktop

Finish the existing productization branch before broadening scope. The release must provide an installer-free Windows x64 ZIP, deterministic offline review, responsive background processing, source-safe exports, readable diagnostics, a JSON audit report, and a packaged self-test. It must not require Python, a GPU, a model download, administrator privileges, or an internet connection for standard review.

### Release 0.7.0: document fidelity and review workspace

Preserve the original DOCX package instead of rebuilding a plain-text document. AutoCite will apply supported citation edits directly to existing WordprocessingML while preserving unrelated paragraphs, styles, numbering, tables, footnotes, endnotes, headers, footers, hyperlinks, bookmarks, comments, fields, and section properties. Review-required findings will become Word comments anchored to their source locations when a reliable mapping exists. The desktop will expose exact change and finding locations, per-item decisions, bulk acceptance for safe mechanical fixes, undo, filtering, and a final unresolved-item checklist.

### Release 0.8.0: broader source coverage and local evidence

Add rule families and extractors in risk-controlled increments for court and docket documents, books and treatises, state administrative materials, registers, Tribal materials, archival sources, AI-generated materials, newspapers, multimedia, and improved internet citations. Add a source-packet workflow that compares cited metadata, quotations, and page markers against user-supplied authorities without making legal-support or good-law conclusions. Optional OCR remains a separate component so the standard portable build stays small and low-memory.

### Release 0.9.0: project-wide citechecking

Add a matter workspace with shared authority identities, cross-document consistency checks, a draft Table of Authorities, jurisdiction and journal rule packs, and versioned house-style profiles. Project data remains local by default.

## Architecture

### Deterministic core remains authoritative

The existing citation engine, DocumentIR, citation graph, and deterministic rule families remain the source of truth for automatic changes. Optional models may classify or propose, but no model-only proposal becomes an automatic edit.

### Document editing is isolated from citation analysis

A new `docx_preservation` module will own all Word package mutation. It consumes explicit text edits and review annotations expressed in source offsets plus DocumentIR locations. It does not perform citation analysis. This separation allows the same analysis result to drive desktop, CLI, MCP, and export workflows while keeping Word corruption risk contained and testable.

### Review decisions are first-class data

A review-session model will assign stable IDs to detected edits and findings. Each item records source range, correction level, decision state, provenance, and explanation. Decisions are applied to produce an export plan rather than mutating the analysis result in place. The session is serializable so it can support desktop persistence and later matter-wide work.

### Evidence is never a legal conclusion

Source-packet and CourtListener results will use explicit states such as metadata matched, quotation candidate found, page marker found, ambiguous, and unavailable. They will never assert that an authority is current, controlling, good law, or supportive of the proposition.

## Data flow

1. Load the source document into DocumentIR without changing the source file.
2. Run deterministic extraction, graph construction, rules, and safe-fix generation.
3. Convert edits and findings into a stable review session.
4. Let the user retain defaults or accept/reject supported changes.
5. Build an export plan from accepted edits and unresolved annotations.
6. For DOCX input, apply the plan to a copy of the original OPC package.
7. Validate the output package, verify source preservation, and write atomically to a different path.
8. Generate a compact audit record containing the source hash, version, decisions, performed checks, unperformed checks, and accuracy boundaries.

## DOCX preservation constraints

- Never overwrite the source file.
- Never flatten the original DOCX merely to apply citation edits.
- Preserve every unmodified ZIP part byte-for-byte whenever Word package relationships do not require a change.
- Preserve existing tracked changes and comments.
- Refuse an edit when its source range cannot be mapped confidently to Word text nodes.
- Apply insertions and deletions with Word tracked-change markup when enabled.
- Anchor review comments only when the target range maps unambiguously.
- Validate that the result opens as an OPC ZIP and that all referenced relationship targets still exist.
- Fail closed with a usable audit report rather than emitting a partially corrupted document.

## Desktop usability constraints

- Standard deterministic mode is the default and recommended setting for 8 GB systems.
- Review work must not block the UI thread.
- The user can always see whether work was local or network-assisted.
- The user can navigate from a finding to its source location.
- Safe edits can be accepted in bulk, but unsupported or judgment-dependent findings cannot.
- Exports use clear default names and atomic writes.
- Error messages state what happened, what was preserved, and what the user can do next.
- Keyboard navigation and screen-reader labels are required for new controls.

## Evaluation strategy

### Automated synthetic and adversarial tests

Keep the existing gold corpus and add focused regression cases for each new extractor, rule family, Word mutation operation, and failure mode. Every production change follows red-green-refactor.

### Real-document evaluation harness

Create a manifest-driven evaluator for permissioned, anonymized documents without committing confidential source files. Gold annotations are stored separately from documents and may reference locally mounted files. Primary release metrics are safe-fix precision, false-positive rate, citation recall, unintended prose modification, short-form abstention, DOCX structural preservation, export validity, memory use, and runtime.

### Hardware acceptance

The Windows portable release must be tested on an 8 GB RAM laptop without a dedicated GPU. Standard review must start, process representative TXT, DOCX, and searchable PDF documents, export a reviewed DOCX and JSON report, and complete the packaged self-test without installing anything.

## Release and security model

- Releases are immutable version tags.
- Portable archives include a build manifest and SHA-256 checksum.
- Build workflows exclude optional model runtimes from the standard desktop package.
- Signing and notarization are added when protected credentials are available; unsigned status remains disclosed until then.
- Update checks are explicit and never transmit document content.
- No telemetry is added.

## Non-goals for the current implementation cycle

- Retraining the 0.8B model without held-out evidence of model-specific failures.
- Claiming full Bluebook compliance.
- Determining good-law status, precedential weight, controlling authority, or proposition support.
- Cloud collaboration or mandatory accounts.
- Bundling OCR or large model runtimes into the low-memory standard package.

## Immediate implementation scope

This cycle will:

1. Repair and verify the existing 0.6.0 branch and release path.
2. Add the review-session data model and deterministic decision semantics.
3. Add a preservation-first DOCX edit planner and package validator, with tracked changes and review comments for reliably mapped ranges.
4. Integrate preservation exports into the desktop controller while keeping the existing reconstructed-DOCX export as a clearly labeled fallback for non-DOCX inputs.
5. Add a local real-document evaluation harness and nonconfidential fixtures.
6. Improve CI diagnostics and document the external runner-allocation limitation currently preventing GitHub-hosted jobs from starting.

Later 0.8 and 0.9 work remains governed by this design but will receive separate task-level plans before implementation.