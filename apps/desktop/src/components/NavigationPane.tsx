import {
  FilePlus2,
  FileSearch,
  Files,
  Heading,
  MoreHorizontal,
  Search,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

import {
  extractHeadings,
  formatRelativeTime,
  markdownToHtml,
  scrollToText,
} from "../lib/document";
import { useWorkspace } from "../store/useWorkspace";

interface NavigationPaneProps {
  onNew: () => void;
  onOpen: () => void;
}

export function NavigationPane({ onNew, onOpen }: NavigationPaneProps) {
  const tab = useWorkspace((state) => state.navigationTab);
  const setTab = useWorkspace((state) => state.setNavigationTab);
  const setPaneVisibility = useWorkspace((state) => state.setPaneVisibility);
  const sessions = useWorkspace((state) => state.sessions);
  const activeSession = useWorkspace((state) => state.activeSession);
  const documentText = useWorkspace((state) => state.documentText);
  const openSession = useWorkspace((state) => state.openSession);
  const [query, setQuery] = useState("");

  const headings = useMemo(
    () => extractHeadings(markdownToHtml(documentText)),
    [documentText],
  );
  const matches = useMemo(() => findMatches(documentText, query), [documentText, query]);

  return (
    <aside className="navigation-pane" aria-label="Document navigation">
      <header className="pane-header">
        <strong>Navigation</strong>
        <button aria-label="Close navigation pane" onClick={() => setPaneVisibility("navigation", false)}>
          <X size={15} />
        </button>
      </header>
      <div className="pane-tabs" role="tablist">
        <button className={tab === "documents" ? "is-active" : ""} onClick={() => setTab("documents")} title="Documents" aria-label="Documents"><Files size={16} /></button>
        <button className={tab === "headings" ? "is-active" : ""} onClick={() => setTab("headings")} title="Headings" aria-label="Headings"><Heading size={16} /></button>
        <button className={tab === "search" ? "is-active" : ""} onClick={() => setTab("search")} title="Search document" aria-label="Search document"><Search size={16} /></button>
      </div>

      {tab === "documents" ? (
        <div className="navigation-content document-library">
          <div className="library-actions">
            <button onClick={onNew}><FilePlus2 size={15} /> New</button>
            <button onClick={onOpen}><FileSearch size={15} /> Open</button>
          </div>
          <span className="section-caption">Recent documents</span>
          <div className="document-list">
            {sessions.length === 0 ? (
              <EmptyPane title="No documents yet" detail="Create a new draft or open a Word, PDF, Markdown, or text file." />
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  className={`document-list-item ${activeSession?.id === session.id ? "is-active" : ""}`}
                  onClick={() => void openSession(session.id)}
                >
                  <span className="file-glyph">{session.source_format.slice(0, 1).toUpperCase()}</span>
                  <span className="file-copy">
                    <strong>{session.title}</strong>
                    <small>{session.word_count.toLocaleString()} words · {formatRelativeTime(session.updated_at)}</small>
                  </span>
                  <MoreHorizontal className="row-more" size={15} />
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}

      {tab === "headings" ? (
        <div className="navigation-content headings-list">
          <span className="section-caption">Document outline</span>
          {headings.length === 0 ? (
            <EmptyPane title="No headings" detail="Apply heading styles from Home to build a navigable outline." />
          ) : (
            headings.map((heading) => (
              <button
                key={heading.id}
                style={{ paddingLeft: `${12 + (heading.level - 1) * 14}px` }}
                onClick={() => scrollToText(heading.text)}
              >
                {heading.text}
              </button>
            ))
          )}
        </div>
      ) : null}

      {tab === "search" ? (
        <div className="navigation-content search-pane">
          <label className="pane-search">
            <Search size={15} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search this document" autoFocus />
            {query ? <button onClick={() => setQuery("")} aria-label="Clear search"><X size={13} /></button> : null}
          </label>
          <span className="section-caption">{query ? `${matches.length} matches` : "Find in document"}</span>
          <div className="search-results">
            {matches.map((match) => (
              <button key={`${match.index}-${match.text}`} onClick={() => scrollToText(match.text)}>
                <small>Result {match.index + 1}</small>
                <span>{match.contextBefore}<mark>{match.text}</mark>{match.contextAfter}</span>
              </button>
            ))}
            {query && matches.length === 0 ? <EmptyPane title="No matches" detail={`“${query}” was not found in this document.`} /> : null}
          </div>
        </div>
      ) : null}
    </aside>
  );
}

function findMatches(text: string, query: string) {
  const normalized = query.trim();
  if (normalized.length < 2) return [];
  const lowerText = text.toLocaleLowerCase();
  const lowerQuery = normalized.toLocaleLowerCase();
  const results: {
    index: number;
    text: string;
    contextBefore: string;
    contextAfter: string;
  }[] = [];
  let cursor = 0;
  while (results.length < 100) {
    const start = lowerText.indexOf(lowerQuery, cursor);
    if (start < 0) break;
    results.push({
      index: results.length,
      text: text.slice(start, start + normalized.length),
      contextBefore: text.slice(Math.max(0, start - 44), start).replace(/\s+/g, " "),
      contextAfter: text.slice(start + normalized.length, start + normalized.length + 60).replace(/\s+/g, " "),
    });
    cursor = start + Math.max(normalized.length, 1);
  }
  return results;
}

function EmptyPane({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-pane"><strong>{title}</strong><p>{detail}</p></div>;
}
