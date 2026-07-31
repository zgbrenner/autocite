import {
  AlertTriangle,
  Check,
  CheckCheck,
  ChevronRight,
  CircleHelp,
  ExternalLink,
  FileCheck2,
  Filter,
  Info,
  SearchCheck,
  ShieldCheck,
  X,
} from "lucide-react";
import { useMemo } from "react";

import { issueExcerpt, scrollToText } from "../lib/document";
import { useWorkspace } from "../store/useWorkspace";
import type { ApplicationIssue, DecisionState, ReviewFilter } from "../types";

const filters: { id: ReviewFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "safe", label: "Safe fixes" },
  { id: "attention", label: "Needs review" },
  { id: "accepted", label: "Accepted" },
  { id: "rejected", label: "Rejected" },
];

export function ReviewPane() {
  const active = useWorkspace((state) => state.activeSession);
  const documentText = useWorkspace((state) => state.documentText);
  const selectedIssueId = useWorkspace((state) => state.selectedIssueId);
  const selectIssue = useWorkspace((state) => state.selectIssue);
  const reviewFilter = useWorkspace((state) => state.reviewFilter);
  const setReviewFilter = useWorkspace((state) => state.setReviewFilter);
  const setPaneVisibility = useWorkspace((state) => state.setPaneVisibility);
  const setEvidenceDrawerOpen = useWorkspace((state) => state.setEvidenceDrawerOpen);
  const decideIssue = useWorkspace((state) => state.decideIssue);
  const applyAllSafe = useWorkspace((state) => state.applyAllSafe);
  const runReview = useWorkspace((state) => state.runReview);
  const isReviewing = useWorkspace((state) => state.isReviewing);

  const issues = active?.latest_review?.application_issues ?? [];
  const decisionMap = useMemo(
    () => new Map(active?.decisions.map((decision) => [decision.issue_id, decision.state]) ?? []),
    [active?.decisions],
  );
  const filtered = issues.filter((issue) => matchesFilter(issue, decisionMap.get(issue.id), reviewFilter));
  const safeCount = issues.filter((issue) => issue.safe_to_apply && decisionMap.get(issue.id) !== "accepted").length;
  const attentionCount = issues.filter((issue) => !issue.safe_to_apply && !decisionMap.has(issue.id)).length;

  return (
    <aside className="review-pane" aria-label="Citation review">
      <header className="pane-header review-pane-header">
        <div>
          <strong>Citation review</strong>
          <span>{issues.length ? `${issues.length} items` : "Ready when you are"}</span>
        </div>
        <button aria-label="Close review pane" onClick={() => setPaneVisibility("review", false)}><X size={15} /></button>
      </header>

      {!active ? (
        <EmptyReview
          icon={<FileCheck2 />}
          title="Open a document"
          detail="Citation findings and source evidence will appear here."
        />
      ) : !active.latest_review ? (
        <div className="review-empty-wrap">
          <EmptyReview
            icon={<SearchCheck />}
            title="Review this document"
            detail="AutoCite checks citations without rewriting the surrounding prose."
          />
          <button className="review-call-to-action" onClick={() => void runReview()} disabled={isReviewing}>
            <FileCheck2 size={16} /> {isReviewing ? "Reviewing citations…" : "Start citation review"}
          </button>
          <ReviewGuarantees />
        </div>
      ) : (
        <>
          <section className="review-summary">
            <div><ShieldCheck size={17} /><span><strong>{safeCount}</strong> safe fixes</span></div>
            <div><AlertTriangle size={17} /><span><strong>{attentionCount}</strong> need judgment</span></div>
            <button onClick={() => void applyAllSafe()} disabled={safeCount === 0}><CheckCheck size={15} /> Apply safe fixes</button>
          </section>

          <div className="review-filter-row">
            <Filter size={14} />
            <select value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value as ReviewFilter)} aria-label="Filter review items">
              {filters.map((filter) => <option value={filter.id} key={filter.id}>{filter.label}</option>)}
            </select>
            <button title="Run review again" onClick={() => void runReview()} disabled={isReviewing}><SearchCheck size={14} /></button>
          </div>

          <div className="issue-list">
            {filtered.map((issue, index) => (
              <IssueCard
                key={issue.id}
                issue={issue}
                index={index}
                documentText={documentText}
                decision={decisionMap.get(issue.id)}
                selected={selectedIssueId === issue.id}
                onSelect={() => {
                  selectIssue(issue.id);
                  scrollToText(issue.original);
                }}
                onDecision={(decision) => void decideIssue(issue.id, decision)}
                onEvidence={() => {
                  selectIssue(issue.id);
                  setEvidenceDrawerOpen(true);
                }}
              />
            ))}
            {filtered.length === 0 ? (
              <EmptyReview icon={<Check />} title="Nothing in this view" detail="Choose another filter or run the review again." />
            ) : null}
          </div>
        </>
      )}
    </aside>
  );
}

