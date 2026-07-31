import { describe, expect, it } from "vitest";

import {
  buildCanonical,
  buildPageTitle,
  buildSoftwareApplicationJsonLd,
  normalizePath,
} from "./seo";

describe("SEO helpers", () => {
  it("normalizes canonical paths without preserving tracking parameters", () => {
    expect(normalizePath("guides/privacy?utm_source=test#section")).toBe("/guides/privacy/");
    expect(buildCanonical("/privacy")).toBe("https://zgbrenner.github.io/privacy/");
  });

  it("keeps page titles unique while avoiding a duplicate brand suffix", () => {
    expect(buildPageTitle("Private legal citation checker")).toBe(
      "Private legal citation checker | AutoCite",
    );
    expect(buildPageTitle("AutoCite")).toBe("AutoCite");
  });

  it("publishes only truthful software claims", () => {
    const schema = buildSoftwareApplicationJsonLd();
    expect(schema.applicationCategory).toBe("LegalService");
    expect(schema.isAccessibleForFree).toBe(true);
    expect(schema.featureList).toContain("No application telemetry");
    expect(JSON.stringify(schema)).not.toMatch(/complete Bluebook|guaranteed|good law/iu);
  });
});
