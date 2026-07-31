import type { Editor } from "@tiptap/react";
import {
  Check,
  ChevronDown,
  CloudOff,
  Command,
  FileCheck2,
  Redo2,
  Save,
  Undo2,
} from "lucide-react";

import { useWorkspace } from "../store/useWorkspace";

interface TitleBarProps {
  editor: Editor | null;
}

export function TitleBar({ editor }: TitleBarProps) {
  const documentTitle = useWorkspace((state) => state.documentTitle);
  const updateTitle = useWorkspace((state) => state.updateTitle);
  const saveNow = useWorkspace((state) => state.saveNow);
  const saveStatus = useWorkspace((state) => state.saveStatus);
  const connectionStatus = useWorkspace((state) => state.connectionStatus);
  const setCommandPaletteOpen = useWorkspace((state) => state.setCommandPaletteOpen);
  const runReview = useWorkspace((state) => state.runReview);
  const isReviewing = useWorkspace((state) => state.isReviewing);
  const activeSession = useWorkspace((state) => state.activeSession);

  return (
    <header className="title-bar" data-tauri-drag-region>
      <div className="quick-access" aria-label="Quick access toolbar">
        <span className="app-mark" aria-label="AutoCite">
          A<span>C</span>
        </span>
        <IconButton
          label="Save"
          onClick={() => void saveNow()}
          disabled={!activeSession || saveStatus === "saving"}
        >
          <Save size={15} />
        </IconButton>
        <IconButton
          label="Undo"
          onClick={() => editor?.chain().focus().undo().run()}
          disabled={!editor?.can().undo()}
        >
          <Undo2 size={15} />
        </IconButton>
        <IconButton
          label="Redo"
          onClick={() => editor?.chain().focus().redo().run()}
          disabled={!editor?.can().redo()}
        >
          <Redo2 size={15} />
        </IconButton>
        <span className="quick-divider" />
        <button className="quick-more" aria-label="Customize quick access toolbar">
          <ChevronDown size={13} />
        </button>
      </div>

      <div className="title-center" data-tauri-drag-region>
        {activeSession ? (
          <input
            className="document-title-input"
            value={documentTitle}
            aria-label="Document title"
            spellCheck={false}
            onChange={(event) => updateTitle(event.target.value)}
            onBlur={() => void saveNow()}
          />
        ) : (
          <span className="document-title-placeholder">AutoCite</span>
        )}
        <SaveIndicator status={saveStatus} />
      </div>

      <div className="title-actions">
        <button
          className="command-search"
          onClick={() => setCommandPaletteOpen(true)}
          aria-label="Search commands"
        >
          <Command size={15} />
          <span>Search tools and commands</span>
          <kbd>⌘K</kbd>
        </button>
        <span
          className={`local-status ${connectionStatus === "ready" ? "is-ready" : ""}`}
          title="AutoCite processes ordinary reviews locally"
        >
          <CloudOff size={14} />
          Local
        </span>
        <button
          className="primary-review-button"
          onClick={() => void runReview()}
          disabled={!activeSession || isReviewing}
        >
          {isReviewing ? <FileCheck2 className="spin-soft" size={15} /> : <FileCheck2 size={15} />}
          {isReviewing ? "Reviewing…" : "Review citations"}
        </button>
      </div>
    </header>
  );
}

function SaveIndicator({ status }: { status: string }) {
  if (status === "saving") return <span className="save-indicator">Saving…</span>;
  if (status === "dirty") return <span className="save-indicator">Unsaved</span>;
  if (status === "conflict") return <span className="save-indicator is-warning">Conflict</span>;
  if (status === "error") return <span className="save-indicator is-warning">Save failed</span>;
  return (
    <span className="save-indicator is-saved">
      <Check size={12} /> Saved
    </span>
  );
}

function IconButton({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button className="quick-button" aria-label={label} title={label} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}
