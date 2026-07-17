# AutoCite Phase 2: Structure-Preserving DocumentIR Design

## Scope

Phase 2 replaces flat-file ingestion with a structure-preserving intermediate representation while keeping the existing flat-text API compatible. It covers TXT, Markdown, DOCX, and text PDFs. It does not implement citation-memory resolution or expanded Bluebook rules, which remain Phase 3 and Phase 4 work.

## Representation

`DocumentIR` owns immutable document metadata, source format, selected citation mode, normalized compatibility text, ordered structural blocks, stable source-location mappings, and citation occurrences. Each `DocumentBlock` has a stable ID, block kind, exact text, document-wide offsets, block-local offsets, parent relationship, order, note/page identifiers, reconstruction confidence, coordinates when available, and a formatting anchor.

Block kinds cover headings, paragraphs, sentences, citation clauses, citation sentences, footnotes, endnotes, tables, quotations, block quotations, hyperlinks, page boundaries, and explicit note references. Nested spans point to their parent block rather than duplicating text in compatibility serialization.

`CitationLocation` binds every extracted citation to its exact block, note or page, absolute offsets, block-local offsets, and provenance. IDs are deterministic from source structure and order.

## Parsing

- Plain text preserves paragraph and line ordering.
- Markdown recognizes headings, block quotations, inline links, footnote references, and footnote definitions while retaining Markdown identifiers.
- DOCX reads body paragraphs and tables through OOXML, then reads `footnotes.xml` and `endnotes.xml` directly. Note markers, note IDs, displayed numbers, note order, paragraph order, and body-to-note relationships are retained.
- PDF parsing creates page-scoped blocks, retains text coordinates exposed by pypdf, and labels likely footnote reconstruction with explicit confidence and uncertainty. Image-only or insufficient-text PDFs continue to return `ocr_required`.

## Compatibility

`DocumentIR.to_text()` produces deterministic normalized text and an offset map. Existing `DocumentInput.text` callers continue to work; `DocumentInput` gains an `ir` field. Uploaded-document review exposes a structured citation inventory while preserving the existing response schema.

## Mode classification

The deterministic classifier gives explicit user selection highest priority, then considers document metadata, caption/court language, inline citation patterns, numbered notes, academic language, and structure. It returns selected mode, confidence, supporting evidence, conflicting evidence, and whether confirmation is recommended. No model is introduced.

## Safety boundaries

- Original bytes are never rewritten during parsing.
- Reconstructed PDF footnotes are never labeled certain.
- DOCX notes are separate blocks and never silently merged into body paragraphs.
- Stable locations are based on structural IDs plus deterministic serialized offsets.
- Existing callers receive normalized text but can trace it back to the IR.
