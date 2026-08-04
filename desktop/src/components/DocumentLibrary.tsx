import {
  FilePlus,
  FileText,
  FolderOpen,
  MagnifyingGlass,
} from "@phosphor-icons/react";
import { useDeferredValue, useMemo, useState } from "react";

import type { DocumentSummary } from "../services/applicationAdapter";

interface DocumentLibraryProps {
  documents: DocumentSummary[];
  activeDocumentId: string | null;
  onSelect(sessionId: string): void;
  onNew(): void;
  onOpen(): void;
}

function formatUpdatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently edited";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function DocumentLibrary({
  documents,
  activeDocumentId,
  onSelect,
  onNew,
  onOpen,
}: DocumentLibraryProps) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query.trim().toLocaleLowerCase());
  const filtered = useMemo(
    () =>
      deferredQuery.length === 0
        ? documents
        : documents.filter((document) =>
            [document.title, document.fileName ?? "", document.jurisdiction ?? ""]
              .join(" ")
              .toLocaleLowerCase()
              .includes(deferredQuery),
          ),
    [deferredQuery, documents],
  );

  return (
    <aside className="document-library" aria-label="Document library">
      <div className="library-heading">
        <div>
          <p>Workspace</p>
          <h2>Documents</h2>
        </div>
        <button type="button" aria-label="New document" onClick={onNew}>
          <FilePlus size={19} />
        </button>
      </div>
      <div className="library-actions">
        <button type="button" onClick={onOpen}>
          <FolderOpen size={17} />
          Open file
        </button>
      </div>
      <label className="library-search">
        <MagnifyingGlass size={16} aria-hidden="true" />
        <input
          aria-label="Search documents"
          type="search"
          placeholder="Search documents"
          value={query}
          onChange={(event) => setQuery(event.currentTarget.value)}
        />
      </label>
      <div className="document-list" role="list">
        {filtered.length === 0 ? (
          <div className="library-empty">
            <FileText size={30} />
            <p>No documents match this search.</p>
          </div>
        ) : (
          filtered.map((document) => (
            <div key={document.sessionId} role="listitem">
              <button
                type="button"
                aria-label={`Open ${document.title}`}
                className={`document-row${document.sessionId === activeDocumentId ? " is-active" : ""}`}
                onClick={() => onSelect(document.sessionId)}
              >
                <FileText size={21} weight={document.hasReview ? "fill" : "regular"} />
                <span className="document-row-copy">
                  <strong>{document.title}</strong>
                  <small>{formatUpdatedAt(document.updatedAt)}</small>
                </span>
                {document.hasReview && <span className="review-dot" aria-label="Reviewed" />}
              </button>
            </div>
          ))
        )}
      </div>
      <div className="library-footer">
        <span>{documents.length} local document{documents.length === 1 ? "" : "s"}</span>
        <span>Private by default</span>
      </div>
    </aside>
  );
}
