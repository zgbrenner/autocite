import { expect, test } from "@playwright/test";


test("opens, reviews, and navigates the AutoCite word processor", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByLabel("Document title")).toHaveValue("Motion to dismiss");
  await expect(page.getByRole("tab", { name: "Home" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("textbox", { name: "Document editor" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "AutoCite review" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Motion to dismiss" })).toBeVisible();

  await page.screenshot({
    path: "test-results/autocite-workspace.png",
    fullPage: true,
  });

  await page.getByRole("button", { name: "Run AutoCite review" }).click();
  await expect(
    page.getByText("Use the standard United States Code abbreviation."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Reject suggestion" }).click();
  await expect(page.getByRole("button", { name: "Reset decision" })).toBeVisible();

  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog", { name: "Command palette" })).toBeVisible();
  await expect(page.getByLabel("Search commands")).toBeFocused();
  await page.getByLabel("Search commands").fill("compare");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Original", { exact: true })).toBeVisible();
  await expect(page.getByText("Reviewed", { exact: true })).toBeVisible();
});


test("keeps essential controls keyboard reachable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByLabel("Document title")).toHaveValue("Motion to dismiss");

  await page.keyboard.press("Control+k");
  const palette = page.getByRole("dialog", { name: "Command palette" });
  await expect(palette).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(palette).toBeHidden();

  await page.getByRole("tab", { name: "Review" }).click();
  await expect(page.getByLabel("Mode")).toBeVisible();
  await expect(page.getByLabel("Jurisdiction")).toBeVisible();
});
