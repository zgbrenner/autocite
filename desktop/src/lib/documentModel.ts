export type ReviewDecision = "accepted" | "rejected" | "pending";

export interface ReviewItem {
  itemId: string;
  code: string;
  start: number;
  end: number;
  original: string;
  suggestion: string | null;
  message: string;
  severity: string;
  confidence: string;
  correctionLevel: string;
  provenance: string;
  decision: ReviewDecision;
  rule?: string | null;
  missingFacts?: string[];
}

export interface DocumentStats {
  words: number;
  characters: number;
  estimatedPages: number;
}

export function calculateDocumentStats(text: string): DocumentStats {
  const trimmed = text.trim();
  const words = trimmed.length === 0 ? 0 : trimmed.split(/\s+/u).length;
  return {
    words,
    characters: text.length,
    estimatedPages: Math.max(1, Math.ceil(words / 500)),
  };
}

export function normalizeDocumentTitle(title: string): string {
  const forbidden = new Set('<>:"/\\|?*');
  const sanitized = Array.from(title.normalize("NFKC"), (character) => {
    const codePoint = character.codePointAt(0) ?? 0;
    return codePoint < 32 || forbidden.has(character) ? " " : character;
  }).join("");
  const normalized = sanitized
    .replace(/\s+/gu, " ")
    .trim()
    .replace(/[. ]+$/gu, "")
    .slice(0, 160)
    .trim();
  return normalized || "Untitled document";
}

export function applyAcceptedReviewItems(
  originalText: string,
  items: readonly ReviewItem[],
): string {
  const accepted = items
    .filter(
      (item) => item.decision === "accepted" && item.suggestion !== null,
    )
    .toSorted((left, right) => right.start - left.start || right.end - left.end);

  let previousStart = originalText.length;
  let result = originalText;
  for (const item of accepted) {
    if (item.start < 0 || item.end <= item.start || item.end > originalText.length) {
      throw new Error(`Review item ${item.itemId} has an invalid source span.`);
    }
    if (item.end > previousStart) {
      throw new Error("Accepted review items overlap and cannot be applied safely.");
    }
    if (originalText.slice(item.start, item.end) !== item.original) {
      throw new Error(
        `Review item ${item.itemId} no longer matches the current document.`,
      );
    }
    result = `${result.slice(0, item.start)}${item.suggestion ?? ""}${result.slice(item.end)}`;
    previousStart = item.start;
  }
  return result;
}
