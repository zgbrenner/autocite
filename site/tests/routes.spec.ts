import { expect, test } from "@playwright/test";

const routes = [
  "/",
  "/download/",
  "/citation-risk-scan/",
  "/bluebook-citation-checker/",
  "/legal-citation-checker/",
  "/law-students/",
  "/law-review/",
  "/law-firms/",
  "/privacy/",
  "/methodology/",
  "/compare/generic-ai/",
  "/faq/",
  "/guides/",
  "/guides/bluepages-vs-whitepages/",
  "/press/",
  "/changelog/",
];

test("indexable routes have one H1 and complete metadata", async ({ page }) => {
  const titles = new Set<string>();
  const canonicals = new Set<string>();

  for (const route of routes) {
    await page.goto(route);
    await expect(page.locator("h1")).toHaveCount(1);
    const title = await page.title();
    const description = await page.locator('meta[name="description"]').getAttribute("content");
    const canonical = await page.locator('link[rel="canonical"]').getAttribute("href");
    expect(title.length, `${route} title`).toBeGreaterThan(10);
    expect(description?.length ?? 0, `${route} description`).toBeGreaterThan(69);
    expect(canonical, `${route} canonical`).toMatch(/^https:\/\//u);
    expect(titles.has(title), `${route} duplicate title`).toBe(false);
    expect(canonicals.has(canonical ?? ""), `${route} duplicate canonical`).toBe(false);
    titles.add(title);
    canonicals.add(canonical ?? "");
  }
});
