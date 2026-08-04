import type { Editor } from "@tiptap/core";
import { Warning } from "@phosphor-icons/react";
import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { CommandPalette, type AppCommand } from "./components/CommandPalette";
import { DocumentEditor } from "./components/DocumentEditor";
import { DocumentLibrary } from "./components/DocumentLibrary";
import { ReviewPane } from "./components/ReviewPane";
import {
  Ribbon,
  type DocumentViewMode,
  type RibbonTab,
} from "./components/Ribbon";
import { StatusBar } from "./components/StatusBar";
import { TitleBar } from "./components/TitleBar";
import {
  applyAcceptedReviewItems,
  calculateDocumentStats,
  normalizeDocumentTitle,
  type ReviewDecision,
  type ReviewItem,
} from "./lib/documentModel";
import type {
  ApplicationAdapter,
  DocumentRecord,
  DocumentSummary,
  ExportDocumentResult,
  ExportFormat,
  NativeDocumentFile,
} from "./services/applicationAdapter";

interface AppProps {
  adapter: ApplicationAdapter;
}

type SaveState = "saved" | "saving" | "unsaved" | "error";
type BackendState = "checking" | "ready" | "preview" | "offline";

interface ConflictState {
  localText: string;
  localTitle: string;
  remote: DocumentRecord;
}

function recordToSummary(document: DocumentRecord): DocumentSummary {
  const { text: _text, mimeType: _mimeType, ...summary } = document;
  return summary;
}

function replaceSummary(
  documents: DocumentSummary[],
  document: DocumentRecord,
): DocumentSummary[] {
  const summary = recordToSummary(document);
  return [summary, ...documents.filter((item) => item.sessionId !== summary.sessionId)];
}

