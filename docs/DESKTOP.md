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

## Understand the results

The summary reports:

- detected citation style and confidence;
- citation count;
- safe fixes applied;
- items requiring review;
- items outside current rule coverage;
- remaining detected mechanical issues.

The result tabs contain:

- **Corrected text:** the source text with only permitted mechanical edits applied;
- **Original text:** the extracted source text;
- **Review items:** structured findings with severity, confidence, correction level, location, provenance, rule family, missing facts, and any supported suggestion.

AutoCite intentionally labels ambiguous short forms, source-dependent issues, local-rule questions, and unsupported rule families instead of guessing.

## Save the work

**Save reviewed Word document** creates a new DOCX with text-level tracked insertions and deletions. It does not recreate the source document's complete layout, styles, fields, footnotes, or pagination.

**Save audit report** creates a compact JSON record containing the document fingerprint, mode detection, summary, applied edits, citation inventory, review items, local-processing status, and accuracy boundaries. It does not include the source file's full local path.

Exports are written atomically. AutoCite also refuses to overwrite the source document, even when the same filename is selected accidentally.

## Privacy and network behavior

Standard desktop review:

- runs locally;
- has no telemetry;
- does not load optional model packages;
- does not download model weights;
- does not send the document to CourtListener;
- does not change the original file.

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

## Packaged self-test

Release builds execute the application with `--self-test` on Windows, macOS, and Linux before publication. The self-test performs a deterministic citation correction, exports a reviewed DOCX, and verifies that the result exists and is nonempty.

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
