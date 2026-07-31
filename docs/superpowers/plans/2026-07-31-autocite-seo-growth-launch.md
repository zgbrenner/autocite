# AutoCite SEO and Growth Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a truthful, high-converting, search-optimized AutoCite launch site with a private browser demo, growth assets, and automated quality gates.

**Architecture:** Add an isolated Astro static site under `site/`. Shared layout and SEO helpers own metadata and structured data; content pages consume focused section components; the Citation Risk Scan imports a pure TypeScript rules engine that is independently tested. GitHub Actions build and audit the site without changing AutoCite's Python or Tauri runtime.

**Tech Stack:** Astro 5, TypeScript, CSS, Vitest, Playwright, Node 22, GitHub Actions.

## Global Constraints

- Position AutoCite as the private legal citation checker.
- The desktop-app download is the primary conversion event.
- The Citation Risk Scan runs entirely in the browser and never transmits pasted text.
- Do not claim complete Bluebook compliance, guaranteed accuracy, good-law checking, proposition support, or third-party endorsement.
- Use a true-white, deep-ink, restrained-blue legal-editorial visual system.
- Avoid fake testimonials, fake logos, unsupported metrics, generic AI gradients, and repetitive card grids.
- Cloudflare Pages deployment remains opt-in until production secrets and a domain are configured.

---

### Task 1: Static-site foundation and SEO contracts

**Files:**
- Create: `site/package.json`
- Create: `site/astro.config.mjs`
- Create: `site/tsconfig.json`
- Create: `site/src/config.ts`
- Create: `site/src/lib/seo.ts`
- Create: `site/src/lib/seo.test.ts`
- Create: `site/src/layouts/SiteLayout.astro`
- Create: `site/src/styles/global.css`

**Interfaces:**
- Produces: `SITE`, `buildCanonical(pathname)`, `buildSoftwareApplicationJsonLd()`, and `<SiteLayout title description pathname jsonLd>`.

- [ ] Write tests asserting canonical normalization, unique page-title composition, and truthful SoftwareApplication JSON-LD.
- [ ] Run `npm test -- seo.test.ts` and confirm failure because helpers do not exist.
- [ ] Implement the helpers and shared layout with canonical, Open Graph, Twitter, JSON-LD, favicon, and accessible skip navigation.
- [ ] Add the design tokens, responsive type scale, buttons, typography, document-preview primitives, and reduced-motion rules.
- [ ] Run unit tests and `npm run typecheck`.

### Task 2: Conversion-focused homepage and shared navigation

**Files:**
- Create: `site/src/components/Header.astro`
- Create: `site/src/components/Footer.astro`
- Create: `site/src/components/ProductReviewDemo.astro`
- Create: `site/src/components/ProofStrip.astro`
- Create: `site/src/components/DownloadCta.astro`
- Create: `site/src/pages/index.astro`
- Create: `site/tests/home.spec.ts`

**Interfaces:**
- Consumes: `SiteLayout` and `SITE.releaseUrl`.
- Produces: homepage sections and stable labels used by Playwright.

- [ ] Write Playwright assertions for the H1, primary download link, secondary risk-scan link, privacy proof, supported-file claims, limitations link, and mobile navigation.
- [ ] Run the homepage test and confirm the route is missing.
- [ ] Implement the homepage with hero, semantic product-review demo, three-step workflow, safeguards section, audience paths, methodology proof, FAQ preview, and final download CTA.
- [ ] Run desktop and mobile homepage tests.

### Task 3: Browser-only Citation Risk Scan

**Files:**
- Create: `site/src/lib/riskScanner.ts`
- Create: `site/src/lib/riskScanner.test.ts`
- Create: `site/src/components/RiskScanner.astro`
- Create: `site/src/pages/citation-risk-scan/index.astro`
- Create: `site/tests/risk-scan.spec.ts`

**Interfaces:**
- Produces: `scanCitationRisk(input: string): ScanResult` where `ScanResult` includes sanitized counts, corrected text, and exact mechanical findings.

- [ ] Write unit tests for USC, CFR, section-spacing, `Id.`, clean text, prose false positives, empty input, and share-summary redaction.
- [ ] Run tests and confirm failure because the scanner is missing.
- [ ] Implement bounded regex rules with exact source spans and no invented data.
- [ ] Build the interactive scanner with sample text, local-only status, clear input, copy corrected text, native share fallback, and a download CTA.
- [ ] Write a Playwright test that blocks all network requests after page load, runs the scan, and verifies the result contains no hidden outbound request or pasted-text share payload.
- [ ] Run unit and browser tests.

### Task 4: Search-intent landing pages

**Files:**
- Create: `site/src/components/AudiencePage.astro`
- Create: `site/src/components/FaqList.astro`
- Create: `site/src/pages/bluebook-citation-checker/index.astro`
- Create: `site/src/pages/legal-citation-checker/index.astro`
- Create: `site/src/pages/law-students/index.astro`
- Create: `site/src/pages/law-review/index.astro`
- Create: `site/src/pages/law-firms/index.astro`
- Create: `site/src/pages/privacy/index.astro`
- Create: `site/src/pages/methodology/index.astro`
- Create: `site/src/pages/compare/generic-ai/index.astro`
- Create: `site/src/pages/faq/index.astro`
- Create: `site/tests/routes.spec.ts`

