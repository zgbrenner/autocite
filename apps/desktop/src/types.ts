export type SessionStatus = "ready" | "reviewing" | "reviewed" | "error";

export type DecisionState = "pending" | "accepted" | "rejected";

export interface BackendConnection {
  endpoint: string;
  token: string;
  port: number;
  pid?: number;
}

export interface SessionSummary {
  id: string;
  title: string;
  source_format: string;
  revision: number;
  status: SessionStatus;
  word_count: number;
  citation_count: number;
  created_at: string;
  updated_at: string;
}

export interface ReviewDecision {
  session_id: string;
  issue_id: string;
  state: DecisionState;
  expected_revision: number;
  replacement?: string | null;
  rationale?: string | null;
  decided_at: string;
}

export interface ApplicationIssue {
  id: string;
  start: number;
  end: number;
  original: string;
  replacement?: string | null;
  issue_code?: string | null;
  message?: string | null;
  correction_level: string;
  safe_to_apply: boolean;
  provenance?: string | null;
  raw?: Record<string, unknown>;
}

export interface ReviewPayload {
  application_issues?: ApplicationIssue[];
  corrected_text?: string;
  mode?: string;
  jurisdiction?: string;
  context_reduction?: {
    strategy?: string;
    metrics?: {
      original_characters: number;
      reduced_characters: number;
      savings_ratio: number;
      bypassed: boolean;
      bypass_reason?: string | null;
    };
    reversible?: boolean;
    used_for_deterministic_review?: boolean;
  };
  [key: string]: unknown;
}

export interface DocumentSession extends SessionSummary {
  original_text: string;
  working_text: string;
  metadata: {
    editor_state?: Record<string, unknown>;
    source_path?: string;
    canonical_format?: string;
    [key: string]: unknown;
  };
  latest_review?: ReviewPayload | null;
  decisions: ReviewDecision[];
}

export interface ReviewJob {
  id: string;
  session_id: string;
  session_revision: number;
  state: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  result_summary?: {
    issue_count?: number;
    safe_auto_fix_count?: number;
    mode?: string;
    jurisdiction?: string;
  } | null;
  error?: string | null;
}

export type ExportFormat = "docx" | "pdf" | "md" | "txt";

export type RibbonTab =
  | "file"
  | "home"
  | "insert"
  | "layout"
  | "references"
  | "review"
  | "view";

export type NavigationTab = "documents" | "headings" | "search";

export type ReviewFilter = "all" | "safe" | "attention" | "accepted" | "rejected";

export interface HeadingItem {
  id: string;
  level: number;
  text: string;
}

export interface CommandItem {
  id: string;
  label: string;
  description: string;
  shortcut?: string;
  keywords?: string[];
  run: () => void | Promise<void>;
}
