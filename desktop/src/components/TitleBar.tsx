import {
  CloudSlash,
  Command,
  FloppyDisk,
  LockKey,
} from "@phosphor-icons/react";

interface TitleBarProps {
  title: string;
  onTitleChange(title: string): void;
  onSave(): void;
  saveState: "saved" | "saving" | "unsaved" | "error";
  backendStatus: "checking" | "ready" | "preview" | "offline";
  onOpenCommands(): void;
}

function saveLabel(state: TitleBarProps["saveState"]): string {
  if (state === "saving") return "Saving";
  if (state === "unsaved") return "Unsaved changes";
  if (state === "error") return "Save failed";
  return "Saved locally";
}

export function TitleBar({
  title,
  onTitleChange,
  onSave,
  saveState,
  backendStatus,
  onOpenCommands,
}: TitleBarProps) {
  return (
    <header className="title-bar">
      <div className="brand-lockup" aria-label="AutoCite">
        <div className="brand-mark" aria-hidden="true">
          A
        </div>
        <strong>AutoCite</strong>
      </div>
      <div className="quick-access">
        <button type="button" aria-label="Save document" onClick={onSave}>
          <FloppyDisk size={18} />
        </button>
      </div>
      <input
        className="document-title-input"
        aria-label="Document title"
        value={title}
        spellCheck={false}
        onChange={(event) => onTitleChange(event.currentTarget.value)}
      />
      <div className="title-status">
        <span className={`save-state state-${saveState}`}>{saveLabel(saveState)}</span>
        <span className={`backend-state state-${backendStatus}`}>
          {backendStatus === "ready" ? (
            <LockKey size={15} weight="fill" />
          ) : backendStatus === "preview" ? (
            <CloudSlash size={15} />
          ) : (
            <span className="status-indicator" />
          )}
          {backendStatus === "ready"
            ? "Local engine"
            : backendStatus === "preview"
              ? "Preview engine"
              : backendStatus === "checking"
                ? "Connecting"
                : "Engine offline"}
        </span>
        <button
          type="button"
          className="command-trigger"
          aria-label="Open command palette"
          onClick={onOpenCommands}
        >
          <Command size={16} />
          <span>Commands</span>
          <kbd>Ctrl K</kbd>
        </button>
      </div>
    </header>
  );
}
