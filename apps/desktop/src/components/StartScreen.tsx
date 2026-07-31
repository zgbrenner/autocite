import {
  ArrowRight,
  BookOpenCheck,
  FilePlus2,
  FileSearch,
  FileText,
  LockKeyhole,
  Scale,
  ShieldCheck,
} from "lucide-react";

import { formatRelativeTime } from "../lib/document";
import { useWorkspace } from "../store/useWorkspace";

export function StartScreen({ onNew, onOpen }: { onNew: () => void; onOpen: () => void }) {
  const sessions = useWorkspace((state) => state.sessions);
  const openSession = useWorkspace((state) => state.openSession);

  return (
    <main className="start-screen">
      <section className="start-hero">
        <div className="start-brand">
          <span className="start-logo">AC</span>
          <span><strong>AutoCite</strong><small>Legal citation editor</small></span>
        </div>
        <div className="start-copy">
          <span className="start-kicker"><Scale size={15} /> Write first. Review precisely.</span>
          <h1>A real word processor built around trustworthy citechecking.</h1>
          <p>Draft and edit your full document, review every citation in context, accept deterministic fixes, inspect evidence, and export clean Word or PDF files.</p>
          <div className="start-actions">
            <button className="start-primary" onClick={onNew}><FilePlus2 size={18} /> New document</button>
            <button className="start-secondary" onClick={onOpen}><FileSearch size={18} /> Open document</button>
          </div>
          <span className="supported-formats"><FileText size={14} /> Word, searchable PDF, Markdown, and plain text</span>
        </div>
        <div className="start-preview" aria-hidden="true">
          <div className="preview-window">
            <div className="preview-ribbon"><span /><span /><span /><span /></div>
            <div className="preview-body">
              <div className="preview-page">
                <b>MEMORANDUM OF POINTS AND AUTHORITIES</b>
                <i />
                <i />
                <i className="short" />
                <p><span /> <mark /> <span /></p>
                <i />
                <i className="medium" />
              </div>
              <div className="preview-review"><strong>Citation review</strong><span className="safe" /><span /><span className="attention" /></div>
            </div>
          </div>
        </div>
      </section>

      <section className="start-content">
        <div className="recent-section">
          <header><div><h2>Recent documents</h2><p>Stored locally on this computer</p></div>{sessions.length ? <button onClick={onOpen}>Browse files <ArrowRight size={14} /></button> : null}</header>
          {sessions.length ? (
            <div className="recent-grid">
              {sessions.slice(0, 8).map((session) => (
                <button key={session.id} className="recent-card" onClick={() => void openSession(session.id)}>
                  <span className="recent-file-icon">{session.source_format.slice(0, 1).toUpperCase()}</span>
                  <span className="recent-card-copy"><strong>{session.title}</strong><small>{session.word_count.toLocaleString()} words · {session.citation_count} citations</small><small>{formatRelativeTime(session.updated_at)}</small></span>
                  <ArrowRight size={15} />
                </button>
              ))}
            </div>
          ) : (
            <div className="recent-empty"><BookOpenCheck size={28} /><strong>Your documents will appear here</strong><p>Start a blank draft or import an existing legal document. AutoCite preserves the original separately from your working revision.</p></div>
          )}
        </div>

        <aside className="trust-panel">
          <span className="trust-kicker">Designed for consequential work</span>
          <h2>Transparent by default</h2>
          <div className="trust-item"><LockKeyhole size={18} /><span><strong>Local document sessions</strong><small>Ordinary editing and citation review stay on your computer.</small></span></div>
          <div className="trust-item"><ShieldCheck size={18} /><span><strong>Conservative automatic edits</strong><small>Only exact, deterministic safe fixes can be applied automatically.</small></span></div>
          <div className="trust-item"><BookOpenCheck size={18} /><span><strong>Evidence is inspectable</strong><small>Rules, source spans, and unresolved judgment calls remain separately labeled.</small></span></div>
        </aside>
      </section>
    </main>
  );
}
