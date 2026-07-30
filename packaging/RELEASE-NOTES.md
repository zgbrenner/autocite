# AutoCite 0.6.0

AutoCite 0.6.0 turns the initial desktop shell into a practical, installer-free application for local legal citation review, with human decision controls and preservation-first Word export.

## Portable desktop

- Download the ZIP for your operating system, extract it, and launch AutoCite.
- Standard review requires no Python installation, package manager, administrator access, dedicated GPU, model download, or internet connection.
- The Windows x64 bundle is designed for ordinary 8 GB laptops in deterministic mode.
- Every ZIP includes a start guide, MIT license, file manifest, external release manifest, and matching SHA-256 checksum.

## Human review workspace

- Reviews run on a background worker so the window remains responsive.
- Automatic Bluepages and Whitepages detection, document-type choices, and jurisdiction presets.
- Every change and finding has a stable review ID and an Accepted, Pending, or Rejected decision.
- High-confidence safe mechanical changes begin accepted. Judgment-dependent and unsupported findings begin pending.
- Per-item accept, reject, and reset controls.
- Accept all safe changes affects only high-confidence mechanical changes.
- Bounded undo and redo history, previous and next navigation, filters, search, and keyboard shortcuts.
- Exact source-range selection in the original extracted text.
- Corrected preview regenerated from the currently accepted text edits.
- Final unresolved-item summary before export.

## Preservation-first DOCX export

- A DOCX source is exported from a copy of the original Word package instead of being flattened into a new plain-text document.
- Supported mapped changes use Word tracked deletions and insertions.
- Unmodified package parts remain unchanged, preserving surrounding tables, styles, numbering, headers, footers, hyperlinks, fields, bookmarks, section properties, footnotes, endnotes, comments, and other untouched structure.
- Pending findings become Word comments when their source ranges map safely to the main document.
- Findings that cannot be anchored safely remain in the JSON audit report.
- Edits crossing protected or ambiguous Word structures are refused rather than forced into the document.
- The original DOCX is fingerprinted during review, and a changed source must be reviewed again before export.
- TXT, Markdown, and PDF inputs retain the clearly labeled text-level reviewed DOCX fallback.

## Audit and evaluation

- Compact JSON audit reports include every review item, stable ID, decision, provenance, document fingerprint, preservation status, and accuracy boundary without exposing the full local source path or in-memory source bytes.
- A permissioned real-document evaluation harness accepts locally mounted manifests, requires an explicit permission basis, rejects path traversal and duplicate IDs, measures exact citations and issue codes, records runtime and peak memory, and fails release gates on unsafe edits, source mutation, invalid DOCX output, guessed antecedents, or unexpected local-mode network activity.
- Synthetic regression evaluation remains available and is not represented as a substitute for real-document validation.

## Safety and reliability

- The source document is never modified and AutoCite refuses to export over it.
- Exports use atomic replacement so an interrupted write cannot leave a partial result at the chosen path.
- Standard review remains local, has no telemetry, and does not load optional model packages.
- The release workflow requires both a deterministic review-and-export self-test and an original-DOCX preservation self-test on Windows, macOS, and Linux before publication.
- The preservation self-test validates the Word package, confirms a header and table remain intact, and confirms the source hash is unchanged.
- Portable archives must pass checksum and manifest verification before an immutable release tag is created.

## Accuracy boundary

AutoCite checks supported citation mechanics and flags judgment-dependent work. It does not determine whether authority is current, good law, controlling, or supportive of a proposition. It does not replace current local rules, official source review, licensed citators, or legal judgment.