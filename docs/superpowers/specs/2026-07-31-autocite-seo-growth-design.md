# AutoCite SEO and Growth Launch Design

## Product category

AutoCite will own the phrase **private legal citation checker**. The primary promise is:

> Fix Bluebook citation problems without rewriting your document or uploading confidential legal work.

The primary conversion event is a desktop-app download from GitHub Releases. The primary acquisition event is completion of a browser-only Citation Risk Scan.

## Audiences

1. Law students and journal editors who need Bluepages and Whitepages help.
2. Judicial clerks and litigators who review briefs, motions, and memoranda.
3. Solo and small-firm lawyers who need an affordable privacy-first workflow.
4. Legal technologists evaluating deterministic, auditable alternatives to generic AI rewriting.

## Claims and boundaries

The public site may claim that AutoCite is local-first, open source, telemetry-free at the application layer, source-document preserving, deterministic-first, and capable of reviewing supported legal citation patterns in DOCX, PDF, Markdown, and TXT workflows.

The site must not claim complete Bluebook compliance, guaranteed accuracy, good-law checking, proposition support, controlling-authority analysis, or endorsement by The Bluebook, CourtListener, Free Law Project, any court, school, journal, or law firm.

Any accuracy statement must point to a published evaluation artifact or describe only the supported deterministic test corpus.

## Information architecture

The launch surface will be an Astro static site under `site/` with these indexable routes:

- `/` product homepage
- `/download/` release and installation guidance
- `/bluebook-citation-checker/`
- `/legal-citation-checker/`
- `/law-students/`
- `/law-review/`
- `/law-firms/`
- `/privacy/`
- `/methodology/`
- `/compare/generic-ai/`
- `/citation-risk-scan/`
- `/guides/` and individual educational guides
- `/press/`
- `/changelog/`
- `/faq/`

The homepage must lead with the private legal citation checker category, show a product workflow, explain deterministic safeguards, and provide one dominant download action plus one secondary browser-demo action.

## Citation Risk Scan

The scanner runs entirely in the browser and uses a deliberately bounded deterministic rule set. It may normalize:

- `USC` to `U.S.C.` when citation-shaped context is present;
- `CFR` to `C.F.R.` when citation-shaped context is present;
- spacing around the section symbol;
- common `Id.` capitalization and punctuation patterns.

The scanner must:

- never transmit input;
- visibly state that it is a limited preview, not full AutoCite review;
- return exact before-and-after spans;
- explain each mechanical change;
- refuse to invent missing citation facts;
- produce a shareable summary containing counts and categories only, never pasted legal text.

## Visual system

The site will use a clean legal-editorial system: true-white and deep-ink surfaces, restrained blue accents, serif display headings, sans-serif interface text, thin rules, document-paper motifs, and a product screenshot-style citation review panel built from semantic HTML and CSS. It must avoid fake law-firm logos, fake testimonials, unsupported metrics, generic AI gradients, and repetitive card grids.

## SEO system

Every indexable page requires a unique title, description, canonical URL, Open Graph metadata, Twitter metadata, semantic heading structure, internal links, and JSON-LD appropriate to the route. The build must emit `sitemap-index.xml`, `robots.txt`, RSS, and `llms.txt`.

The keyword clusters are:

- Bluebook citation checker
- legal citation checker
- private legal AI
- offline legal citation checker
- Bluepages checker
- Whitepages checker
- law review citation checker
- legal brief citation checker
- citation hallucination checker
- Bluebook checker for Word

Pages must answer real search intent rather than repeat keyword variants.

## Growth loops

1. Search guide to Citation Risk Scan to download.
2. Product download to first successful review to shareable privacy-safe result card.
3. Law-review editor adoption to journal-team recommendation.
4. GitHub release to changelog, launch post, and reusable social assets.

## Launch materials

The repository will contain truthful, ready-to-edit launch drafts for Product Hunt, Hacker News, LinkedIn, X, Reddit, email, directory submissions, press outreach, and a 30-day content calendar. Drafts must use placeholders only for dates, URLs, and founder quotes that cannot be known from the repository.

## Technical delivery

- Astro 5 static output with TypeScript.
- No runtime backend and no analytics dependency by default.
- Lightweight client JavaScript only for the scanner, mobile navigation, copy, and share actions.
- Unit tests for scanner behavior and metadata helpers.
- Playwright smoke tests for core routes and scanner privacy behavior.
- SEO validation script for titles, descriptions, canonicals, structured data, sitemap, robots, `llms.txt`, and broken internal links.
- GitHub Actions for lint, typecheck, unit tests, build, Playwright, SEO audit, and Cloudflare Pages-compatible artifact upload.
- Cloudflare Pages deployment remains opt-in until repository secrets and the production domain are configured.

## Success criteria

The work is complete when:

1. All listed routes build as static HTML.
2. The scanner completes locally with network requests blocked.
3. Every indexable page passes the metadata and internal-link audit.
4. Desktop and mobile Playwright smoke tests pass.
5. The README and repository description lead with the marketable category without weakening accuracy boundaries.
6. Launch assets are present and factually consistent with shipped functionality.
7. The branch is reviewed through a pull request and is not merged while required checks are failing.
