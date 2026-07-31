import type { Editor } from "@tiptap/react";
import { confirm, open, save } from "@tauri-apps/plugin-dialog";
import { AlertTriangle, FilePlus2, FileSearch, RefreshCw, Save } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { backend } from "./api/backend";
import { CommandPalette } from "./components/CommandPalette";
import { EditorCanvas } from "./components/EditorCanvas";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { NavigationPane } from "./components/NavigationPane";
import { ReviewPane } from "./components/ReviewPane";
import { Ribbon } from "./components/Ribbon";
import { StartScreen } from "./components/StartScreen";
import { StatusBar } from "./components/StatusBar";
import { TitleBar } from "./components/TitleBar";
import { Toast } from "./components/Toast";
import { useWorkspace } from "./store/useWorkspace";
import type { ExportFormat } from "./types";

export default function App() {
  const initialize = useWorkspace((state) => state.initialize);
  const connectionStatus = useWorkspace((state) => state.connectionStatus);
  const initializationError = useWorkspace((state) => state.initializationError);
  const active = useWorkspace((state) => state.activeSession);
  const documentText = useWorkspace((state) => state.documentText);
  const updateDocument = useWorkspace((state) => state.updateDocument);
  const createDocument = useWorkspace((state) => state.createDocument);
  const importDocument = useWorkspace((state) => state.importDocument);
  const saveNow = useWorkspace((state) => state.saveNow);
  const dirty = useWorkspace((state) => state.dirty);
  const saveStatus = useWorkspace((state) => state.saveStatus);
  const saveError = useWorkspace((state) => state.saveError);
  const reloadAfterConflict = useWorkspace((state) => state.reloadAfterConflict);
  const runReview = useWorkspace((state) => state.runReview);
  const showNavigation = useWorkspace((state) => state.showNavigation);
  const showReviewPane = useWorkspace((state) => state.showReviewPane);
  const showRuler = useWorkspace((state) => state.showRuler);
  const compareMode = useWorkspace((state) => state.compareMode);
  const focusMode = useWorkspace((state) => state.focusMode);
  const zoom = useWorkspace((state) => state.zoom);
  const setCommandPaletteOpen = useWorkspace((state) => state.setCommandPaletteOpen);
  const notify = useWorkspace((state) => state.notify);

  const [editor, setEditor] = useState<Editor | null>(null);
  const [selectedText, setSelectedText] = useState("");

  useEffect(() => {
    void initialize();
  }, [initialize]);

  const handleNew = useCallback(() => {
    void createDocument();
  }, [createDocument]);

  const handleOpen = useCallback(async () => {
    try {
      const path = await open({
        multiple: false,
        directory: false,
        title: "Open a document in AutoCite",
        filters: [
          {
            name: "Supported documents",
            extensions: ["docx", "pdf", "md", "markdown", "txt"],
          },
          { name: "Word documents", extensions: ["docx"] },
          { name: "PDF documents", extensions: ["pdf"] },
          { name: "Text documents", extensions: ["md", "markdown", "txt"] },
        ],
      });
      if (typeof path === "string") await importDocument(path);
    } catch (error) {
      notify({
        title: "Document could not be opened",
        detail: error instanceof Error ? error.message : "The selected file could not be imported.",
        tone: "error",
      });
    }
  }, [importDocument, notify]);

  const handleExport = useCallback(
    async (format: ExportFormat) => {
      if (!active) return;
      await saveNow();
      const extension = format;
      const destination = await save({
        title: `Export ${active.title}`,
        defaultPath: `${active.title}-autocite.${extension}`,
        filters: [{ name: exportLabel(format), extensions: [extension] }],
      });
      if (!destination) return;
      try {
        await backend.exportSession(active.id, format, destination);
        notify({
          title: `${exportLabel(format)} created`,
          detail: destination,
          tone: "success",
        });
      } catch (error) {
        notify({
          title: "Export failed",
          detail: error instanceof Error ? error.message : "AutoCite could not create the export.",
          tone: "error",
        });
      }
    },
    [active, notify, saveNow],
  );

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      const modifier = event.metaKey || event.ctrlKey;
      if (modifier && event.key.toLowerCase() === "s") {
        event.preventDefault();
        void saveNow();
      } else if (modifier && event.key.toLowerCase() === "o") {
        event.preventDefault();
        void handleOpen();
      } else if (modifier && event.key.toLowerCase() === "n") {
        event.preventDefault();
        handleNew();
      } else if (modifier && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandPaletteOpen(true);
      } else if (event.key === "F7") {
        event.preventDefault();
        void runReview();
      }
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, [handleNew, handleOpen, runReview, saveNow, setCommandPaletteOpen]);

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (dirty) event.preventDefault();
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [dirty]);

  useEffect(() => {
    let disposed = false;
    let release: (() => void) | undefined;
    void import("@tauri-apps/api/webviewWindow")
      .then(({ getCurrentWebviewWindow }) =>
        getCurrentWebviewWindow().onDragDropEvent((event) => {
          if (event.payload.type !== "drop") return;
          const path = event.payload.paths[0];
          if (path && /\.(docx|pdf|md|markdown|txt)$/i.test(path)) void importDocument(path);
        }),
      )
      .then((unlisten) => {
        if (disposed) void unlisten();
        else release = unlisten;
      })
      .catch(() => undefined);
    return () => {
      disposed = true;
      if (release) void release();
    };
  }, [importDocument]);

  if (connectionStatus === "starting") return <LoadingScreen />;
  if (connectionStatus === "error") {
    return <ConnectionError message={initializationError} retry={() => void initialize()} />;
  }

  return (
    <div className={`app-shell ${focusMode ? "is-focus-mode" : ""}`}>
      <TitleBar editor={editor} />
      {active ? <Ribbon editor={editor} onNew={handleNew} onOpen={() => void handleOpen()} onExport={(format) => void handleExport(format)} /> : null}

      {saveStatus === "conflict" || saveStatus === "error" ? (
        <div className={`save-banner ${saveStatus === "conflict" ? "is-conflict" : "is-error"}`}>
          <AlertTriangle size={16} />
          <span><strong>{saveStatus === "conflict" ? "A newer revision exists." : "AutoCite could not save this revision."}</strong> {saveError}</span>
          {saveStatus === "conflict" ? <button onClick={() => void reloadAfterConflict()}><RefreshCw size={14} /> Reload saved revision</button> : <button onClick={() => void saveNow()}><Save size={14} /> Try again</button>}
        </div>
      ) : null}

      {!active ? (
        <StartScreen onNew={handleNew} onOpen={() => void handleOpen()} />
      ) : (
        <main className="workspace">
          {showNavigation && !focusMode ? <NavigationPane onNew={handleNew} onOpen={() => void handleOpen()} /> : null}
          <section className="editor-workspace">
            <EditorCanvas
              sessionId={active.id}
              markdown={documentText}
              originalMarkdown={active.original_text}
              zoom={zoom}
              showRuler={showRuler}
              compareMode={compareMode}
              onChange={updateDocument}
              onEditorReady={setEditor}
              onSelectionChange={setSelectedText}
            />
          </section>
          {showReviewPane && !focusMode ? <ReviewPane /> : null}
        </main>
      )}

      {active ? <StatusBar selectedText={selectedText} /> : null}
      <CommandPalette editor={editor} onNew={handleNew} onOpen={() => void handleOpen()} onExport={(format) => void handleExport(format)} />
      <EvidenceDrawer />
      <Toast />
    </div>
  );
}

function LoadingScreen() {
  return (
    <main className="loading-screen">
      <span className="loading-logo">AC</span>
      <h1>AutoCite</h1>
      <p>Starting the private document engine…</p>
      <span className="loading-line"><i /></span>
    </main>
  );
}

function ConnectionError({ message, retry }: { message: string | null; retry: () => void }) {
  return (
    <main className="connection-error">
      <span><AlertTriangle /></span>
      <h1>AutoCite could not start its local engine</h1>
      <p>{message || "The bundled sidecar did not become ready."}</p>
      <div>
        <button onClick={retry}><RefreshCw size={16} /> Try again</button>
        <button onClick={() => window.location.reload()}><FileSearch size={16} /> Reload app</button>
      </div>
      <small>No document content was sent anywhere.</small>
    </main>
  );
}

function exportLabel(format: ExportFormat): string {
  return { docx: "Word document", pdf: "PDF document", md: "Markdown document", txt: "Plain text document" }[format];
}
