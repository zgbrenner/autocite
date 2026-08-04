import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type {
  ApplicationAdapter,
  ReviewDecisionRequest,
  UpdateDocumentRequest,
} from "./services/applicationAdapter";

function createAdapter(): ApplicationAdapter {
  return {
    health: vi.fn(async () => ({ status: "ok", localFirst: true })),
    listDocuments: vi.fn(async () => ({
      items: [
        {
          sessionId: "doc-1",
          title: "Motion to dismiss",
          sourceFormat: "markdown",
          fileName: "motion.md",
          mode: "bluepages",
          jurisdiction: "federal",
          documentType: "brief",
          revision: 1,
          contentSha256: "abc",
          reviewRevision: null,
          hasReview: false,
          createdAt: "2026-07-31T00:00:00Z",
          updatedAt: "2026-07-31T00:00:00Z",
        },
      ],
      nextCursor: null,
    })),
    getDocument: vi.fn(async () => ({
      sessionId: "doc-1",
      title: "Motion to dismiss",
      text: "See 42 USC § 1983.",
      sourceFormat: "markdown",
      fileName: "motion.md",
      mimeType: "text/markdown",
      mode: "bluepages",
      jurisdiction: "federal",
      documentType: "brief",
      revision: 1,
      contentSha256: "abc",
      reviewRevision: null,
      hasReview: false,
      createdAt: "2026-07-31T00:00:00Z",
      updatedAt: "2026-07-31T00:00:00Z",
    })),
    createDocument: vi.fn(),
    updateDocument: vi.fn(async (request: UpdateDocumentRequest) => ({
      sessionId: request.sessionId,
      title: request.title ?? "Motion to dismiss",
      text: request.text,
      sourceFormat: "markdown",
      fileName: "motion.md",
      mimeType: "text/markdown",
      mode: request.mode ?? "bluepages",
      jurisdiction: request.jurisdiction ?? "federal",
      documentType: request.documentType ?? "brief",
      revision: request.expectedRevision + 1,
      contentSha256: "def",
      reviewRevision: null,
      hasReview: false,
      createdAt: "2026-07-31T00:00:00Z",
      updatedAt: "2026-07-31T00:01:00Z",
    })),
    importDocument: vi.fn(),
    reviewDocument: vi.fn(async () => ({
      job: { jobId: "job-1", status: "completed" },
      summary: { itemCount: 1, acceptedCount: 1, pendingCount: 0, rejectedCount: 0 },
    })),
    getReviewItems: vi.fn(async () => ({
      sessionId: "doc-1",
      documentRevision: 1,
      reviewRevision: 1,
      items: [
        {
          itemId: "issue-1",
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
          decision: "accepted" as const,
        },
      ],
      offset: 0,
      limit: 100,
      total: 1,
      nextOffset: null,
    })),
    setReviewDecision: vi.fn(async (request: ReviewDecisionRequest) => ({
      itemId: request.itemId,
      decision: request.decision,
    })),
    exportDocument: vi.fn(),
    openDocumentFile: vi.fn(async () => null),
    saveExportFile: vi.fn(async () => null),
  };
}

describe("AutoCite desktop workspace", () => {
  it("renders a Word-like ribbon, document canvas, library, and review pane", async () => {
    render(<App adapter={createAdapter()} />);

    expect(await screen.findByDisplayValue("Motion to dismiss")).toBeVisible();
    expect(screen.getByRole("tab", { name: "Home" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: "Insert" })).toBeVisible();
    expect(screen.getByRole("tab", { name: "Review" })).toBeVisible();
    expect(
      await screen.findByRole("textbox", { name: "Document editor" }),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "AutoCite review" })).toBeVisible();
    expect(
      screen.getByRole("button", { name: /Motion to dismiss/i }),
    ).toBeVisible();
  });

  it("runs a review and persists an explicit reject decision", async () => {
    const user = userEvent.setup();
    const adapter = createAdapter();
    render(<App adapter={adapter} />);

    await screen.findByDisplayValue("Motion to dismiss");
    await user.click(screen.getByRole("button", { name: "Run AutoCite review" }));

    expect(await screen.findByText("Use the standard code abbreviation.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Reject suggestion" }));

    await waitFor(() => {
      expect(adapter.setReviewDecision).toHaveBeenCalledWith({
        sessionId: "doc-1",
        itemId: "issue-1",
        decision: "rejected",
        expectedRevision: 1,
      });
    });
  });
});
