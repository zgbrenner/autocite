import type { Editor } from "@tiptap/react";
import {
  CheckCheck,
  Command,
  FileDiff,
  FileDown,
  FilePlus2,
  FileSearch,
  FileText,
  PanelLeft,
  PanelRight,
  Save,
  SearchCheck,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { useWorkspace } from "../store/useWorkspace";
import type { CommandItem, ExportFormat } from "../types";

interface CommandPaletteProps {
  editor: Editor | null;
  onNew: () => void;
  onOpen: () => void;
  onExport: (format: ExportFormat) => void;
}

export function CommandPalette({ editor, onNew, onOpen, onExport }: CommandPaletteProps) {
  const open = useWorkspace((state) => state.commandPaletteOpen);
  const setOpen = useWorkspace((state) => state.setCommandPaletteOpen);
  const saveNow = useWorkspace((state) => state.saveNow);
  const runReview = useWorkspace((state) => state.runReview);
  const applyAllSafe = useWorkspace((state) => state.applyAllSafe);
  const showNavigation = useWorkspace((state) => state.showNavigation);
  const showReviewPane = useWorkspace((state) => state.showReviewPane);
  const setPaneVisibility = useWorkspace((state) => state.setPaneVisibility);
  const toggleCompareMode = useWorkspace((state) => state.toggleCompareMode);
  const activeSession = useWorkspace((state) => state.activeSession);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = useMemo<CommandItem[]>(
    () => [
      { id: "new", label: "New document", description: "Start a blank local document", shortcut: "⌘N", keywords: ["create", "blank"], run: onNew },
      { id: "open", label: "Open document", description: "Import Word, PDF, Markdown, or text", shortcut: "⌘O", keywords: ["import", "browse"], run: onOpen },
      { id: "save", label: "Save now", description: "Save the current revision", shortcut: "⌘S", run: () => saveNow() },
      { id: "review", label: "Review citations", description: "Run AutoCite on the current revision", shortcut: "F7", keywords: ["check", "bluebook", "citations"], run: () => runReview() },
      { id: "safe", label: "Apply all safe fixes", description: "Accept deterministic nonoverlapping corrections", keywords: ["accept", "automatic"], run: () => applyAllSafe() },
      { id: "compare", label: "Compare with original", description: "Show the imported original beside the working revision", keywords: ["diff", "changes"], run: toggleCompareMode },
      { id: "nav", label: showNavigation ? "Hide navigation pane" : "Show navigation pane", description: "Toggle documents, headings, and search", run: () => setPaneVisibility("navigation", !showNavigation) },
      { id: "review-pane", label: showReviewPane ? "Hide review pane" : "Show review pane", description: "Toggle citation findings and decisions", run: () => setPaneVisibility("review", !showReviewPane) },
      { id: "docx", label: "Export as Word", description: "Create a DOCX copy", keywords: ["download", "office"], run: () => onExport("docx") },
      { id: "pdf", label: "Export as PDF", description: "Create a portable PDF copy", keywords: ["print"], run: () => onExport("pdf") },
      { id: "markdown", label: "Export as Markdown", description: "Create an editable Markdown copy", run: () => onExport("md") },
      { id: "select-all", label: "Select all", description: "Select the entire document", shortcut: "⌘A", run: () => editor?.chain().focus().selectAll().run() },
    ],
    [
      activeSession,
      applyAllSafe,
      editor,
      onExport,
      onNew,
      onOpen,
      runReview,
      saveNow,
      setPaneVisibility,
      showNavigation,
      showReviewPane,
      toggleCompareMode,
    ],
  );

  const filtered = useMemo(() => {
    const terms = query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    if (!terms.length) return commands;
    return commands.filter((command) => {
      const haystack = [command.label, command.description, ...(command.keywords ?? [])]
        .join(" ")
        .toLocaleLowerCase();
      return terms.every((term) => haystack.includes(term));
    });
  }, [commands, query]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setSelected(0);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }, [open]);

  useEffect(() => {
    setSelected((current) => Math.min(current, Math.max(0, filtered.length - 1)));
  }, [filtered.length]);

  if (!open) return null;

  const execute = (command: CommandItem | undefined) => {
    if (!command) return;
    setOpen(false);
    void command.run();
  };

  return (
    <div className="palette-backdrop" role="presentation" onMouseDown={() => setOpen(false)}>
      <section
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Command search"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <label className="palette-input">
          <Command size={18} />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search tools and commands"
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setSelected((current) => Math.min(current + 1, filtered.length - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setSelected((current) => Math.max(current - 1, 0));
              } else if (event.key === "Enter") {
                event.preventDefault();
                execute(filtered[selected]);
              } else if (event.key === "Escape") {
                setOpen(false);
              }
            }}
          />
          <kbd>Esc</kbd>
        </label>
        <div className="palette-results" role="listbox">
          {filtered.map((command, index) => (
            <button
              key={command.id}
              role="option"
              aria-selected={selected === index}
              className={selected === index ? "is-selected" : ""}
              onMouseEnter={() => setSelected(index)}
              onClick={() => execute(command)}
            >
              <span className="palette-icon">{commandIcon(command.id)}</span>
              <span><strong>{command.label}</strong><small>{command.description}</small></span>
              {command.shortcut ? <kbd>{command.shortcut}</kbd> : null}
            </button>
          ))}
          {filtered.length === 0 ? <div className="palette-empty">No commands match “{query}”.</div> : null}
        </div>
        <footer><span>↑↓ Navigate</span><span>↵ Run command</span><span>Search never leaves your computer</span></footer>
      </section>
    </div>
  );
}

function commandIcon(id: string) {
  const icons: Record<string, React.ReactNode> = {
    new: <FilePlus2 />,
    open: <FileSearch />,
    save: <Save />,
    review: <SearchCheck />,
    safe: <CheckCheck />,
    compare: <FileDiff />,
    nav: <PanelLeft />,
    "review-pane": <PanelRight />,
    docx: <FileDown />,
    pdf: <FileDown />,
    markdown: <FileText />,
  };
  return icons[id] ?? <Command />;
}
