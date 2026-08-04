---
title: "How to Check Bluebook Citations in a Word Document"
description: "A practical workflow for reviewing legal citations in DOCX files while preserving the original, validating exact changes, handling footnotes, and exporting a reviewed copy."
publishedAt: 2026-07-31
audience: all
keywords:
  - Bluebook checker for Word
  - Word legal citation checker
  - DOCX citation review
---

Microsoft Word is where many legal documents live, but a `.docx` file is more than plain text. It can contain footnotes, endnotes, fields, comments, tracked changes, hyperlinks, styles, tables, headers, and cross-references.

A safe citation-review workflow should preserve the original file, distinguish text-level corrections from layout changes, and verify the exported result before filing or publication.

## 1. Save the original separately

Do not run automated edits against the only copy. Preserve the submitted or attorney-approved version and create a clearly named working copy.

AutoCite keeps the imported source separate from its working revision. That design reduces the chance that autosave or a batch correction silently replaces the original.

## 2. Confirm the document is readable

A DOCX file normally contains machine-readable text. Searchable PDFs also work, but an image-only PDF requires OCR before a citation tool can review the text reliably.

For a complex Word document, check whether important citations appear in:

- body text;
- footnotes or endnotes;
- text boxes;
- tables;
- headers or footers;
- generated fields.

Not every parser supports every advanced Word object equally.

## 3. Choose the correct citation mode

Briefs, motions, pleadings, and practitioner memoranda generally start with Bluepages priorities. Law-review articles, seminar papers, and student notes generally start with Whitepages priorities.

Also collect any court, professor, journal, or organization-specific rules that control the final format.

## 4. Run the citation review without rewriting prose

A purpose-built checker should identify citation spans and propose bounded changes. Review each item for:

- the exact original characters;
- the proposed replacement;
- the rule family;
- whether the change is mechanical;
- whether source or legal judgment is still required.

Avoid a workflow that sends the entire document to a general-purpose model with an instruction to "clean everything up." The resulting prose changes can be difficult to separate from citation changes.

## 5. Review footnotes and short forms in context

Footnotes create relationships across the document. `Id.`, `supra`, `supra note`, and shortened case names may depend on sources in earlier notes.

AutoCite's document model retains supported footnote and endnote blocks separately and builds a document-wide citation graph. Ambiguous antecedents remain review-required.

## 6. Accept changes selectively

Mechanical corrections can still be wrong when the underlying span was misidentified or the document changed after review. Use a tool that checks the original span again before applying an edit.

When several changes are accepted, apply them from the end of the document toward the beginning or use an offset-safe edit engine so earlier replacements do not shift later locations.

## 7. Export a reviewed copy

Choose an export that fits the next step:

- DOCX for continued editing;
- PDF for visual review;
- Markdown or TXT for text workflows;
- a structured audit report for review records.

AutoCite can create reviewed DOCX output and optional insertion/deletion markup. Text-level change preservation does not guarantee a pixel-perfect round trip for every custom style, Word field, footnote layout, or pagination choice.

## 8. Compare and proof the final file

Open the exported document in Word and review:

- every accepted citation change;
- footnote and endnote numbering;
- cross-references and fields;
- italics, small caps, and quotation formatting;
- tables and text boxes;
- page breaks and line wrapping;
- comments and tracked changes;
- filing or journal requirements.

Then perform the independent source and citator review required for the document.

## A practical naming convention

Keep versions obvious:

```text
Motion-original.docx
Motion-autocite-review.docx
Motion-source-verified.docx
Motion-final-approved.docx
```

A clear version trail is more valuable than an ambiguous file named `FINAL-v7-revised-final.docx`.

[Download AutoCite](https://github.com/zgbrenner/autocite/releases/latest) for local DOCX review or read the [methodology](/methodology/).
