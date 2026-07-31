import {
  AlertCircle,
  CheckCircle2,
  FileCheck2,
  PanelLeft,
  PanelRight,
  WifiOff,
} from "lucide-react";

import { countCharacters, countWords } from "../lib/document";
import { useWorkspace } from "../store/useWorkspace";

export function StatusBar({ selectedText }: { selectedText: string }) {
  const active = useWorkspace((state) => state.activeSession);
  const documentText = useWorkspace((state) => state.documentText);
  const saveStatus = useWorkspace((state) => state.saveStatus);
  const zoom = useWorkspace((state) => state.zoom);
  const setZoom = useWorkspace((state) => state.setZoom);
  const showNavigation = useWorkspace((state) => state.showNavigation);
  const showReviewPane = useWorkspace((state) => state.showReviewPane);
  const setPaneVisibility = useWorkspace((state) => state.setPaneVisibility);
  const mode = useWorkspace((state) => state.mode);
  const jurisdiction = useWorkspace((state) => state.jurisdiction);

  const words = countWords(documentText);
  const selectionWords = countWords(selectedText);
  const selectionCharacters = countCharacters(selectedText);

  return (
    <footer className="status-bar">
      <div className="status-left">
        <span>Page 1</span>
        <span>{words.toLocaleString()} words</span>
        {selectedText ? <span>{selectionWords} selected · {selectionCharacters} characters</span> : null}
        <span>{active?.citation_count ?? 0} detected citations</span>
        <span className="status-mode"><FileCheck2 size={13} /> {mode === "auto" ? "Auto mode" : mode} · {jurisdiction}</span>
      </div>
      <div className="status-right">
        <SaveStatus status={saveStatus} />
        <span className="offline-badge"><WifiOff size={12} /> Local</span>
        <button className={showNavigation ? "is-active" : ""} onClick={() => setPaneVisibility("navigation", !showNavigation)} aria-label="Toggle navigation pane"><PanelLeft size={14} /></button>
        <button className={showReviewPane ? "is-active" : ""} onClick={() => setPaneVisibility("review", !showReviewPane)} aria-label="Toggle review pane"><PanelRight size={14} /></button>
        <button className="zoom-symbol" onClick={() => setZoom(zoom - 10)} aria-label="Zoom out">−</button>
        <input aria-label="Document zoom" type="range" min="70" max="180" value={zoom} onChange={(event) => setZoom(Number(event.target.value))} />
        <button className="zoom-symbol" onClick={() => setZoom(zoom + 10)} aria-label="Zoom in">+</button>
        <button className="zoom-value" onClick={() => setZoom(100)}>{zoom}%</button>
      </div>
    </footer>
  );
}

function SaveStatus({ status }: { status: string }) {
  if (status === "saved") return <span className="status-save is-saved"><CheckCircle2 size={12} /> Saved</span>;
  if (status === "saving") return <span className="status-save">Saving…</span>;
  if (status === "dirty") return <span className="status-save">Unsaved changes</span>;
  return <span className="status-save is-error"><AlertCircle size={12} /> {status === "conflict" ? "Save conflict" : "Save error"}</span>;
}
