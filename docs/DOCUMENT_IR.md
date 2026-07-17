# DocumentIR

`DocumentIR` is AutoCite's structure-preserving representation for TXT, Markdown, DOCX, and text PDF inputs. It replaces the assumption that every document is merely one flat string while retaining a flat-text compatibility view for existing callers.

## What is preserved

Each structural block has a stable ID, type, exact text, absolute offsets, block-local offsets, parent, document order, formatting anchor, and relevant note or page information. Supported blocks include:

- headings, paragraphs, and sentences;
- citation clauses and citation sentences;
- footnotes, endnotes, and body note references;
- tables;
- quotations and block quotations;
- hyperlinks;
- PDF pages and extracted coordinate evidence.

Every citation in `structured_citation_inventory` includes its stable block ID, absolute and block-local offsets, footnote/endnote identity, page number, reconstruction confidence, and provenance.

## Format behavior

### TXT

Paragraph boundaries and absolute character offsets are preserved. Bracketed explicit notes such as `[1]` references and `[1] Note text` definitions become separate note-reference and footnote structures.

### Markdown

AutoCite preserves Markdown headings, block quotations, inline links, footnote identifiers such as `[^source]`, note references, and note definitions. The original Markdown remains available through `DocumentIR.to_text()`.

### DOCX

AutoCite reads the underlying OOXML package. Body paragraphs, heading styles, tables, hyperlinks, footnote and endnote markers, note IDs, displayed note numbers, note order, paragraph order inside notes, and body-to-note relationships are preserved. Notes are never silently flattened into body paragraphs.

### PDF

Text PDFs retain page boundaries and coordinates exposed by the PDF text layer. AutoCite uses page position and font-size evidence to identify likely footnote fragments. Because PDFs usually lack actual note relationships, reconstructed footnotes are labeled `low` or `medium` confidence and accompanied by an uncertainty warning. They are never labeled certain.

Scanned and image-only PDFs still return `ocr_required` when insufficient text is extractable.

## Compatibility API

`load_document_bytes()` still returns `DocumentInput.text` and `DocumentInput.source_format`. It now also returns `DocumentInput.ir`. Existing text-only callers therefore continue to work.

Uploaded review results add:

- `document_ir`, a compact structural summary;
- `structured_citation_inventory`, the original source citations with stable locations;
- `input_document.document_ir`, the parsed input summary.

The existing corrected-text and citation-inventory fields remain available.

## Mode classification

The classifier is deterministic. It considers explicit selection, declared document type, document metadata, caption and court language, academic language, inline citation patterns, and numbered notes. It returns:

- `selected_mode` and the compatible `mode` alias;
- `confidence`;
- supporting `evidence`;
- `conflicting_evidence`;
- `user_confirmation_recommended`;
- deterministic provenance.

Explicit user selection remains authoritative. Ambiguous documents recommend confirmation instead of using a model to guess.
