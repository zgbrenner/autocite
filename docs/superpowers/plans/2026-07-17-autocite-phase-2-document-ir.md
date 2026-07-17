# AutoCite Phase 2 DocumentIR Implementation Plan

## Goal

Implement a structure-preserving `DocumentIR` for all supported document formats, retain exact citation locations, and preserve the existing flat-text API.

## Tasks

### 1. Core IR and compatibility map

- Add immutable metadata, block, location, mapping, citation-occurrence, and document classes.
- Add deterministic serialization and absolute-to-block lookup.
- Add tests for stable IDs, offsets, nested spans, and compatibility text.

### 2. Plain text and Markdown parsing

- Preserve headings, paragraphs, quotations, links, footnote references, and definitions.
- Add sentence, citation-sentence, and citation-clause spans.
- Add mixed body/note and seminar-paper fixtures.

### 3. DOCX OOXML parsing

- Parse body paragraphs, headings, tables, hyperlinks, footnote/endnote markers, footnotes, and endnotes.
- Preserve note identity, displayed number, order, paragraph order, and marker relationship.
- Add generated DOCX fixtures with multiple citations and prose plus several authorities in one note.

### 4. PDF structure and uncertainty

- Preserve page boundaries and available coordinates.
- Identify likely footnote fragments conservatively and assign confidence below certainty.
- Preserve the OCR-required failure path.

### 5. Citation locations and mode classification

- Bind deterministic extraction results to stable block and note/page locations.
- Expand mode-classification output with evidence, conflicts, confidence, and confirmation advice.
- Keep explicit mode selection authoritative.

### 6. Integration and verification

- Add `DocumentInput.ir` and structured uploaded-review output without breaking flat-text callers.
- Update documentation and the Phase 2 completion report.
- Run the complete test suite, Ruff, compile checks, evaluations, and package build.
- Publish and merge the isolated Phase 2 pull request.
