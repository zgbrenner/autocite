import {
  Binary,
  CheckCircle2,
  Copy,
  FileSearch,
  Fingerprint,
  Gauge,
  ShieldCheck,
  X,
} from "lucide-react";
import { useMemo } from "react";

import { issueExcerpt } from "../lib/document";
import { useWorkspace } from "../store/useWorkspace";

export function EvidenceDrawer() {
  const open = useWorkspace((state) => state.evidenceDrawerOpen);
  const setOpen = useWorkspace((state) => state.setEvidenceDrawerOpen);
  const active = useWorkspace((state) => state.activeSession);
  const documentText = useWorkspace((state) => state.documentText);
  const selectedIssueId = useWorkspace((state) => state.selectedIssueId);
  const issue = useMemo(
    () => active?.latest_review?.application_issues?.find((item) => item.id === selectedIssueId),
    [active?.latest_review?.application_issues, selectedIssueId],
  );

  if (!open) return null;
  const excerpt = issue
    ? issueExcerpt(documentText, issue.start, issue.end, 180)
    : null;
  const reduction = active?.latest_review?.context_reduction;

  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={() => setOpen(false)}>
      <aside
        className="evidence-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Issue evidence"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <span className="drawer-kicker">AutoCite evidence</span>
            <h2>{issue?.issue_code?.replaceAll("_", " ") || "Review provenance"}</h2>
          </div>
          <button aria-label="Close evidence" onClick={() => setOpen(false)}><X size={17} /></button>
        </header>

        {!issue ? (
          <div className="drawer-empty">Select a review item to inspect its evidence, span, and safety boundary.</div>
        ) : (
          <div className="drawer-scroll">
            <section className="evidence-hero">
              <span className={issue.safe_to_apply ? "is-safe" : "is-attention"}>
                {issue.safe_to_apply ? <ShieldCheck size={18} /> : <FileSearch size={18} />}
              </span>
              <div>
                <strong>{issue.safe_to_apply ? "Deterministic safe fix" : "Human review required"}</strong>
                <p>{issue.message || "AutoCite found a citation issue at this exact source location."}</p>
              </div>
            </section>

            <EvidenceSection title="Exact source span" icon={<Fingerprint size={15} />}>
              <div className="source-span-card">
                <p>{excerpt?.before}<mark>{excerpt?.target || issue.original}</mark>{excerpt?.after}</p>
                <dl>
                  <div><dt>Start</dt><dd>{issue.start}</dd></div>
                  <div><dt>End</dt><dd>{issue.end}</dd></div>
                  <div><dt>Characters</dt><dd>{issue.end - issue.start}</dd></div>
                </dl>
                <button onClick={() => void navigator.clipboard.writeText(issue.original)}><Copy size={13} /> Copy original</button>
              </div>
            </EvidenceSection>

            {issue.replacement ? (
              <EvidenceSection title="Proposed change" icon={<CheckCircle2 size={15} />}>
                <div className="evidence-diff">
                  <div><span>Original</span><del>{issue.original}</del></div>
                  <div><span>Replacement</span><ins>{issue.replacement}</ins></div>
                </div>
              </EvidenceSection>
            ) : null}

            <EvidenceSection title="Decision boundary" icon={<Gauge size={15} />}>
              <dl className="evidence-metadata">
                <div><dt>Correction level</dt><dd>{issue.correction_level.replaceAll("_", " ")}</dd></div>
                <div><dt>Provenance</dt><dd>{issue.provenance || "deterministic engine"}</dd></div>
                <div><dt>Automatic application</dt><dd>{issue.safe_to_apply ? "Eligible while span matches" : "Blocked"}</dd></div>
              </dl>
              <p className="evidence-explanation">
                {issue.safe_to_apply
                  ? "AutoCite will apply this edit only if the current document still contains the exact original text at the recorded span."
                  : "This item is surfaced for judgment. AutoCite will not silently invent missing facts, authority, treatment, or proposition support."}
              </p>
            </EvidenceSection>

            {reduction ? (
              <EvidenceSection title="Context routing" icon={<Binary size={15} />}>
                <dl className="evidence-metadata">
                  <div><dt>Strategy</dt><dd>{reduction.strategy || "deterministic legal"}</dd></div>
                  <div><dt>Full document used for rules</dt><dd>{reduction.used_for_deterministic_review === false ? "Yes" : "Unknown"}</dd></div>
                  <div><dt>Reversible</dt><dd>{reduction.reversible ? "Yes" : "No"}</dd></div>
                  <div><dt>Context savings</dt><dd>{reduction.metrics ? `${Math.round(reduction.metrics.savings_ratio * 100)}%` : "Not measured"}</dd></div>
                </dl>
                <p className="evidence-explanation">Context reduction is measured for bounded downstream tasks. It does not replace full-document citation extraction or deterministic validation.</p>
              </EvidenceSection>
            ) : null}

            <details className="raw-evidence">
              <summary>Structured issue record</summary>
              <pre>{JSON.stringify(issue.raw ?? issue, null, 2)}</pre>
            </details>
          </div>
        )}
      </aside>
    </div>
  );
}

function EvidenceSection({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return <section className="evidence-section"><h3>{icon}{title}</h3>{children}</section>;
}
