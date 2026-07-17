# AutoCite MCP

AutoCite turns Claude or ChatGPT into a safer legal-citation specialist for:

- **Bluepages** — briefs, motions, pleadings, court filings, and practitioner memoranda.
- **Whitepages** — law reviews, student notes, seminar papers, and academic legal research.

AutoCite 0.4 also includes an optional local SLM layer using [`foolish-bandit/AutoCite-0.8B`](https://huggingface.co/foolish-bandit/AutoCite-0.8B), a citation-specialized LoRA adapter based on `Qwen/Qwen3.5-0.8B`. The model can classify ambiguous citation issues and propose structured repairs, but deterministic validation remains in control of every automatic edit.

The normal workflow remains simple: connect AutoCite, provide text or a document, and ask the model to fix the citations. AutoCite detects the appropriate mode, applies deterministic fixes, supplies citation-rule knowledge, and—when explicitly requested—retrieves case authority to compare quotations, page markers, and candidate supporting passages.

## Install in three minutes

### Claude Desktop: local and private

```bash
uv tool install "git+https://github.com/zgbrenner/autocite.git"
autocite setup-claude
```

Completely quit and reopen Claude Desktop. Then ask:

> Use AutoCite to review and fix every citation in this document. Preserve all non-citation prose and list anything that still requires source review.

### ChatGPT or Claude web

Run the Streamable HTTP server:

```bash
AUTOCITE_TRANSPORT=streamable-http autocite-mcp
```

Connect an authenticated HTTPS endpoint ending in `/mcp`. For confidential work, use a private deployment or secure MCP tunnel rather than an unauthenticated public URL. Detailed steps are in [`docs/CONNECT.md`](docs/CONNECT.md).

## Start-here tools

### `review_document`

Use this for text-based requests. It returns:

- automatic Bluepages/Whitepages selection;
- corrected text containing deterministic citation edits;
- exact citation spans and source classifications;
- applied edits and unresolved issues;
- source-specific citation guidance and rule families;
- a federal or state jurisdiction profile;
- an explicit response contract that prohibits fabricated facts and overclaims.

Set `deep_review=true` to retrieve matched case authority from CourtListener and prepare evidence-backed findings. Ordinary review makes no source-retrieval network call.

### `review_uploaded_document`

Use this for TXT, Markdown, DOCX, and text-based PDF. Scanned or image-only PDFs return `ocr_required` rather than silently producing incomplete text. Files are processed in memory and limited to 15 MB.

Uploaded documents are parsed into a structure-preserving `DocumentIR`. DOCX footnotes and endnotes remain separate from body text, Markdown note identifiers are retained, and text PDFs keep page and coordinate evidence where available. Every original citation is returned with a stable block, note, or page location in `structured_citation_inventory`. See [`docs/DOCUMENT_IR.md`](docs/DOCUMENT_IR.md).

Each review also builds a document-wide citation graph. It keeps conservative authority identities, every citation occurrence, structural relationships, and explicit short-form resolutions. Ambiguous `Id.`, short-case, `supra`, `supra note`, statutory short forms, and `hereinafter` uses return candidates and a review warning instead of a guessed antecedent. See [`docs/CITATION_GRAPH.md`](docs/CITATION_GRAPH.md).

Contextual findings come from declared deterministic rule families and carry one of four correction levels. Only `safe_auto_fix` findings can be applied without approval. Exact supported, partial, and unsupported coverage is published in [`docs/RULE_COVERAGE.json`](docs/RULE_COVERAGE.json); AutoCite does not claim complete Bluebook compliance.

When a finding is ambiguous or requires explanation, AutoCite can retrieve a small set of approved original Markdown summaries entirely locally. Every result identifies its chunk ID, source file, heading, license, and ranking provenance. Clean citations skip retrieval. See [`docs/LOCAL_RULE_RETRIEVAL.md`](docs/LOCAL_RULE_RETRIEVAL.md).

### `open_citecheck_workspace`

MCP Apps-capable hosts can render a self-contained workspace with:

- original/corrected review context;
- issue and source-evidence filters;
- accept/reject controls;
- quotation and pincite statuses;
- candidate source passages;
- one-click corrected-text copying.

Text-only clients still receive a useful structured result.

### `export_review_docx`

Creates an in-memory DOCX containing corrected text and optional Word insertion/deletion markup. It preserves text-level changes, not the original file's complete layout, styles, fields, footnotes, or pagination.

## Deep source review

With `COURTLISTENER_TOKEN` configured and `deep_review=true`, AutoCite can:

1. locate U.S. case citations through CourtListener;
2. retrieve matched opinion text;
3. compare nearby quotations with source text;
4. check for explicit page markers such as `*675`;
5. extract the proposition before the citation;
6. rank bounded candidate passages using disclosed lexical scores;
7. report later-citation counts only as context labeled `not_a_citator`.

AutoCite does **not** conclude that a source supports a legal proposition. Candidate passages always require legal judgment. It also does not determine good-law status, controlling authority, precedential weight, or positive/negative treatment. See [`docs/SOURCE_REVIEW.md`](docs/SOURCE_REVIEW.md).

## Jurisdiction profiles

AutoCite includes:

- a curated federal-court priority profile;
- a curated California priority profile;
- addressable profiles for all fifty states.

Generic state profiles identify the jurisdiction but set `verified_overrides=false` and explicitly require current local-rule and state-manual review. AutoCite never imports one state's citation assumptions into another.

## Other MCP tools

| Tool | Purpose |
|---|---|
| `get_jurisdiction_profile` | Return federal, California, or safe generic state priorities. |
| `list_jurisdiction_profiles` | List federal and all fifty state profiles. |
| `get_citation_guidance` | Return a compact rule playbook for a mode and source type. |
| `check_citations` | Audit a document and return structured issues. |
| `get_citation_graph` | Inspect authorities, occurrences, relationships, and resolutions. |
| `resolve_short_form` | Resolve short forms or return bounded ambiguous candidates. |
| `get_rule_coverage` | List tested partial and unsupported rule/source families. |
| `get_rule_context` | Retrieve source-attributed approved local rule summaries. |
| `fix_citations` | Apply high-confidence mechanical fixes only. |
| `check_single_citation` | Review exactly one recognized citation. |
| `convert_citation` | Convert a recognized citation using only present facts. |
| `generate_citation` | Generate from supplied facts and refuse missing required data. |
| `verify_case_citations` | Normalize and locate U.S. case citations through CourtListener. |
| `explain_issue` | Explain an issue and its mode-specific rule family. |
| `list_capabilities` | Return coverage, limitations, and guardrails. |

## Safe automatic fixes

AutoCite applies only high-confidence mechanical edits, including:

- common reporter abbreviations;
- `U.S.C.` and `C.F.R.` abbreviations;
- section-symbol spacing;
- `Id.` capitalization and punctuation.

It does not invent a reporter, court, year, author, title, page, pincite, date, URL, parenthetical, archive link, or legal treatment.

## Command line

Review text:

```bash
uv run autocite review "See 42 USC §1983."
```

Enable optional local SLM suggestions:

```bash
uv sync --extra slm
uv run autocite review "See 42 USC §1983." --slm
```

SLM suggestions are not applied by default. Even with the application flag, a proposal is eligible only when it exactly agrees with a high-confidence deterministic autofix:

```bash
uv run autocite review "See 42 USC §1983." --slm --apply-slm-fixes
```

Model loading is offline-only by default and never silently downloads weights during document review. Predownload both the base model and adapter, or explicitly pass `--allow-model-download` during a nonconfidential setup run. Ordinary AutoCite review does not import ML packages or load weights. See [`docs/SLM.md`](docs/SLM.md) for CPU, GPU, quantized, offline, privacy, and smoke-test instructions.

Review a DOCX or text PDF:

```bash
uv run autocite review-file brief.docx --jurisdiction california
```

Request source-backed case review:

```bash
COURTLISTENER_TOKEN="..." uv run autocite review-file brief.docx --deep-review
```

Export tracked changes:

```bash
uv run autocite export-docx \
  --original-file original.txt \
  --corrected-file corrected.txt \
  --output autocite-review.docx
```

List jurisdiction profiles:

```bash
uv run autocite jurisdictions
```

Run the deterministic gold evaluation:

```bash
uv run autocite eval --file evals/gold.jsonl
```

## Install and run from a checkout

AutoCite requires Python 3.10 or later.

```bash
uv sync --extra dev
uv run autocite-mcp
```

Hosted mode:

```bash
AUTOCITE_TRANSPORT=streamable-http \
AUTOCITE_HOST=0.0.0.0 \
AUTOCITE_PORT=8000 \
uv run autocite-mcp
```

Endpoints:

```text
GET  /health
MCP  /mcp
```

## Docker

```bash
docker build -t autocite-mcp .
docker run --rm -p 8000:8000 autocite-mcp
```

A public deployment without authentication is appropriate only for demonstrations or nonconfidential text. Production multi-user hosting must add OAuth or an authenticated reverse proxy, tenant isolation, TLS, request limits, and log redaction. See [`docs/SECURITY.md`](docs/SECURITY.md).

## Evaluation and release

The repository includes a JSONL gold corpus and deterministic evaluator for extraction, correction, quotation comparison, and passage ranking. CI runs on Python 3.10, 3.12, and 3.13, builds distributions, runs the evaluator, and verifies that the third-party reference corpus is absent from the wheel.

A GitHub Release workflow is prepared for PyPI Trusted Publishing. Publication will work only after the repository owner configures the PyPI project or pending publisher and the GitHub `pypi` environment.

## Accuracy boundaries

“Mechanically clean” means no remaining issue detected within AutoCite's supported deterministic checks. “Source verified” means retrieved text directly contains identified metadata, language, or an explicit page marker. Neither means:

- the authority is current or good law;
- the authority supports the proposition;
- the source is controlling;
- a quotation is fair in context;
- a pincite is correct in the official source;
- every local court or journal rule has been applied.

AutoCite labels those questions for legal or editorial review rather than pretending to resolve them.

## Development

```bash
uv run ruff check src tests
uv run pytest
uv run python -m py_compile src/autocite_mcp/*.py
uv run autocite eval --file evals/gold.jsonl
uv build
```

## Licensing and references

AutoCite is MIT licensed. The repository's `reference/` directory contains public and separately licensed materials governed by [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Those files are excluded from the wheel and source distribution and are never returned through MCP resources.

AutoCite is not affiliated with or endorsed by the publishers or editors of *The Bluebook*, CourtListener, or Free Law Project. It does not replace official manuals, controlling rules, licensed citators, source verification, or professional judgment.