**Interfaces:**
- Consumes: `AudiencePage`, `FaqList`, `DownloadCta`, and `SiteLayout`.

- [ ] Write a route matrix test checking one H1, unique titles, canonical links, descriptions, and truthful calls to action.
- [ ] Run the test and confirm the routes are missing.
- [ ] Implement each page around distinct search intent, avoiding duplicate doorway copy.
- [ ] Include clear capability boundaries and internal links to methodology, privacy, scanner, and download pages.
- [ ] Run the route matrix test.

### Task 5: Download, press, changelog, and educational content hub

**Files:**
- Create: `site/src/pages/download/index.astro`
- Create: `site/src/pages/press/index.astro`
- Create: `site/src/pages/changelog/index.astro`
- Create: `site/src/content.config.ts`
- Create: `site/src/content/guides/*.md`
- Create: `site/src/pages/guides/index.astro`
- Create: `site/src/pages/guides/[...slug].astro`
- Create: `site/src/pages/rss.xml.ts`

**Interfaces:**
- Produces: `guides` Astro content collection and RSS feed.

- [ ] Write tests that require at least six guides, valid publication dates, descriptions, canonical routes, and Article JSON-LD.
- [ ] Run tests and confirm failure.
- [ ] Implement release guidance for Windows, macOS, Linux, MCP, and source users without promising installers that are not published.
- [ ] Add educational guides covering Bluepages vs. Whitepages, citation checker privacy, citation hallucinations, `Id.` and short forms, law-review workflows, and Word document review.
- [ ] Add press facts, logos represented as text/SVG brand assets, founder boilerplate, and truthful product description.
- [ ] Run content tests and build.

### Task 6: Crawlability, structured data, and automated SEO audit

**Files:**
- Create: `site/public/robots.txt`
- Create: `site/public/llms.txt`
- Create: `site/public/site.webmanifest`
- Create: `site/public/favicon.svg`
- Create: `site/src/pages/404.astro`
- Create: `site/scripts/audit-seo.mjs`
- Create: `site/scripts/audit-seo.test.mjs`

**Interfaces:**
- Produces: `npm run audit:seo` exit status and a machine-readable report at `site/reports/seo-audit.json`.

- [ ] Write audit fixture tests for missing titles, duplicate titles, missing canonicals, broken internal links, invalid JSON-LD, missing `llms.txt`, and noindex leakage.
- [ ] Run tests and confirm failure.
- [ ] Implement the static-output crawler and JSON report.
- [ ] Run `npm run build` then `npm run audit:seo`.

### Task 7: Launch kit and repository positioning

**Files:**
- Create: `docs/marketing/POSITIONING.md`
- Create: `docs/marketing/SEO-KEYWORDS.md`
- Create: `docs/marketing/LAUNCH-KIT.md`
- Create: `docs/marketing/CONTENT-CALENDAR.md`
- Create: `docs/marketing/DIRECTORY-SUBMISSIONS.md`
- Create: `docs/marketing/MEDIA-AND-ASSETS.md`
- Modify: `README.md`

**Interfaces:**
- Produces: approved public messaging hierarchy and channel-specific launch drafts.

- [ ] Write a repository copy test asserting the first README screen contains the category, privacy promise, download CTA, scanner CTA, and accuracy boundary.
- [ ] Run the test and confirm failure against the existing engineer-first README.
- [ ] Rewrite the README opening while retaining detailed technical documentation below it.
- [ ] Add differentiated launch drafts for Product Hunt, Hacker News, LinkedIn, X, Reddit communities, email, press outreach, and directory listings.
- [ ] Add a 30-day content calendar tied to the guide cluster and release cadence.
- [ ] Run repository copy tests and a claim-consistency scan.

### Task 8: CI, Cloudflare-compatible build, and release integration

**Files:**
- Create: `.github/workflows/site-ci.yml`
- Create: `.github/workflows/site-deploy.yml`
- Create: `.github/dependabot.yml` entries for `site/` if not already present
- Modify: `.github/workflows/desktop-release.yml` or active release workflow to expose release metadata without coupling release success to the site.

**Interfaces:**
- Produces: `site-dist` build artifact and opt-in Cloudflare Pages deployment.

- [ ] Add workflow-contract tests for Node 22, `npm ci`, unit tests, typecheck, build, Playwright, SEO audit, artifact upload, least-privilege permissions, and deployment secret guards.
- [ ] Run the tests and confirm missing workflow behavior.
- [ ] Implement CI and deployment workflows.
- [ ] Run YAML parsing and workflow-contract tests.

### Task 9: Full verification and pull request

**Files:**
- Modify only files required by failing verification.

- [ ] Run `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, `npm run audit:seo`, and `npm run test:e2e` from `site/`.
- [ ] Run existing Python CI tests affected by README and workflow changes.
- [ ] Inspect desktop and mobile screenshots for layout, typography, contrast, navigation, scanner states, and overflow.
- [ ] Verify the scanner while blocking post-load network requests.
- [ ] Confirm no unsupported claims, fake proof, pasted legal text in share payloads, or production analytics dependency.
- [ ] Open a non-draft PR with verification evidence and do not merge until required checks pass.
