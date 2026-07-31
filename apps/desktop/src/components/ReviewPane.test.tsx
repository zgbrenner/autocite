import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useWorkspace } from "../store/useWorkspace";
import type { DocumentSession } from "../types";
import { ReviewPane } from "./ReviewPane";

const session: DocumentSession = {
  id: "session-1",
  title: "Motion",
  source_format: "md",
  original_text: "See 42 USC §1983 and Roe v. Wade.",
  working_text: "See 42 USC §1983 and Roe v. Wade.",
  revision: 1,
  status: "reviewed",
  metadata: {},
  decisions: [],
  word_count: 8,
  citation_count: 2,
  created_at: "2026-07-31T00:00:00Z",
  updated_at: "2026-07-31T00:00:00Z",
  latest_review: {
    application_issues: [
      {
        id: "safe",
        start: 4,
        end: 17,
        original: "42 USC §1983",
        replacement: "42 U.S.C. § 1983",
        issue_code: "statute_spacing",
        message: "Normalize the statute citation.",
        correction_level: "safe_auto_fix",
        safe_to_apply: true,
      },
      {
        id: "attention",
        start: 22,
        end: 33,
        original: "Roe v. Wade",
        replacement: null,
        issue_code: "source_review",
        message: "Confirm the proposition and current authority.",
        correction_level: "requires_source_review",
        safe_to_apply: false,
      },
    ],
  },
};

describe("ReviewPane", () => {
  beforeEach(() => {
    useWorkspace.setState({
      activeSession: session,
      documentText: session.working_text,
      selectedIssueId: "safe",
      reviewFilter: "all",
      showReviewPane: true,
    });
  });

  it("separates safe fixes from judgment calls", () => {
    render(<ReviewPane />);

    expect(screen.getByText("1", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("Normalize the statute citation.")).toBeInTheDocument();
    expect(screen.getByText("Confirm the proposition and current authority.")).toBeInTheDocument();
    expect(screen.getByText("Safe automatic fix")).toBeInTheDocument();
    expect(screen.getByTitle("This item requires human judgment and cannot be auto-applied")).toBeDisabled();
  });
});
