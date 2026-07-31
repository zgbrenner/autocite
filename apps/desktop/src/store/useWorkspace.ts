import { create } from "zustand";

import { ApiError, backend } from "../api/backend";
import { normalizeDocumentTitle } from "../lib/document";
import type {
  DecisionState,
  DocumentSession,
  NavigationTab,
  ReviewFilter,
  RibbonTab,
  SessionSummary,
} from "../types";

export type ConnectionStatus = "starting" | "ready" | "error";
export type SaveStatus = "saved" | "dirty" | "saving" | "conflict" | "error";

export interface ToastMessage {
  id: number;
  title: string;
  detail?: string;
  tone: "neutral" | "success" | "warning" | "error";
}

interface WorkspaceState {
  connectionStatus: ConnectionStatus;
  initializationError: string | null;
  sessions: SessionSummary[];
  activeSession: DocumentSession | null;
  documentText: string;
  documentTitle: string;
  dirty: boolean;
  saveStatus: SaveStatus;
  saveError: string | null;
  isReviewing: boolean;
  selectedIssueId: string | null;
  ribbonTab: RibbonTab;
  navigationTab: NavigationTab;
  reviewFilter: ReviewFilter;
  showNavigation: boolean;
  showReviewPane: boolean;
  showRuler: boolean;
  focusMode: boolean;
  compareMode: boolean;
  zoom: number;
  mode: "auto" | "bluepages" | "whitepages";
  jurisdiction: string;
  deepReview: boolean;
  useLocalModel: boolean;
  commandPaletteOpen: boolean;
  evidenceDrawerOpen: boolean;
  toast: ToastMessage | null;

  initialize: () => Promise<void>;
  refreshSessions: () => Promise<void>;
  openSession: (sessionId: string) => Promise<void>;
  createDocument: (title?: string) => Promise<void>;
  importDocument: (path: string) => Promise<void>;
  deleteActiveDocument: () => Promise<void>;
  updateDocument: (text: string) => void;
  updateTitle: (title: string) => void;
  saveNow: () => Promise<void>;
  reloadAfterConflict: () => Promise<void>;
  runReview: () => Promise<void>;
  decideIssue: (issueId: string, decision: DecisionState) => Promise<void>;
  applyAllSafe: () => Promise<void>;
  selectIssue: (issueId: string | null) => void;
  setRibbonTab: (tab: RibbonTab) => void;
  setNavigationTab: (tab: NavigationTab) => void;
  setReviewFilter: (filter: ReviewFilter) => void;
  setPaneVisibility: (pane: "navigation" | "review", visible: boolean) => void;
  toggleRuler: () => void;
  toggleFocusMode: () => void;
  toggleCompareMode: () => void;
  setZoom: (zoom: number) => void;
  setMode: (mode: "auto" | "bluepages" | "whitepages") => void;
  setJurisdiction: (jurisdiction: string) => void;
  setDeepReview: (enabled: boolean) => void;
  setUseLocalModel: (enabled: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setEvidenceDrawerOpen: (open: boolean) => void;
  notify: (message: Omit<ToastMessage, "id">) => void;
  clearToast: () => void;
}

let autosaveTimer: number | null = null;
let saveQueue: Promise<void> = Promise.resolve();
let toastSequence = 0;

function preferenceBoolean(key: string, fallback: boolean): boolean {
  const stored = window.localStorage.getItem(`autocite.${key}`);
  return stored === null ? fallback : stored === "true";
}

function preferenceNumber(key: string, fallback: number): number {
  const stored = Number(window.localStorage.getItem(`autocite.${key}`));
  return Number.isFinite(stored) ? stored : fallback;
}

function scheduleAutosave(save: () => Promise<void>): void {
  if (autosaveTimer !== null) window.clearTimeout(autosaveTimer);
  autosaveTimer = window.setTimeout(() => {
    autosaveTimer = null;
    void save();
  }, 850);
}

function summaryFromSession(session: DocumentSession): SessionSummary {
  return {
    id: session.id,
    title: session.title,
    source_format: session.source_format,
    revision: session.revision,
    status: session.status,
    word_count: session.word_count,
    citation_count: session.citation_count,
    created_at: session.created_at,
    updated_at: session.updated_at,
  };
}

function mergeSession(
  previous: DocumentSession,
  incoming: DocumentSession,
): DocumentSession {
  return {
    ...previous,
    ...incoming,
    original_text: incoming.original_text ?? previous.original_text,
    working_text: incoming.working_text ?? previous.working_text,
    metadata: incoming.metadata ?? previous.metadata,
    decisions: incoming.decisions ?? previous.decisions ?? [],
  };
}

function errorMessage(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return "The local AutoCite service did not respond in time.";
  }
  return error instanceof Error ? error.message : "An unexpected error occurred.";
}

