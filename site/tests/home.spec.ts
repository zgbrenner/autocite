import { expect, test } from "@playwright/test";

test("homepage communicates the private citation checker offer", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "The private legal citation checker that leaves your writing alone.",
    }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Download AutoCite free" })).toHaveAttribute(
    "href",
    /github\.com\/zgbrenner\/autocite\/releases\/latest/u,
  );
  await expect(page.getByRole("link", { name: "Try the private risk scan" })).toHaveAttribute(
    "href",
    "/citation-risk-scan/",
  );
  await expect(page.getByText("No application telemetry", { exact: true })).toBeVisible();
  await expect(page.getByText(/DOCX, searchable PDF, Markdown, or TXT/iu)).toBeVisible();
  await expect(page.getByRole("link", { name: "Read the methodology" })).toBeVisible();
});

test("navigation remains usable at the active viewport", async ({ page }, testInfo) => {
  await page.goto("/");
  if (testInfo.project.name === "mobile") {
    const menu = page.getByText("Menu", { exact: true });
    await expect(menu).toBeVisible();
    await menu.click();
    await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toBeVisible();
  } else {
    await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  }
});
