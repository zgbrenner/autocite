import { expect, test } from "@playwright/test";

test("citation scan runs locally and shares no pasted text", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: async (payload: ShareData) => {
        (window as typeof window & { __sharedPayload?: ShareData }).__sharedPayload = payload;
      },
    });
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: async () => undefined },
    });
  });

  const networkAfterLoad: string[] = [];
  await page.goto("/citation-risk-scan/");
  page.on("request", (request) => {
    if (["fetch", "xhr", "websocket"].includes(request.resourceType())) {
      networkAfterLoad.push(request.url());
    }
  });

  const secret = "Privileged Project Marigold analysis cites 42 USC §1983. Smith controls. id at 172.";
  await page.getByLabel("Paste a short citation sample").fill(secret);
  await page.getByRole("button", { name: "Scan citation mechanics" }).click();

  await expect(page.locator("[data-output]")).toContainText("42 U.S.C. § 1983");
  await expect(page.locator("[data-output]")).toContainText("Id. at 172");
  await expect(page.locator("[data-count]")).toContainText("issue");
  expect(networkAfterLoad).toEqual([]);

  await page.getByRole("button", { name: "Share private summary" }).click();
  const payload = await page.evaluate(
    () => (window as typeof window & { __sharedPayload?: ShareData }).__sharedPayload,
  );
  expect(payload?.text).toContain("No document text is included");
  expect(payload?.text).not.toContain("Project Marigold");
  expect(payload?.text).not.toContain("42 USC");
});