function IssueCard({
  issue,
  index,
  documentText,
  decision,
  selected,
  onSelect,
  onDecision,
  onEvidence,
}: {
  issue: ApplicationIssue;
  index: number;
  documentText: string;
  decision?: DecisionState;
  selected: boolean;
  onSelect: () => void;
  onDecision: (decision: DecisionState) => void;
  onEvidence: () => void;
}) {
  const excerpt = issueExcerpt(documentText, issue.start, issue.end);
  return (
    <article className={`issue-card ${selected ? "is-selected" : ""} ${decision ? `is-${decision}` : ""}`}>
      <button className="issue-card-main" onClick={onSelect}>
        <span className={`issue-type-icon ${issue.safe_to_apply ? "is-safe" : "is-attention"}`}>
          {issue.safe_to_apply ? <ShieldCheck size={15} /> : <AlertTriangle size={15} />}
        </span>
        <span className="issue-card-copy">
          <span className="issue-eyebrow">{issue.issue_code?.replaceAll("_", " ") || `Review item ${index + 1}`}</span>
          <strong>{issue.message || (issue.safe_to_apply ? "Mechanical citation correction" : "Citation requires review")}</strong>
          <span className="issue-excerpt">{excerpt.before}<mark>{excerpt.target || issue.original}</mark>{excerpt.after}</span>
        </span>
        <ChevronRight size={15} />
      </button>

      {issue.replacement ? (
        <div className="suggested-change">
          <span className="change-label">Suggested</span>
          <del>{issue.original}</del>
          <span className="change-arrow">→</span>
          <ins>{issue.replacement}</ins>
        </div>
      ) : null}

      <div className="issue-card-footer">
        <span className={`correction-level ${issue.safe_to_apply ? "safe" : "attention"}`}>
          {issue.safe_to_apply ? "Safe automatic fix" : humanizeLevel(issue.correction_level)}
        </span>
        <button className="evidence-button" onClick={onEvidence}><Info size={13} /> Evidence</button>
        <span className="issue-action-spacer" />
        <button className="reject-button" onClick={() => onDecision("rejected")} disabled={decision === "rejected"}>Reject</button>
        <button className="accept-button" onClick={() => onDecision("accepted")} disabled={!issue.safe_to_apply || decision === "accepted"} title={!issue.safe_to_apply ? "This item requires human judgment and cannot be auto-applied" : undefined}>
          <Check size={13} /> Accept
        </button>
      </div>
    </article>
  );
}

function matchesFilter(issue: ApplicationIssue, decision: DecisionState | undefined, filter: ReviewFilter): boolean {
  if (filter === "safe") return issue.safe_to_apply && decision !== "accepted";
  if (filter === "attention") return !issue.safe_to_apply && !decision;
  if (filter === "accepted") return decision === "accepted";
  if (filter === "rejected") return decision === "rejected";
  return true;
}

function humanizeLevel(level: string): string {
  return level.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function EmptyReview({ icon, title, detail }: { icon: React.ReactNode; title: string; detail: string }) {
  return <div className="empty-review"><span>{icon}</span><strong>{title}</strong><p>{detail}</p></div>;
}

function ReviewGuarantees() {
  return (
    <div className="review-guarantees">
      <span><ShieldCheck size={14} /><span><strong>Deterministic edits</strong> only when the source span still matches.</span></span>
      <span><CircleHelp size={14} /><span><strong>Ambiguity is labeled</strong> instead of silently guessed.</span></span>
      <span><ExternalLink size={14} /><span><strong>Source review is separate</strong> and requires explicit activation.</span></span>
    </div>
  );
}
