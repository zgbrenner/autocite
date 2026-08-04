import {
  Check,
  CheckCircle,
  Funnel,
  Info,
  Play,
  Warning,
  X,
} from "@phosphor-icons/react";
import { useMemo, useState } from "react";

import type { ReviewDecision, ReviewItem } from "../lib/documentModel";

interface ReviewPaneProps {
  items: ReviewItem[];
  loading: boolean;
  error: string | null;
  onRunReview(): void;
  onDecision(itemId: string, decision: ReviewDecision): void;
}

type ReviewFilter = "all" | ReviewDecision;

function confidenceLabel(value: string): string {
  return value.length === 0 ? "Unspecified confidence" : `${value} confidence`;
}

export function ReviewPane({
  items,
  loading,
  error,
  onRunReview,
  onDecision,
}: ReviewPaneProps) {
  const [filter, setFilter] = useState<ReviewFilter>("all");
  const filtered = useMemo(
    () => (filter === "all" ? items : items.filter((item) => item.decision === filter)),
    [filter, items],
  );
  const accepted = items.filter((item) => item.decision === "accepted").length;
  const pending = items.filter((item) => item.decision === "pending").length;
  const rejected = items.filter((item) => item.decision === "rejected").length;

  return (
    <aside className="review-pane" aria-label="AutoCite review pane">
      <header className="review-heading">
        <div>
          <p>Document review</p>
          <h2>AutoCite review</h2>
        </div>
        <button
          type="button"
          className="primary-review-button"
          aria-label="Run AutoCite review"
          disabled={loading}
          onClick={onRunReview}
        >
          <Play size={17} weight="fill" />
          {loading ? "Reviewing" : "Review"}
        </button>
      </header>

      <div className="review-summary" aria-label="Review summary">
        <div>
          <strong>{accepted}</strong>
          <span>Applied</span>
        </div>
        <div>
          <strong>{pending}</strong>
          <span>Needs review</span>
        </div>
        <div>
          <strong>{rejected}</strong>
          <span>Dismissed</span>
        </div>
      </div>

      <div className="review-filters" role="tablist" aria-label="Filter review items">
        <Funnel size={15} aria-hidden="true" />
        {(["all", "pending", "accepted", "rejected"] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={filter === value}
            className={filter === value ? "is-active" : ""}
            onClick={() => setFilter(value)}
          >
            {value === "all"
              ? "All"
              : value === "pending"
                ? "Open"
                : value === "accepted"
                  ? "Applied"
                  : "Dismissed"}
          </button>
        ))}
      </div>

      <div className="review-list">
        {error !== null && (
          <div className="review-message is-error" role="alert">
            <Warning size={20} />
            <div>
              <strong>Review could not finish</strong>
              <p>{error}</p>
            </div>
          </div>
        )}
        {loading && (
          <div className="review-loading" aria-live="polite">
            <span className="spinner" />
            <div>
              <strong>Reviewing citations</strong>
              <p>Deterministic checks stay in control of every proposed edit.</p>
            </div>
          </div>
        )}
        {!loading && error === null && items.length === 0 && (
          <div className="review-empty">
            <CheckCircle size={36} weight="duotone" />
            <h3>Ready to review</h3>
            <p>
              AutoCite checks citation form, short forms, source context, and safe
              mechanical corrections without rewriting your prose.
            </p>
            <button
              type="button"
              aria-label="Start AutoCite review"
              onClick={onRunReview}
            >
              Run AutoCite review
            </button>
          </div>
        )}
        {!loading && items.length > 0 && filtered.length === 0 && (
          <div className="review-empty compact">
            <Info size={26} />
            <p>No review items are in this category.</p>
          </div>
        )}
        {filtered.map((item) => (
          <article
            key={item.itemId}
            className={`review-card decision-${item.decision}`}
          >
            <div className="review-card-topline">
              <span className={`severity-dot severity-${item.severity}`} />
              <strong>{item.code.replaceAll("_", " ")}</strong>
              <span>{confidenceLabel(item.confidence)}</span>
            </div>
            <p className="review-card-message">{item.message}</p>
            <div className="citation-change" aria-label="Suggested citation change">
              <code>{item.original}</code>
              {item.suggestion !== null && (
                <>
                  <span aria-hidden="true">→</span>
                  <code>{item.suggestion}</code>
                </>
              )}
            </div>
            <div className="review-card-meta">
              <span>{item.provenance.replaceAll("_", " ")}</span>
              {item.rule !== null && item.rule !== undefined && <span>{item.rule}</span>}
            </div>
            <div className="review-card-actions">
              <button
                type="button"
                aria-label="Accept suggestion"
                className={item.decision === "accepted" ? "is-selected" : ""}
                disabled={item.suggestion === null}
                onClick={() => onDecision(item.itemId, "accepted")}
              >
                <Check size={16} />
                Accept
              </button>
              <button
                type="button"
                aria-label="Reject suggestion"
                className={item.decision === "rejected" ? "is-selected" : ""}
                onClick={() => onDecision(item.itemId, "rejected")}
              >
                <X size={16} />
                Reject
              </button>
              {item.decision !== "pending" && (
                <button
                  type="button"
                  aria-label="Reset decision"
                  onClick={() => onDecision(item.itemId, "pending")}
                >
                  Reset
                </button>
              )}
            </div>
          </article>
        ))}
      </div>

      <footer className="review-footer">
        <Info size={15} />
        <span>Source text stays local unless source verification is requested.</span>
      </footer>
    </aside>
  );
}
