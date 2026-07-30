# AutoCite Desktop

AutoCite Desktop is the simplest way to review legal citations without configuring Python, an MCP host, or a local model. The portable build contains the application and its runtime in one ZIP.

## Start on Windows

1. Download `AutoCite-windows-x64-v0.6.0.zip` from the GitHub Release.
2. Extract the entire ZIP to a normal folder.
3. Open the extracted `AutoCite` folder.
4. Double-click `AutoCite.exe`.

Do not run the executable from inside the ZIP. The portable build does not require an installer, administrator access, Python, a dedicated GPU, or a separate runtime download.

Windows can display a reputation warning for a newly released unsigned application. Use only the official repository release and compare the ZIP against its matching `.sha256` file when authenticity matters.

## Recommended settings for an 8 GB computer

Keep **Standard local review (recommended)** selected. This is the complete deterministic reviewer. It does not load the optional 0.8B model, PyTorch, Transformers, or model weights.

The standard workflow is local, offline, and appropriate for ordinary laptops without a dedicated GPU. Closing memory-heavy programs can help when reviewing unusually large documents.

## Review a document

AutoCite accepts:

- TXT;
- Markdown;
- DOCX;
- searchable, text-based PDF.

Choose a document or drag it into the window. AutoCite reviews it on a background worker so the window remains responsive. The source file is read-only and is never modified.

The main options are:

- **Citation style:** automatic detection, Bluepages, or Whitepages;
- **Document type:** automatic detection, brief or motion, legal memorandum, law review or journal, or seminar paper;
- **Jurisdiction:** automatic or general, federal, or California;
- **Review engine:** standard deterministic review or an optional advanced local model when installed separately.

## Review each item

The workspace separates analysis from user decisions. Every detected change or review finding has a stable identity and one of three decisions:

- **Accepted:** apply the supported text change, or mark a judgment-dependent item reviewed;
- **Pending review:** retain the item in the review record without resolving it;
- **Rejected:** do not apply the proposed text change and retain the decision in the review record.

High-confidence safe mechanical edits begin as accepted. Judgment-dependent and unsupported findings begin as pending. **Accept all safe changes** affects only high-confidence `safe_auto_fix` items. It never accepts unsupported or judgment-dependent work.

The workspace provides:

- accept, reject, and reset controls for each item;
- bounded undo and redo history;
- previous and next navigation;
- filters for decision state, correction level, severity, and citation source type;
- full-text search across issue code, explanation, original text, suggestion, rule family, source type, and provenance;
- exact selection of the source range in the original extracted text;
- a corrected preview regenerated from the currently accepted text edits;
- keyboard shortcuts for open, save, undo, redo, and item navigation;
- a final review summary before export.

A filter can hide an item immediately after its decision changes. This does not delete it. Clear or change the filter to see it again.

## Understand the results

The summary reports:

- detected citation style and confidence;
- total review items;
- accepted, pending, and rejected counts;
- items outside current rule coverage.

The result areas contain:

- **Corrected preview:** the source text with only currently accepted mechanical edits applied;
- **Original text:** the extracted source text, with the selected finding's source range highlighted;
- **Item details:** explanation, decision, correction level, severity, confidence, location, source type, rule family, original text, suggestion, missing facts, and provenance.

AutoCite intentionally labels ambiguous short forms, source-dependent issues, local-rule questions, and unsupported rule families instead of guessing.

## Preserve an original DOCX

When the source is DOCX, AutoCite creates the reviewed document from a copy of the original Word package rather than rebuilding a plain-text document.

For edits that map unambiguously to supported Word text nodes, AutoCite:

- inserts Word tracked deletions and insertions;
- preserves the original run formatting around the edit;
- leaves untouched package parts unchanged;
- preserves surrounding tables, styles, numbering, headers, footers, hyperlinks, fields, bookmarks, section properties, footnotes, endnotes, comments, and other Word parts that are not modified;
- adds a Word comment for a pending review item when its range maps safely to the main document;
- validates the output package and every internal relationship before writing it.

AutoCite refuses an edit when its range crosses an unsupported Word structure, an existing revision boundary, a hyperlink, a field, multiple package parts, or another mapping that cannot be proven safe. A review comment that cannot be anchored safely remains in the JSON audit report rather than forcing risky markup into the Word document.

The original DOCX is fingerprinted during review. If it changes before export, AutoCite requires a new review rather than applying stale offsets.

## Export non-DOCX sources

TXT, Markdown, and PDF files do not contain an original Word package. For those formats, **Save reviewed Word document** creates a clearly labeled text-level DOCX containing the reviewed text and tracked insertions and deletions. It does not recreate the source file's complete visual layout or pagination.

## Save the work

**Save reviewed Word document** uses the decisions currently shown in the workspace. Pending and unsupported items can remain as review comments or audit entries. AutoCite warns before exporting while unresolved items remain.

**Save audit report** creates a compact JSON record containing:

- the document fingerprint and source format;
- mode detection and jurisdiction;
- every review item with its stable ID and current decision;
- applied text edits;
- citation inventory;
- local-model and local-retrieval status;
- DOCX-preservation readiness and warnings;
- accuracy boundaries.

The audit report does not include the source file's full local path or the in-memory original document bytes.

Exports are written atomically. AutoCite refuses to overwrite the source document, even when the same filename is selected accidentally.

## Privacy and network behavior

Standard desktop review:

- runs locally;
- has no telemetry;
- does not load optional model packages;
- does not download model weights;
- does not send the document to CourtListener;
- does not change the original file;
- keeps original DOCX bytes in memory only for the active review and never writes them to settings or audit reports.

Network-based CourtListener review remains available through the CLI and MCP workflows when explicitly configured. It is not enabled automatically in the portable desktop workflow.

## Common errors

### The PDF needs OCR

The PDF does not contain readable text. Create a searchable PDF with OCR and review that copy.

### The document is too large

AutoCite accepts one document up to 15 MB. Split a larger document into logical parts and review them separately.

### AutoCite cannot read the file

Close the document in other programs, confirm that it still exists, or copy it to a folder you can access.

### The review ran out of memory

Close other applications and use Standard local review. The optional model is not required for normal citation review.

### DOCX preservation is unavailable

The source may have changed during review, become unreadable, or contain an unsupported mapping for an accepted edit. Review the current file again. AutoCite does not silently replace a preservation failure with a reconstructed DOCX for an original DOCX source.

### A finding appears only in the audit report

AutoCite could not anchor the finding to one safe Word text range. The finding remains available for human review without risking corruption of the DOCX package.

## Packaged self-tests

Release builds execute both commands on Windows, macOS, and Linux before publication:

```text
AutoCite --self-test
AutoCite --self-test-preservation
```

The first command performs deterministic citation correction and creates a nonempty reviewed DOCX. The preservation command creates a structured DOCX with a header and table, reviews it, exports it through the preservation path, validates the package, confirms the header and table remain intact, and confirms the source hash is unchanged.

Every portable ZIP also contains:

- `START HERE.txt`;
- `LICENSE.txt`;
- `BUILD-MANIFEST.json`;
- a matching external SHA-256 checksum file;
- an external release manifest.

## Accuracy boundaries

AutoCite checks supported citation mechanics and citation structure. It does not determine whether an authority is current, good law, controlling, or supportive of a proposition. Source retrieval does not replace quotation review, official pincite verification, current local rules, journal rules, licensed citators, or professional legal judgment.

## Install from Python instead

Developers can install the optional desktop dependency and run the same shared core:

```bash
uv tool install 'autocite-mcp[desktop]'
autocite-desktop
```

The portable GitHub Release is the recommended path for ordinary desktop use.