---
title: "Why AI Hallucinates Legal Citations—and How to Review Them"
description: "Learn why plausible legal citations can contain invented reporters, pages, courts, years, parentheticals, or authorities, and use a safer source-verification workflow."
publishedAt: 2026-07-31
audience: all
keywords:
  - AI legal citation hallucinations
  - fake case citations
  - citation verification
---

A fabricated legal citation is dangerous precisely because it often looks ordinary. The case name sounds plausible. The reporter abbreviation is familiar. The page number fits the pattern. A fluent answer can conceal that one or more citation facts were never supported.

## What counts as a citation hallucination?

A hallucination is not limited to inventing an entire case. It can include:

- a real case paired with the wrong reporter or page;
- a nonexistent case name;
- an incorrect court or year;
- a quotation that does not appear in the source;
- a fabricated pincite;
- an invented parenthetical;
- a source that exists but does not support the proposition;
- a claim that authority is controlling or remains good law without a reliable citator review.

Some errors are retrieval failures. Others arise when a model completes a familiar citation pattern from probability rather than evidence.

## Why legal citations are especially vulnerable

Legal citations are highly structured. That structure helps a model produce text that *looks* correct even when the underlying facts are absent. A citation can be syntactically polished and substantively false.

The problem becomes harder with short forms. `Id.`, `supra`, shortened case names, and statutory short forms depend on earlier authorities and document structure. A model reviewing an isolated sentence may guess the intended antecedent.

## The safer review sequence

Use a layered process:

1. **Extract the citation exactly.** Preserve the original text and location.
2. **Separate mechanics from facts.** Abbreviation and spacing corrections are different from reporter, court, year, and page data.
3. **Locate the authority in an authoritative source.** Do not rely on the model's citation alone.
4. **Confirm every metadata field.** Case name, reporter, volume, page, court, year, statute title, section, regulation title, and source date.
5. **Open the cited page.** Verify quotations and pincites in context.
6. **Evaluate proposition support.** A source can contain similar words without supporting the legal claim.
7. **Use an appropriate citator.** Later-citation counts are not a substitute for treatment analysis or good-law review.

## Where deterministic checking helps

A deterministic citation rule can normalize an existing `USC` abbreviation or section-symbol spacing without inventing a new authority. The rule should record the exact span, proposed replacement, and reason the change is considered mechanical.

AutoCite uses that narrower contract for automatic edits. It can optionally retrieve CourtListener opinion text for candidate source review, but it does not label a source as supporting a proposition or remaining good law.

## A useful prompt boundary

When using a general-purpose AI system for legal work, avoid asking it to "fix all citations" without constraints. A safer instruction is:

> Identify citation-shaped text. Do not add or replace any factual citation field unless it is present in a source I supplied. Separate mechanical formatting suggestions from source-verification questions.

Even then, independently verify the result.

## Red flags in a generated citation

Pause when:

- the authority cannot be found quickly;
- the reporter and year seem inconsistent;
- the quoted language appears only in secondary summaries;
- the pincite lands on an unrelated page;
- the parenthetical is unusually perfect for the proposition;
- a short form has more than one plausible antecedent;
- the answer states good-law status without identifying a citator and date.

## The core rule

**Formatting confidence is not source confidence.** A citation can be mechanically elegant and legally unusable.

Use the [private Citation Risk Scan](/citation-risk-scan/) for a limited mechanical demonstration, then follow the source-review sequence before relying on any authority.