export const useWorkspace = create<WorkspaceState>((set, get) => ({
  connectionStatus: "starting",
  initializationError: null,
  sessions: [],
  activeSession: null,
  documentText: "",
  documentTitle: "",
  dirty: false,
  saveStatus: "saved",
  saveError: null,
  isReviewing: false,
  selectedIssueId: null,
  ribbonTab: "home",
  navigationTab: "documents",
  reviewFilter: "all",
  showNavigation: preferenceBoolean("showNavigation", true),
  showReviewPane: preferenceBoolean("showReviewPane", true),
  showRuler: preferenceBoolean("showRuler", true),
  focusMode: false,
  compareMode: false,
  zoom: Math.max(70, Math.min(180, preferenceNumber("zoom", 100))),
  mode: "auto",
  jurisdiction: "federal",
  deepReview: false,
  useLocalModel: false,
  commandPaletteOpen: false,
  evidenceDrawerOpen: false,
  toast: null,

  initialize: async () => {
    set({ connectionStatus: "starting", initializationError: null });
    try {
      await backend.connect();
      const sessions = await backend.listSessions();
      set({ connectionStatus: "ready", sessions });
      const first = sessions[0];
      if (first) await get().openSession(first.id);
    } catch (error) {
      set({
        connectionStatus: "error",
        initializationError: errorMessage(error),
      });
    }
  },

  refreshSessions: async () => {
    const sessions = await backend.listSessions();
    set({ sessions });
  },

  openSession: async (sessionId) => {
    if (get().activeSession?.id === sessionId) return;
    await get().saveNow();
    const session = await backend.getSession(sessionId);
    set({
      activeSession: session,
      documentText: session.working_text,
      documentTitle: session.title,
      dirty: false,
      saveStatus: "saved",
      saveError: null,
      selectedIssueId: session.latest_review?.application_issues?.[0]?.id ?? null,
      compareMode: false,
    });
  },

  createDocument: async (title = "Untitled document") => {
    await get().saveNow();
    const session = await backend.createSession(normalizeDocumentTitle(title));
    const full = await backend.getSession(session.id);
    set((state) => ({
      sessions: [summaryFromSession(full), ...state.sessions],
      activeSession: full,
      documentText: full.working_text,
      documentTitle: full.title,
      dirty: false,
      saveStatus: "saved",
      saveError: null,
      selectedIssueId: null,
      compareMode: false,
    }));
  },

  importDocument: async (path) => {
    await get().saveNow();
    const session = await backend.importDocument(path);
    const full = await backend.getSession(session.id);
    set((state) => ({
      sessions: [summaryFromSession(full), ...state.sessions.filter((item) => item.id !== full.id)],
      activeSession: full,
      documentText: full.working_text,
      documentTitle: full.title,
      dirty: false,
      saveStatus: "saved",
      saveError: null,
      selectedIssueId: null,
      compareMode: false,
      ribbonTab: "home",
    }));
    get().notify({
      title: "Document imported",
      detail: `${full.title} is ready to edit and review.`,
      tone: "success",
    });
  },

  deleteActiveDocument: async () => {
    const session = get().activeSession;
    if (!session) return;
    await backend.deleteSession(session.id);
    const remaining = get().sessions.filter((item) => item.id !== session.id);
    set({
      sessions: remaining,
      activeSession: null,
      documentText: "",
      documentTitle: "",
      dirty: false,
      saveStatus: "saved",
      selectedIssueId: null,
    });
    const next = remaining[0];
    if (next) await get().openSession(next.id);
  },

  updateDocument: (text) => {
    set({
      documentText: text,
      dirty: true,
      saveStatus: "dirty",
      saveError: null,
    });
    scheduleAutosave(get().saveNow);
  },

  updateTitle: (title) => {
    set({
      documentTitle: title,
      dirty: true,
      saveStatus: "dirty",
      saveError: null,
    });
    scheduleAutosave(get().saveNow);
  },

  saveNow: async () => {
    saveQueue = saveQueue
      .catch(() => undefined)
      .then(async () => {
        const snapshot = get();
        const active = snapshot.activeSession;
        if (!active || !snapshot.dirty) return;

        const capturedText = snapshot.documentText;
        const capturedTitle = normalizeDocumentTitle(snapshot.documentTitle);
        const capturedRevision = active.revision;
        set({ saveStatus: "saving", saveError: null });
        try {
          const incoming = await backend.updateSession(active.id, capturedRevision, {
            text: capturedText,
            title: capturedTitle,
            editor_state: {
              zoom: get().zoom,
              show_ruler: get().showRuler,
            },
          });
          const current = get();
          if (current.activeSession?.id !== active.id) return;
          const merged = mergeSession(active, incoming);
          const unchanged =
            current.documentText === capturedText &&
            normalizeDocumentTitle(current.documentTitle) === capturedTitle;
          set((state) => ({
            activeSession: merged,
            documentTitle: unchanged ? capturedTitle : state.documentTitle,
            dirty: !unchanged,
            saveStatus: unchanged ? "saved" : "dirty",
            sessions: [
              summaryFromSession(merged),
              ...state.sessions.filter((item) => item.id !== merged.id),
            ],
          }));
          if (!unchanged) scheduleAutosave(get().saveNow);
        } catch (error) {
          if (error instanceof ApiError && error.status === 409) {
            set({ saveStatus: "conflict", saveError: error.message });
          } else {
            set({ saveStatus: "error", saveError: errorMessage(error) });
          }
        }
      });
    await saveQueue;
  },

  reloadAfterConflict: async () => {
    const session = get().activeSession;
    if (!session) return;
    const current = await backend.getSession(session.id);
    set({
      activeSession: current,
      documentText: current.working_text,
      documentTitle: current.title,
      dirty: false,
      saveStatus: "saved",
      saveError: null,
      selectedIssueId: current.latest_review?.application_issues?.[0]?.id ?? null,
    });
  },

  runReview: async () => {
    await get().saveNow();
    const active = get().activeSession;
    if (!active || get().saveStatus === "conflict") return;
    set({ isReviewing: true, ribbonTab: "review", showReviewPane: true });
    try {
      const state = get();
      const job = await backend.reviewSession(active.id, active.revision, {
        mode: state.mode === "auto" ? undefined : state.mode,
        jurisdiction: state.jurisdiction,
        deepReview: state.deepReview,
        useLocalModel: state.useLocalModel,
      });
      if (job.state === "failed") throw new Error(job.error || "Review failed.");
      const refreshed = await backend.getSession(active.id);
      set((current) => ({
        activeSession: refreshed,
        documentText: refreshed.working_text,
        documentTitle: refreshed.title,
        sessions: [
          summaryFromSession(refreshed),
          ...current.sessions.filter((item) => item.id !== refreshed.id),
        ],
        selectedIssueId: refreshed.latest_review?.application_issues?.[0]?.id ?? null,
        isReviewing: false,
      }));
      get().notify({
        title: "Citation review complete",
        detail: `${job.result_summary?.issue_count ?? 0} review items found.`,
        tone: "success",
      });
    } catch (error) {
      set({ isReviewing: false });
      get().notify({
        title: "Review could not be completed",
        detail: errorMessage(error),
        tone: "error",
      });
    }
  },

  decideIssue: async (issueId, decision) => {
    await get().saveNow();
    const active = get().activeSession;
    if (!active) return;
    try {
      await backend.decideIssue(active.id, active.revision, issueId, decision);
      const refreshed = await backend.getSession(active.id);
      set((state) => ({
        activeSession: refreshed,
        documentText: refreshed.working_text,
        documentTitle: refreshed.title,
        dirty: false,
        saveStatus: "saved",
        sessions: [
          summaryFromSession(refreshed),
          ...state.sessions.filter((item) => item.id !== refreshed.id),
        ],
        selectedIssueId:
          refreshed.latest_review?.application_issues?.find((item) => item.id !== issueId)?.id ??
          null,
      }));
    } catch (error) {
      get().notify({
        title: "Review decision was not applied",
        detail: errorMessage(error),
        tone: "error",
      });
    }
  },

  applyAllSafe: async () => {
    await get().saveNow();
    const active = get().activeSession;
    if (!active) return;
    const decisions = new Map(
      active.decisions.map((decision) => [decision.issue_id, decision.state]),
    );
    const identifiers = (active.latest_review?.application_issues ?? [])
      .filter(
        (issue) => issue.safe_to_apply && decisions.get(issue.id) !== "accepted",
      )
      .map((issue) => issue.id);
    if (identifiers.length === 0) {
      get().notify({
        title: "No safe fixes are waiting",
        detail: "Items requiring judgment remain available for individual review.",
        tone: "neutral",
      });
      return;
    }
    try {
      await backend.applySafeIssues(active.id, active.revision, identifiers);
      const refreshed = await backend.getSession(active.id);
      set((state) => ({
        activeSession: refreshed,
        documentText: refreshed.working_text,
        documentTitle: refreshed.title,
        dirty: false,
        saveStatus: "saved",
        selectedIssueId: null,
        sessions: [
          summaryFromSession(refreshed),
          ...state.sessions.filter((item) => item.id !== refreshed.id),
        ],
      }));
      get().notify({
        title: "Safe fixes applied",
        detail: `${identifiers.length} deterministic changes were accepted. Run review again to refresh offsets.`,
        tone: "success",
      });
    } catch (error) {
      get().notify({
        title: "Safe fixes could not be applied",
        detail: errorMessage(error),
        tone: "error",
      });
    }
  },

  selectIssue: (selectedIssueId) => set({ selectedIssueId }),
  setRibbonTab: (ribbonTab) => set({ ribbonTab }),
  setNavigationTab: (navigationTab) => set({ navigationTab }),
  setReviewFilter: (reviewFilter) => set({ reviewFilter }),
  setPaneVisibility: (pane, visible) => {
    if (pane === "navigation") {
      window.localStorage.setItem("autocite.showNavigation", String(visible));
      set({ showNavigation: visible });
    } else {
      window.localStorage.setItem("autocite.showReviewPane", String(visible));
      set({ showReviewPane: visible });
    }
  },
  toggleRuler: () => {
    const value = !get().showRuler;
    window.localStorage.setItem("autocite.showRuler", String(value));
    set({ showRuler: value });
  },
  toggleFocusMode: () => set((state) => ({ focusMode: !state.focusMode })),
  toggleCompareMode: () => set((state) => ({ compareMode: !state.compareMode })),
  setZoom: (zoom) => {
    const bounded = Math.max(70, Math.min(180, zoom));
    window.localStorage.setItem("autocite.zoom", String(bounded));
    set({ zoom: bounded });
  },
  setMode: (mode) => set({ mode }),
  setJurisdiction: (jurisdiction) => set({ jurisdiction }),
  setDeepReview: (deepReview) => set({ deepReview }),
  setUseLocalModel: (useLocalModel) => set({ useLocalModel }),
  setCommandPaletteOpen: (commandPaletteOpen) => set({ commandPaletteOpen }),
  setEvidenceDrawerOpen: (evidenceDrawerOpen) => set({ evidenceDrawerOpen }),
  notify: (message) => {
    toastSequence += 1;
    const id = toastSequence;
    set({ toast: { ...message, id } });
    window.setTimeout(() => {
      if (get().toast?.id === id) set({ toast: null });
    }, message.tone === "error" ? 8_000 : 4_500);
  },
  clearToast: () => set({ toast: null }),
}));
