export type ScanRuleId =
  | "usc-abbreviation"
  | "cfr-abbreviation"
  | "section-spacing"
  | "id-short-form";

export interface ScanFinding {
  id: string;
  ruleId: ScanRuleId;
  label: string;
  explanation: string;
  start: number;
  end: number;
  original: string;
  replacement: string;
}

export interface ScanResult {
  inputLength: number;
  correctedText: string;
  findings: ScanFinding[];
  counts: Record<ScanRuleId, number>;
  shareSummary: string;
}

interface CandidateFinding extends Omit<ScanFinding, "id"> {}

const LABELS: Record<ScanRuleId, { label: string; explanation: string }> = {
  "usc-abbreviation": {
    label: "U.S.C. abbreviation",
    explanation: "Uses the standard federal code abbreviation without adding missing citation facts.",
  },
  "cfr-abbreviation": {
    label: "C.F.R. abbreviation",
    explanation: "Uses the standard federal regulation abbreviation without changing the title or section number.",
  },
  "section-spacing": {
    label: "Section-symbol spacing",
    explanation: "Normalizes spacing around an existing section symbol.",
  },
  "id-short-form": {
    label: "Id. short form",
    explanation: "Normalizes citation-shaped Id. capitalization and punctuation only when followed by a pinpoint marker.",
  },
};

function collectPattern(
  text: string,
  ruleId: ScanRuleId,
  pattern: RegExp,
  replacementFor: (match: RegExpExecArray) => string,
): CandidateFinding[] {
  const findings: CandidateFinding[] = [];
  for (const match of text.matchAll(pattern)) {
    if (match.index === undefined) continue;
    const original = match[0];
    const replacement = replacementFor(match);
    if (original === replacement) continue;
    findings.push({
      ruleId,
      label: LABELS[ruleId].label,
      explanation: LABELS[ruleId].explanation,
      start: match.index,
      end: match.index + original.length,
      original,
      replacement,
    });
  }
  return findings;
}

function overlaps(left: CandidateFinding, right: CandidateFinding): boolean {
  return left.start < right.end && right.start < left.end;
}

function selectNonOverlapping(findings: CandidateFinding[]): CandidateFinding[] {
  const priority: ScanRuleId[] = [
    "usc-abbreviation",
    "cfr-abbreviation",
    "id-short-form",
    "section-spacing",
  ];
  const sorted = [...findings].sort((a, b) => {
    if (a.start !== b.start) return a.start - b.start;
    return priority.indexOf(a.ruleId) - priority.indexOf(b.ruleId);
  });
  const selected: CandidateFinding[] = [];
  for (const finding of sorted) {
    if (!selected.some((existing) => overlaps(existing, finding))) selected.push(finding);
  }
  return selected;
}

function applyFindings(text: string, findings: CandidateFinding[]): string {
  let corrected = text;
  for (const finding of [...findings].sort((a, b) => b.start - a.start)) {
    if (corrected.slice(finding.start, finding.end) !== finding.original) {
      throw new Error("Citation preview span no longer matches the source text.");
    }
    corrected = `${corrected.slice(0, finding.start)}${finding.replacement}${corrected.slice(finding.end)}`;
  }
  return corrected;
}

function buildShareSummary(findings: ScanFinding[]): string {
  const categories = Array.from(new Set(findings.map((finding) => finding.label)));
  if (findings.length === 0) {
    return "AutoCite's private Citation Risk Scan found no supported mechanical issues in this sample. Full legal review is still required.";
  }
  return `AutoCite's private Citation Risk Scan found ${findings.length} supported mechanical issue${findings.length === 1 ? "" : "s"} across ${categories.length} categor${categories.length === 1 ? "y" : "ies"}. No document text is included in this summary.`;
}

export function scanCitationRisk(input: string): ScanResult {
  const candidates: CandidateFinding[] = [
    ...collectPattern(input, "usc-abbreviation", /\b\d+\s+USC\b/giu, (match) =>
      match[0].replace(/USC/iu, "U.S.C."),
    ),
    ...collectPattern(input, "cfr-abbreviation", /\b\d+\s+CFR\b/giu, (match) =>
      match[0].replace(/CFR/iu, "C.F.R."),
    ),
    ...collectPattern(
      input,
      "id-short-form",
      /(^|[.;:!?]\s+|\n\s*)id\.?(?=\s+(?:at\s+\d|¶\s*\d|§\s*\d))/gimu,
      (match) => `${match[1] ?? ""}Id.`,
    ),
    ...collectPattern(input, "section-spacing", /\s*§\s*/gu, () => " § "),
  ];

  const selected = selectNonOverlapping(candidates);
  const findings: ScanFinding[] = selected.map((finding, index) => ({
    ...finding,
    id: `${finding.ruleId}-${finding.start}-${index}`,
  }));
  const counts: Record<ScanRuleId, number> = {
    "usc-abbreviation": 0,
    "cfr-abbreviation": 0,
    "section-spacing": 0,
    "id-short-form": 0,
  };
  for (const finding of findings) counts[finding.ruleId] += 1;

  return {
    inputLength: input.length,
    correctedText: applyFindings(input, findings),
    findings,
    counts,
    shareSummary: buildShareSummary(findings),
  };
}
