# AutoCite 0.6.0

AutoCite 0.6.0 turns the initial desktop shell into a practical, installer-free application for everyday legal citation review.

## Portable desktop

- Download the ZIP for your operating system, extract it, and launch AutoCite.
- No Python installation, package manager, administrator access, dedicated GPU, or model download is required for standard review.
- The Windows x64 bundle is designed to work on ordinary 8 GB laptops in deterministic mode.
- Every ZIP includes a start guide, MIT license, file manifest, and matching SHA-256 checksum.

## Desktop usability

- Reviews run on a background worker so the window remains responsive.
- Clear automatic Bluepages and Whitepages selection, document-type choices, and jurisdiction presets.
- Side-by-side original and corrected text, structured review items, confidence, provenance, locations, and suggestions.
- One-click copying, reviewed DOCX export, and compact JSON audit-report export.
- Friendly recovery for missing, unreadable, unsupported, oversized, scanned, and memory-constrained files.
- Saved window and review preferences.

## Safety and reliability

- The source document is never modified and AutoCite refuses to export over it.
- Exports use atomic replacement so an interrupted write cannot leave a partial result at the chosen path.
- Standard review remains completely local, has no telemetry, and does not load optional model packages.
- The packaged executable includes a deterministic review-and-export self-test that runs in every release build.
- Portable archives are smoke-tested on Windows, macOS, and Linux before release publication.

## Accuracy boundary

AutoCite checks supported citation mechanics and flags judgment-dependent work. It does not determine whether authority is good law, controlling, or supportive of a proposition, and it does not replace current local rules, official source review, or legal judgment.
