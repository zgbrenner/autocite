import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { auditDirectory } from "./audit-seo.mjs";

const roots = [];

async function fixture(html, extra = {}) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "autocite-seo-"));
  roots.push(root);
  const dist = path.join(root, "dist");
  await fs.mkdir(dist, { recursive: true });
  await fs.writeFile(path.join(dist, "index.html"), html);
  const required = {
    "robots.txt": "User-agent: *\nAllow: /\n",
    "llms.txt": "# AutoCite\n",
    "site.webmanifest": "{}",
    "favicon.svg": "<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>",
    "rss.xml": "<rss></rss>",
    "sitemap-index.xml": "<sitemapindex></sitemapindex>",
    ...extra,
  };
  for (const [filename, content] of Object.entries(required)) {
    const target = path.join(dist, filename);
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, content);
  }
  return dist;
}

afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => fs.rm(root, { recursive: true, force: true })));
});

describe("SEO audit", () => {
  it("passes a complete static page", async () => {
    const dist = await fixture(`<!doctype html><html><head>
      <title>Private legal citation checker | AutoCite</title>
      <meta name="description" content="AutoCite reviews supported legal citation mechanics locally while preserving legal prose and publishing clear limitations for every automated correction.">
      <link rel="canonical" href="https://example.com/">
      <script type="application/ld+json">{"@context":"https://schema.org","@type":"SoftwareApplication"}</script>
      </head><body><h1>Private legal citation checker</h1><a href="/rss.xml">RSS</a></body></html>`);
    const report = await auditDirectory(dist);
    expect(report.errors).toEqual([]);
  });

  it("reports broken links, missing metadata, invalid schema, and noindex leakage", async () => {
    const dist = await fixture(`<!doctype html><html><head>
      <title></title><meta name="robots" content="noindex">
      <script type="application/ld+json">{broken}</script>
      </head><body><h1>One</h1><h1>Two</h1><a href="/missing/">Missing</a></body></html>`);
    const report = await auditDirectory(dist);
    expect(report.errors.join("\n")).toMatch(/missing title/iu);
    expect(report.errors.join("\n")).toMatch(/missing meta description/iu);
    expect(report.errors.join("\n")).toMatch(/missing absolute HTTPS canonical/iu);
    expect(report.errors.join("\n")).toMatch(/expected one H1/iu);
    expect(report.errors.join("\n")).toMatch(/unexpected noindex/iu);
    expect(report.errors.join("\n")).toMatch(/invalid JSON-LD/iu);
    expect(report.errors.join("\n")).toMatch(/broken internal link/iu);
  });
});
