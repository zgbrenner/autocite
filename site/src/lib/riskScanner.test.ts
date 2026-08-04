import { describe, expect, it } from "vitest";

import { scanCitationRisk } from "./riskScanner";

describe("Citation Risk Scan", () => {
  it("normalizes supported federal citation mechanics", () => {
    const result = scanCitationRisk("See 42 USC §1983 and 17 CFR § 240.10b-5.");
    expect(result.correctedText).toBe("See 42 U.S.C. § 1983 and 17 C.F.R. § 240.10b-5.");
    expect(result.counts["usc-abbreviation"]).toBe(1);
    expect(result.counts["cfr-abbreviation"]).toBe(1);
    expect(result.counts["section-spacing"]).toBe(2);
  });

  it("normalizes citation-shaped Id. without rewriting ordinary prose", () => {
    const result = scanCitationRisk("Smith controls. id at 42. The Freudian id. Id represents instinct.");
    expect(result.correctedText).toBe(
      "Smith controls. Id. at 42. The Freudian id. Id represents instinct.",
    );
    expect(result.counts["id-short-form"]).toBe(1);
  });

  it("returns exact source spans for every mechanical preview", () => {
    const source = "See 42 USC §1983.";
    const result = scanCitationRisk(source);
    for (const finding of result.findings) {
      expect(source.slice(finding.start, finding.end)).toBe(finding.original);
    }
  });

  it("keeps clean or empty input unchanged", () => {
    expect(scanCitationRisk("").correctedText).toBe("");
    expect(scanCitationRisk("See 42 U.S.C. § 1983.").findings).toHaveLength(0);
  });

  it("never includes pasted text in the share summary", () => {
    const secret = "Privileged Project Marigold analysis cites 42 USC §1983.";
    const result = scanCitationRisk(secret);
    expect(result.shareSummary).not.toContain("Project Marigold");
    expect(result.shareSummary).not.toContain("42 USC");
    expect(result.shareSummary).toContain("No document text is included");
  });
});
