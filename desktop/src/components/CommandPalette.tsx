import { Command, MagnifyingGlass } from "@phosphor-icons/react";
import {
  useCallback,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

export interface AppCommand {
  id: string;
  label: string;
  description: string;
  category: string;
  shortcut?: string;
  run(): void;
}

interface CommandPaletteProps {
  open: boolean;
  commands: AppCommand[];
  onClose(): void;
}

export function CommandPalette({ open, commands, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query.trim().toLocaleLowerCase());
  const inputRef = useRef<HTMLInputElement>(null);
  const filtered = useMemo(
    () =>
      deferredQuery.length === 0
        ? commands
        : commands.filter((command) =>
            [command.label, command.description, command.category]
              .join(" ")
              .toLocaleLowerCase()
              .includes(deferredQuery),
          ),
    [commands, deferredQuery],
  );
  const close = useCallback(() => {
    setQuery("");
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    queueMicrotask(() => inputRef.current?.focus());
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
      if (event.key === "Enter" && filtered[0] !== undefined) {
        event.preventDefault();
        filtered[0].run();
        close();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [close, filtered, open]);

  if (!open) return null;

  return (
    <div className="palette-backdrop" role="presentation" onMouseDown={close}>
      <section
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <label className="palette-search">
          <MagnifyingGlass size={20} aria-hidden="true" />
          <input
            ref={inputRef}
            aria-label="Search commands"
            placeholder="Type a command or search AutoCite"
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
          />
          <kbd>Esc</kbd>
        </label>
        <div className="palette-results" role="listbox">
          {filtered.length === 0 ? (
            <div className="palette-empty">No commands match this search.</div>
          ) : (
            filtered.map((command, index) => (
              <button
                key={command.id}
                type="button"
                role="option"
                aria-selected={index === 0}
                className={index === 0 ? "is-highlighted" : ""}
                onClick={() => {
                  command.run();
                  close();
                }}
              >
                <Command size={18} />
                <span>
                  <strong>{command.label}</strong>
                  <small>{command.description}</small>
                </span>
                <em>{command.category}</em>
                {command.shortcut !== undefined && <kbd>{command.shortcut}</kbd>}
              </button>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
