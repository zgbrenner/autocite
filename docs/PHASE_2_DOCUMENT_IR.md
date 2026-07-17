# Phase 2 — Structure-Preserving DocumentIR

## Status

Complete. All supported input formats now produce a `DocumentIR`, and DOCX footnotes are retained as separately addressable structures.

## Exact changes

- Added immutable `DocumentIR`, `DocumentMetadata`, `DocumentBlock`, `CitationLocation`, and `CitationOccurrence` types.
- Added stable structural IDs, absolute offsets, parent-local offsets, document ordering, formatting anchors, note/page identity, coordinates, reconstruction confidence, and provenance.
- Added paragraph, heading, sentence, citation-sentence, citation-clause, quotation, block-quotation, hyperlink, table, footnote, endnote, note-reference, and page representations.
- Added exact TXT parsing plus explicit bracketed footnote syntax.
- Added Markdown heading, block quotation, hyperlink, footnote-reference, and footnote-definition preservation.
- Added direct DOCX OOXML parsing for body blocks, tables, hyperlinks, footnotes, endnotes, markers, note IDs, displayed note numbers, note order, paragraph order, and body-to-note relationships.
- Added PDF page and coordinate preservation, conservative likely-footnote detection, explicit uncertainty, and continued `ocr_required` handling.
- Added deterministic citation-to-structure binding through `structured_citation_inventory`.
- Added deterministic mode classification with supporting evidence, conflicting evidence, confidence, and confirmation recommendations.
- Preserved `DocumentInput.text` compatibility while adding `DocumentInput.ir`.
- Added fixtures for a court brief, legal memorandum, law-review article, seminar paper, ambiguous text, mixed body/footnote citations, generated DOCX notes, and coordinate-bearing PDF pages.

## Verification

- Complete unit suite: 71 passed, 1 opt-in real-model test skipped.
- Ruff: passed.
- DOCX test confirms a note containing multiple authorities is retained and every detected note citation maps to the footnote block.
- PDF test confirms page boundaries, coordinates, likely-note confidence, and uncertainty warnings.
- Compatibility tests confirm existing flat text and citation inventory remain available.

## Architectural decisions

1. Stable locations use deterministic structural IDs plus offsets in the compatibility serialization. Plain text and Markdown offsets correspond to the original character stream; OOXML uses structural anchors because DOCX has no single original character stream.
2. Footnotes and endnotes are first-class blocks rather than text appended to body paragraphs.
3. Nested structures point to parent blocks and carry parent-local offsets; they do not duplicate text in compatibility serialization.
4. PDF note inference is evidence, never fact. Even strong layout signals are capped below `certain`.
5. The original source citation inventory is location-bearing. Corrected-text inventory remains separately available because mechanical edits can shift offsets.
6. Mode classification remains deterministic; no additional language model was introduced.

## Unresolved limitations

- DOCX tracked changes, comments, text boxes, headers, footers, fields, and floating objects are not yet represented.
- PDF reading order and footnote relationships remain limited by the quality of the PDF text layer.
- Sentence and citation-clause segmentation is conservative and will be refined alongside the citation graph and expanded parser.
- Structure-preserving corrected DOCX export is not implemented yet; the current export path remains text-oriented.
- OCR is not performed locally in this phase; scanned PDFs return `ocr_required`.
- Citation graph resolution and document-wide antecedent rules remain Phase 3 work.