function bytesFromBase64(value: string): Uint8Array<ArrayBuffer> {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function browserDownload(result: ExportDocumentResult): void {
  const blob = new Blob([bytesFromBase64(result.dataBase64)], {
    type: result.mimeType,
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = result.filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function fileToNativeDocument(file: File): Promise<NativeDocumentFile> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return {
    fileName: file.name,
    mimeType: file.type || null,
    dataBase64: btoa(binary),
  };
}

function safeReviewedText(text: string, items: ReviewItem[]): string {
  try {
    return applyAcceptedReviewItems(text, items);
  } catch {
    return text;
  }
}

export function App({ adapter }: AppProps) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [activeDocument, setActiveDocument] = useState<DocumentRecord | null>(null);
  const [editorText, setEditorText] = useState("");
  const [title, setTitle] = useState("Untitled document");
  const [mode, setMode] = useState("auto");
  const [jurisdiction, setJurisdiction] = useState<string | null>(null);
  const [documentType, setDocumentType] = useState("auto");
  const [editor, setEditor] = useState<Editor | null>(null);
  const [activeTab, setActiveTab] = useState<RibbonTab>("Home");
  const [viewMode, setViewMode] = useState<DocumentViewMode>("editing");
  const [libraryVisible, setLibraryVisible] = useState(true);
  const [reviewPaneVisible, setReviewPaneVisible] = useState(true);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [reviewBaseText, setReviewBaseText] = useState("");
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [backendStatus, setBackendStatus] = useState<BackendState>("checking");
  const [zoom, setZoom] = useState(100);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ConflictState | null>(null);
  const [initializing, setInitializing] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const activeDocumentRef = useRef<DocumentRecord | null>(null);
  const editorTextRef = useRef(editorText);
  const titleRef = useRef(title);
  const modeRef = useRef(mode);
  const jurisdictionRef = useRef(jurisdiction);
  const documentTypeRef = useRef(documentType);
  const saveInFlightRef = useRef<Promise<DocumentRecord | null> | null>(null);
  const hydratedRef = useRef(false);

  useEffect(() => {
    activeDocumentRef.current = activeDocument;
  }, [activeDocument]);
  useEffect(() => {
    editorTextRef.current = editorText;
  }, [editorText]);
  useEffect(() => {
    titleRef.current = title;
  }, [title]);
  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);
  useEffect(() => {
    jurisdictionRef.current = jurisdiction;
  }, [jurisdiction]);
  useEffect(() => {
    documentTypeRef.current = documentType;
  }, [documentType]);

  const hydrateDocument = useCallback((document: DocumentRecord) => {
    hydratedRef.current = false;
    setActiveDocument(document);
    setEditorText(document.text);
    setTitle(document.title);
    setMode(document.mode);
    setJurisdiction(document.jurisdiction);
    setDocumentType(document.documentType);
    setReviewItems([]);
    setReviewBaseText(document.text);
    setViewMode("editing");
    setSaveState("saved");
    setConflict(null);
    queueMicrotask(() => {
      hydratedRef.current = true;
    });
  }, []);

  const loadDocument = useCallback(
    async (sessionId: string) => {
      const document = await adapter.getDocument(sessionId);
      hydrateDocument(document);
      if (document.hasReview) {
        try {
          const page = await adapter.getReviewItems(sessionId);
          setReviewItems(page.items);
          setReviewBaseText(document.text);
        } catch {
          setReviewItems([]);
        }
      }
    },
    [adapter, hydrateDocument],
  );

  useEffect(() => {
    let cancelled = false;
    const initialize = async () => {
      try {
        const [health, page] = await Promise.all([
          adapter.health(),
          adapter.listDocuments(),
        ]);
        if (cancelled) return;
        setBackendStatus(health.status === "preview" ? "preview" : "ready");
        setDocuments(page.items);
        if (page.items[0] !== undefined) {
          await loadDocument(page.items[0].sessionId);
        } else {
          const created = await adapter.createDocument({
            title: "Untitled document",
            text: "",
            sourceFormat: "markdown",
            mode: "auto",
            jurisdiction: null,
            documentType: "auto",
          });
          if (cancelled) return;
          setDocuments([recordToSummary(created)]);
          hydrateDocument(created);
        }
      } catch (error) {
        if (!cancelled) {
          setBackendStatus("offline");
          setToast(error instanceof Error ? error.message : "AutoCite could not start.");
        }
      } finally {
        if (!cancelled) setInitializing(false);
      }
    };
    void initialize();
    return () => {
      cancelled = true;
    };
  }, [adapter, hydrateDocument, loadDocument]);

  const isDirty = useCallback((): boolean => {
    const document = activeDocumentRef.current;
    if (document === null) return false;
    return (
      editorTextRef.current !== document.text ||
      normalizeDocumentTitle(titleRef.current) !== document.title ||
      modeRef.current !== document.mode ||
      jurisdictionRef.current !== document.jurisdiction ||
      documentTypeRef.current !== document.documentType
    );
  }, []);

  const saveDocument = useCallback(async (): Promise<DocumentRecord | null> => {
    const current = activeDocumentRef.current;
    if (current === null || !isDirty()) {
      setSaveState("saved");
      return current;
    }
    if (saveInFlightRef.current !== null) return saveInFlightRef.current;
    setSaveState("saving");
    const request = adapter
      .updateDocument({
        sessionId: current.sessionId,
        text: editorTextRef.current,
        expectedRevision: current.revision,
        title: normalizeDocumentTitle(titleRef.current),
        mode: modeRef.current,
        jurisdiction: jurisdictionRef.current,
        documentType: documentTypeRef.current,
      })
      .then((updated) => {
        setActiveDocument(updated);
        activeDocumentRef.current = updated;
        setTitle(updated.title);
        setDocuments((items) => replaceSummary(items, updated));
        setSaveState("saved");
        setReviewItems([]);
        setReviewBaseText(updated.text);
        return updated;
      })
      .catch(async (error: unknown) => {
        setSaveState("error");
        const message = error instanceof Error ? error.message : String(error);
        if (/revision|conflict/iu.test(message)) {
          const remote = await adapter.getDocument(current.sessionId);
          setConflict({
            localText: editorTextRef.current,
            localTitle: titleRef.current,
            remote,
          });
        } else {
          setToast(message);
        }
        return null;
      })
      .finally(() => {
        saveInFlightRef.current = null;
      });
    saveInFlightRef.current = request;
    return request;
  }, [adapter, isDirty]);

  useEffect(() => {
    if (!hydratedRef.current || activeDocument === null || !isDirty()) return;
    setSaveState("unsaved");
    const timer = window.setTimeout(() => {
      void saveDocument();
    }, 900);
    return () => window.clearTimeout(timer);
  }, [activeDocument, editorText, isDirty, jurisdiction, mode, saveDocument, title]);

  const handleEditorChange = useCallback((value: string) => {
    setEditorText(value);
    if (reviewItems.length > 0 && value !== reviewBaseText) {
      setReviewError("The document changed after review. Run AutoCite again to refresh issue locations.");
    }
  }, [reviewBaseText, reviewItems.length]);

  const selectDocument = useCallback(
    async (sessionId: string) => {
      if (activeDocumentRef.current?.sessionId === sessionId) return;
      await saveDocument();
      try {
        await loadDocument(sessionId);
      } catch (error) {
        setToast(error instanceof Error ? error.message : "Could not open the document.");
      }
    },
    [loadDocument, saveDocument],
  );

  const newDocument = useCallback(async () => {
    await saveDocument();
    try {
      const created = await adapter.createDocument({
        title: "Untitled document",
        text: "",
        sourceFormat: "markdown",
        mode: "auto",
        jurisdiction: null,
        documentType: "auto",
      });
      setDocuments((items) => replaceSummary(items, created));
      hydrateDocument(created);
      queueMicrotask(() => editor?.commands.focus("start"));
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Could not create a document.");
    }
  }, [adapter, editor, hydrateDocument, saveDocument]);

  const importNativeDocument = useCallback(
    async (file: NativeDocumentFile) => {
      await saveDocument();
      const imported = await adapter.importDocument({
        ...file,
        mode: modeRef.current,
        jurisdiction: jurisdictionRef.current,
        documentType: documentTypeRef.current,
      });
      setDocuments((items) => replaceSummary(items, imported));
      hydrateDocument(imported);
      setToast(`${imported.fileName ?? imported.title} opened locally.`);
    },
    [adapter, hydrateDocument, saveDocument],
  );

  const openDocument = useCallback(async () => {
    try {
      const selected = await adapter.openDocumentFile();
      if (selected !== null) {
        await importNativeDocument(selected);
      } else {
        fileInputRef.current?.click();
      }
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Could not open that file.");
    }
  }, [adapter, importNativeDocument]);

  const runReview = useCallback(async () => {
    const saved = await saveDocument();
    const document = saved ?? activeDocumentRef.current;
    if (document === null) return;
    setReviewLoading(true);
    setReviewError(null);
    setReviewPaneVisible(true);
    setActiveTab("Review");
    try {
      await adapter.reviewDocument(document.sessionId);
      const page = await adapter.getReviewItems(document.sessionId);
      setReviewItems(page.items);
      setReviewBaseText(document.text);
      setActiveDocument((current) =>
        current === null
          ? current
          : { ...current, hasReview: true, reviewRevision: current.revision },
      );
      setDocuments((items) =>
        items.map((item) =>
          item.sessionId === document.sessionId
            ? { ...item, hasReview: true, reviewRevision: item.revision }
            : item,
        ),
      );
      setToast(
        page.total === 0
          ? "No supported citation issues were found."
          : `${page.total} review item${page.total === 1 ? "" : "s"} ready.`,
      );
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Review failed.");
    } finally {
      setReviewLoading(false);
    }
  }, [adapter, saveDocument]);

  const setDecision = useCallback(
    async (itemId: string, decision: ReviewDecision) => {
      const document = activeDocumentRef.current;
      if (document === null) return;
      const previous = reviewItems;
      startTransition(() => {
        setReviewItems((items) =>
          items.map((item) => (item.itemId === itemId ? { ...item, decision } : item)),
        );
      });
      try {
        await adapter.setReviewDecision({
          sessionId: document.sessionId,
          itemId,
          decision,
          expectedRevision: document.revision,
        });
      } catch (error) {
        setReviewItems(previous);
        setToast(error instanceof Error ? error.message : "Could not save the decision.");
      }
    },
    [adapter, reviewItems],
  );

  const exportDocument = useCallback(
    async (format: ExportFormat) => {
      const saved = await saveDocument();
      const document = saved ?? activeDocumentRef.current;
      if (document === null) return;
      try {
        const result = await adapter.exportDocument(document.sessionId, format, true);
        const savedPath = await adapter.saveExportFile(result);
        if (savedPath === null) browserDownload(result);
        else setToast(`Exported to ${savedPath}`);
      } catch (error) {
        setToast(error instanceof Error ? error.message : "Export failed.");
      }
    },
    [adapter, saveDocument],
  );

  const reviewedText = useMemo(
    () => safeReviewedText(reviewBaseText, reviewItems),
    [reviewBaseText, reviewItems],
  );
  const stats = useMemo(() => calculateDocumentStats(editorText), [editorText]);

  const commands = useMemo<AppCommand[]>(
    () => [
      {
        id: "new",
        label: "New document",
        description: "Create a blank local document",
        category: "File",
        shortcut: "Ctrl N",
        run: () => void newDocument(),
      },
      {
        id: "open",
        label: "Open document",
        description: "Open DOCX, PDF, Markdown, or text",
        category: "File",
        shortcut: "Ctrl O",
        run: () => void openDocument(),
      },
      {
        id: "save",
        label: "Save document",
        description: "Write the current revision to the local workspace",
        category: "File",
        shortcut: "Ctrl S",
        run: () => void saveDocument(),
      },
      {
        id: "review",
        label: "Run AutoCite review",
        description: "Check every supported citation in this document",
        category: "Review",
        shortcut: "Ctrl Shift R",
        run: () => void runReview(),
      },
      {
        id: "compare",
        label: "Compare original and reviewed text",
        description: "Open the side-by-side document comparison",
        category: "View",
        run: () => setViewMode("compare"),
      },
      ...(["docx", "pdf", "md", "txt"] as ExportFormat[]).map((format) => ({
        id: `export-${format}`,
        label: `Export ${format.toUpperCase()}`,
        description: `Create a local ${format.toUpperCase()} copy`,
        category: "Export",
        run: () => void exportDocument(format),
      })),
    ],
    [exportDocument, newDocument, openDocument, runReview, saveDocument],
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const modifier = event.ctrlKey || event.metaKey;
      if (modifier && event.key.toLocaleLowerCase() === "k") {
        event.preventDefault();
        setCommandPaletteOpen((value) => !value);
      } else if (modifier && event.key.toLocaleLowerCase() === "s") {
        event.preventDefault();
        void saveDocument();
      } else if (modifier && event.key.toLocaleLowerCase() === "o") {
        event.preventDefault();
        void openDocument();
      } else if (modifier && event.key.toLocaleLowerCase() === "n") {
        event.preventDefault();
        void newDocument();
      } else if (
        modifier &&
        event.shiftKey &&
        event.key.toLocaleLowerCase() === "r"
      ) {
        event.preventDefault();
        void runReview();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [newDocument, openDocument, runReview, saveDocument]);

  useEffect(() => {
    if (toast === null) return;
    const timeout = window.setTimeout(() => setToast(null), 4200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const resolveConflict = useCallback(
    async (choice: "local" | "remote") => {
      if (conflict === null) return;
      if (choice === "remote") {
        hydrateDocument(conflict.remote);
        return;
      }
      setActiveDocument(conflict.remote);
      activeDocumentRef.current = conflict.remote;
      setEditorText(conflict.localText);
      setTitle(conflict.localTitle);
      setConflict(null);
      setSaveState("unsaved");
      queueMicrotask(() => void saveDocument());
    },
    [conflict, hydrateDocument, saveDocument],
  );

  if (initializing) {
    return (
      <main className="launch-screen" aria-live="polite">
        <div className="brand-mark large">A</div>
        <h1>AutoCite</h1>
        <p>Opening your local citation workspace</p>
        <span className="spinner" />
      </main>
    );
  }

  return (
    <div className="app-shell">
      <TitleBar
        title={title}
        onTitleChange={setTitle}
        onSave={() => void saveDocument()}
        saveState={saveState}
        backendStatus={backendStatus}
        onOpenCommands={() => setCommandPaletteOpen(true)}
      />
      <Ribbon
        activeTab={activeTab}
        onTabChange={setActiveTab}
        editor={editor}
        onNewDocument={() => void newDocument()}
        onOpenDocument={() => void openDocument()}
        onSave={() => void saveDocument()}
        onRunReview={() => void runReview()}
        onExport={(format) => void exportDocument(format)}
        onToggleLibrary={() => setLibraryVisible((visible) => !visible)}
        onToggleReviewPane={() => setReviewPaneVisible((visible) => !visible)}
        reviewPaneVisible={reviewPaneVisible}
        libraryVisible={libraryVisible}
        mode={mode}
        onModeChange={setMode}
        jurisdiction={jurisdiction}
        onJurisdictionChange={setJurisdiction}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        zoom={zoom}
        onZoomChange={setZoom}
        busy={reviewLoading}
      />

      <main
        className={`workspace${libraryVisible ? " has-library" : ""}${reviewPaneVisible ? " has-review" : ""}`}
      >
        {libraryVisible && (
          <DocumentLibrary
            documents={documents}
            activeDocumentId={activeDocument?.sessionId ?? null}
            onSelect={(sessionId) => void selectDocument(sessionId)}
            onNew={() => void newDocument()}
            onOpen={() => void openDocument()}
          />
        )}
        <section className="document-workspace" aria-label="Document workspace">
          {conflict !== null && (
            <div className="conflict-banner" role="alert">
              <Warning size={20} weight="fill" />
              <div>
                <strong>This document changed in another AutoCite window.</strong>
                <p>Choose which revision to keep. AutoCite will not merge legal text silently.</p>
              </div>
              <button type="button" onClick={() => void resolveConflict("remote")}>
                Use saved revision
              </button>
              <button type="button" onClick={() => void resolveConflict("local")}>
                Keep my changes
              </button>
            </div>
          )}
          {viewMode === "editing" ? (
            <div
              className="paper-stage"
              style={{ "--document-zoom": zoom / 100 } as React.CSSProperties}
            >
              <article className="paper-sheet" aria-label="Editable document page">
                <DocumentEditor
                  value={editorText}
                  onChange={handleEditorChange}
                  onReady={setEditor}
                  editable={activeDocument !== null}
                />
              </article>
            </div>
          ) : viewMode === "reviewed" ? (
            <div
              className="paper-stage"
              style={{ "--document-zoom": zoom / 100 } as React.CSSProperties}
            >
              <article className="paper-sheet reviewed-sheet" aria-label="Reviewed document">
                <DocumentEditor
                  value={reviewedText}
                  onChange={() => undefined}
                  onReady={() => undefined}
                  editable={false}
                />
              </article>
            </div>
          ) : (
            <div className="comparison-workspace">
              <section>
                <header>Original</header>
                <article className="paper-sheet comparison-sheet">
                  <DocumentEditor
                    value={reviewBaseText}
                    onChange={() => undefined}
                    onReady={() => undefined}
                    editable={false}
                  />
                </article>
              </section>
              <section>
                <header>Reviewed</header>
                <article className="paper-sheet comparison-sheet">
                  <DocumentEditor
                    value={reviewedText}
                    onChange={() => undefined}
                    onReady={() => undefined}
                    editable={false}
                  />
                </article>
              </section>
            </div>
          )}
        </section>
        {reviewPaneVisible && (
          <ReviewPane
            items={reviewItems}
            loading={reviewLoading}
            error={reviewError}
            onRunReview={() => void runReview()}
            onDecision={(itemId, decision) => void setDecision(itemId, decision)}
          />
        )}
      </main>

      <StatusBar
        stats={stats}
        issueCount={reviewItems.length}
        mode={mode}
        jurisdiction={jurisdiction}
        zoom={zoom}
        onZoomChange={setZoom}
      />

      <input
        ref={fileInputRef}
        className="visually-hidden"
        type="file"
        accept=".docx,.pdf,.md,.markdown,.txt"
        aria-label="Choose a document to open"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0];
          event.currentTarget.value = "";
          if (file !== undefined) {
            void fileToNativeDocument(file)
              .then(importNativeDocument)
              .catch((error: unknown) =>
                setToast(error instanceof Error ? error.message : "Could not read that file."),
              );
          }
        }}
      />

      <CommandPalette
        open={commandPaletteOpen}
        commands={commands}
        onClose={() => setCommandPaletteOpen(false)}
      />

      {toast !== null && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </div>
  );
}
