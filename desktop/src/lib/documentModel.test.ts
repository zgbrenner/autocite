import { describe, expect, it } from "vitest";

import {
  applyAcceptedReviewItems,
  calculateDocumentStats,
  normalizeDocumentTitle,
  type ReviewItem,
} from "./documentModel";

const reviewItems: ReviewItem[] = [
  {
    itemId: "statute",
    code: "STATUTE_ABBREVIATION",
    start: 4,
    end: 10,
    original: "42 USC",
    suggestion: "42 U.S.C.",
    message: "Use the standard code abbreviation.",
    severity: "warning",
    confidence: "high",
    correctionLevel: "safe_auto_fix",
    provenance: "deterministic_logic",
    decision: "accepted",
  },
  {
    itemId: "manual",
    code: "PIN_CITE_REVIEW",
    start: 13,
    end: 17,
    original: "1983",
    suggestion: null,
    message: "Confirm the pinpoint citation.",
    severity: "warning",
    confidence: "medium",
    correctionLevel: "review_required",
    provenance: "deterministic_logic",
    decision: "pending",
  },
];

describe("document model", () => {
  it("applies only accepted text edits without shifting later offsets", () => {
    expect(applyAcceptedReviewItems("See 42 USC § 1983.", reviewItems)).toBe(
      "See 42 U.S.C. § 1983.",
    );
  });

  it("refuses a stale review span instead of changing unrelated prose", () => {
    expect(() =>
      applyAcceptedReviewItems("See 28 USC § 1331.", reviewItems),
    ).toThrow(/no longer matches/i);
  });

  it("calculates stable word, character, and page estimates", () => {
    expect(calculateDocumentStats("One two three.\n\nFour five.")).toEqual({
      words: 5,
      characters: 26,
      estimatedPages: 1,
    });
  });

  it("normalizes unsafe or blank filenames without erasing the title", () => {
    expect(normalizeDocumentTitle("  Motion: Smith/Johnson?  ")).toBe(
      "Motion Smith Johnson",
    );
    expect(normalizeDocumentTitle("   ")).toBe("Untitled document");
  });
});
