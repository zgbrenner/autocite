# AutoCite Launch Kit

Replace bracketed dates or URLs only after the production site and release are verified. Keep limitations intact.

## Product Hunt

### Name

AutoCite

### Tagline

The private legal citation checker that leaves your writing alone

### Description

AutoCite reviews supported Bluebook citation mechanics in briefs, motions, memoranda, law-review drafts, and academic legal writing. Standard desktop review runs locally with no application telemetry. It preserves non-citation prose, shows exact issue spans and provenance, applies only bounded mechanical fixes automatically, and leaves source support, good-law status, and other legal judgments to the reviewer.

AutoCite is open source under the MIT License and available as a desktop app, MCP server, and CLI.

### First comment

I built AutoCite because “fix the citations” is a dangerous instruction for a general-purpose model. A fluent system can invent a reporter, court, year, page, parenthetical, or source relationship and make the result look polished.

AutoCite takes the opposite approach: preserve the document, validate the exact span, apply only supported mechanical corrections, and clearly label what remains unresolved.

The browser Citation Risk Scan demonstrates the privacy boundary without uploading pasted text. The full desktop workflow supports DOCX, searchable PDF, Markdown, and TXT.

I would especially value feedback from legal-writing instructors, journal editors, clerks, litigators, and anyone responsible for legal software review.

## Hacker News

### Title

Show HN: AutoCite – a local-first legal citation checker that refuses missing facts

### Body

I built AutoCite, an MIT-licensed legal citation reviewer for Bluepages and Whitepages workflows.

The key design constraint is that the system should not “helpfully” complete citation facts. Automatic changes are limited to supported deterministic mechanics, and every edit is validated against the exact original span before application. Ambiguous short forms return candidates rather than a guessed antecedent.

The desktop workflow is local-first and has no application telemetry. Optional CourtListener source retrieval is explicit and does not make good-law or proposition-support conclusions.

The repo includes the MCP server, CLI, desktop releases, evaluation corpus, coverage artifacts, CI, release manifests, and a browser-only risk scan whose share output contains counts only.

Repository: [URL]
Site: [URL]

I am interested in feedback on the architecture, adversarial citation cases, packaging, and the boundary between deterministic correction and model assistance.

## LinkedIn

Legal citation tools should be judged by what they refuse to do.

I am launching AutoCite, an open-source, local-first legal citation checker designed for briefs, motions, memoranda, law-review drafts, and academic legal writing.

AutoCite preserves non-citation prose, validates exact source spans, applies only supported mechanical fixes automatically, and shows what still requires legal or editorial judgment. Standard desktop review runs locally with no application telemetry.

It does not claim complete Bluebook compliance, determine good-law status, or decide whether an authority supports a proposition. Those are boundaries, not missing marketing features.

The free browser Citation Risk Scan demonstrates the workflow without uploading pasted text, and the complete desktop app is available from GitHub Releases.

[URL]

#LegalTech #LegalWriting #OpenSource #Privacy #LawStudents

## X thread

1/ I built AutoCite: a private legal citation checker that leaves your writing alone. It reviews supported Bluebook mechanics locally instead of asking a general-purpose model to rewrite the document. [URL]

2/ The core rule: never invent a reporter, court, year, page, parenthetical, URL, or legal treatment just because the completion looks plausible.

3/ Every eligible edit points to an exact source span. If the document changed and the span is stale, the correction is rejected rather than landing somewhere else.

4/ Short forms are document relationships, not isolated regex matches. AutoCite builds a conservative citation graph and returns bounded candidates when `Id.` or `supra` is ambiguous.

5/ Standard desktop review is local-first and has no application telemetry. Optional source retrieval is explicit and separately disclosed.

6/ AutoCite does not claim complete Bluebook compliance, good-law checking, or proposition-support conclusions. The limitations are part of the product.

7/ It is MIT licensed, with desktop, MCP, and CLI workflows plus public tests and evaluations. Try the browser-only Citation Risk Scan or download the current release: [URL]

## Reddit: law students

### Title

I built a free, local Bluebook citation checker that does not rewrite your memo

### Body

I built an open-source tool called AutoCite for a narrower second pass on legal citations. It supports Bluepages and Whitepages workflows, keeps standard desktop review local, and does not have application telemetry.

The main design choice is that it will not invent missing reporter, court, year, page, or parenthetical information. It applies only supported mechanical fixes automatically and lists ambiguous or source-dependent questions separately.

It is not a substitute for opening sources, checking pincites, following assignment instructions, or using a citator. Please also follow any school or write-on rules about automated tools.

There is a browser-only limited scan that runs locally, plus desktop releases for full documents. I would appreciate feedback on confusing explanations or citation patterns that should become adversarial tests.

[URL]

## Reddit: legal tech / open source

### Title

AutoCite: MIT-licensed local legal citation review with deterministic edit gates

### Body

AutoCite is a Python/MCP/desktop legal citation reviewer with a deterministic-first correction pipeline, structured DocumentIR, conservative citation graph, revision-safe application state, exact-span edit validation, and optional local model suggestions.

The new launch surface includes an Astro site, browser-only mechanical preview, static SEO audit, Playwright privacy tests, Lighthouse gates, and a truthful marketing contract that fails on prohibited claims.

I am looking for feedback on security boundaries, document parsing, evaluation design, and packaging rather than promotional reactions alone.

Repository: [URL]

## Launch email

**Subject:** AutoCite: private legal citation review without the rewrite

AutoCite is now available as an open-source, local-first legal citation checker.

It reviews supported Bluepages and Whitepages citation mechanics while preserving non-citation prose. Automatic edits require exact, supported mechanical rules, and unresolved source or judgment questions remain visible for review.

Standard desktop review runs locally with no application telemetry. AutoCite supports DOCX, searchable PDF, Markdown, and TXT workflows and is also available through MCP and the command line.

It does not guarantee complete Bluebook compliance, determine good-law status, or replace source verification and professional judgment.

Explore the private browser scan: [URL]
Download the latest release: [URL]
View the source: [URL]

## Press outreach

**Subject:** Open-source private legal citation checker launches with deterministic safety boundaries

I am sharing AutoCite, an open-source legal citation reviewer built for local-first document workflows rather than general-purpose prose generation.

The project may be relevant to your coverage of legal AI reliability, hallucinated authorities, privacy, law-school technology, open-source legal tools, or on-device AI. AutoCite's distinguishing design choices include exact-span edit validation, conservative short-form resolution, published coverage and evaluations, no desktop application telemetry, and explicit refusal to make good-law or proposition-support conclusions.

Press facts and limitations: [URL]
Source repository: [URL]

## Demo sequence

1. Open the homepage and state the category in one sentence.
2. Run the Citation Risk Scan with `See 42 USC §1983. id at 172.`
3. Show that the result changes mechanics only.
4. Use the share action and show that no pasted text appears.
5. Open methodology and privacy.
6. Open the current GitHub release.
7. In the desktop app, import a nonconfidential sample and review one safe issue and one judgment-required issue.
8. End on the explicit limitations, not an inflated accuracy claim.

## Launch-day checklist

- Verify production canonical URL and sitemap.
- Verify current release artifacts and checksums.
- Replace all bracketed URLs.
- Confirm the Tauri interface is not described as shipped unless its release is public.
- Capture desktop and mobile screenshots.
- Post the launch announcement from the founder account.
- Respond to technical and legal-boundary questions directly.
- Convert valid criticism into public issues or adversarial tests.
- Do not purchase fake votes, comments, stars, reviews, or directory placements.
