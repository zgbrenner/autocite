import { expect, test } from "@playwright/test";

const routes = [
  "/",
  "/bluebook-citation-checker/",
  "/legal-citation-checker/",
  "/law-students/",
  "/law-review/",
  "/law-firms/",
  "/privacy/",
  "/methodology/",
  "/compare/generic-ai/",
  "/press/",
];

const prohibited = [
  "100% accurate",
  "guaranteed accuracy",
  "complete Bluebook compliance",
  "checks good law",
  "replaces legal judgment",
  "official Bluebook",
];

test("public product pages do not make unsupported claims", async ({ page }) => {
  for (const route of routes) {
    await page.goto(route);
    const text = (await page.locator("body").innerText()).toLowerCase();
    for (const phrase of prohibited) {
      expect(text, `${route} contains ${phrase}`).not.toContain(phrase.toLowerCase());
    }
  }
});
