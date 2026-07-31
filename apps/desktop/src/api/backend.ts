import { invoke } from "@tauri-apps/api/core";

import type {
  BackendConnection,
  DecisionState,
  DocumentSession,
  ExportFormat,
  ReviewJob,
  SessionSummary,
} from "../types";

interface ApiEnvelope {
  request_id?: string;
  error?: string;
  message?: string;
  [key: string]: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly requestId?: string;
  readonly currentRevision?: number;

  constructor(status: number, payload: ApiEnvelope) {
    super(payload.message || payload.error || `AutoCite backend returned ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = payload.error;
    this.requestId = payload.request_id;
    this.currentRevision =
      typeof payload.current_revision === "number"
        ? payload.current_revision
        : undefined;
  }
}

const sleep = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

export class BackendClient {
  private connection: BackendConnection | null = null;

  async connect(): Promise<BackendConnection> {
    if (this.connection) return this.connection;

    const configuredEndpoint = import.meta.env.VITE_AUTOCITE_API_URL as
      | string
      | undefined;
    const configuredToken = import.meta.env.VITE_AUTOCITE_API_TOKEN as
      | string
      | undefined;

    if (configuredEndpoint && configuredToken) {
      this.connection = {
        endpoint: configuredEndpoint.replace(/\/$/, ""),
        token: configuredToken,
        port: Number(new URL(configuredEndpoint).port || 80),
      };
    } else {
      this.connection = await invoke<BackendConnection>("backend_connection");
      this.connection.endpoint = this.connection.endpoint.replace(/\/$/, "");
    }

    let lastError: unknown;
    for (let attempt = 0; attempt < 30; attempt += 1) {
      try {
        await this.request("/health", { authenticated: false, timeoutMs: 1_500 });
        return this.connection;
      } catch (error) {
        lastError = error;
        await sleep(Math.min(100 + attempt * 75, 750));
      }
    }
    this.connection = null;
    throw lastError instanceof Error
      ? lastError
      : new Error("AutoCite's local backend did not become ready.");
  }

  disconnect(): void {
    this.connection = null;
  }

  async restart(): Promise<BackendConnection> {
    this.connection = await invoke<BackendConnection>("restart_backend");
    return this.connect();
  }

  async health(): Promise<Record<string, unknown>> {
    return this.request("/health", { authenticated: false });
  }

  async listSessions(): Promise<SessionSummary[]> {
    const result = await this.request<{ sessions: SessionSummary[] }>(
      "/sessions?limit=100",
    );
    return result.sessions;
  }

  async createSession(
    title: string,
    text = "",
    sourceFormat = "md",
  ): Promise<DocumentSession> {
    const result = await this.request<{ session: DocumentSession }>("/sessions", {
      method: "POST",
      body: { title, text, source_format: sourceFormat },
    });
    return result.session;
  }

  async importDocument(path: string): Promise<DocumentSession> {
    const result = await this.request<{ session: DocumentSession }>(
      "/sessions/import",
      { method: "POST", body: { path } },
    );
    return result.session;
  }

  async getSession(sessionId: string): Promise<DocumentSession> {
    const result = await this.request<{ session: DocumentSession }>(
      `/sessions/${encodeURIComponent(sessionId)}`,
    );
    return result.session;
  }

  async updateSession(
    sessionId: string,
    expectedRevision: number,
    patch: {
      text?: string;
      title?: string;
      editor_state?: Record<string, unknown>;
    },
  ): Promise<DocumentSession> {
    const result = await this.request<{ session: DocumentSession }>(
      `/sessions/${encodeURIComponent(sessionId)}`,
      {
        method: "PATCH",
        body: { expected_revision: expectedRevision, ...patch },
      },
    );
    return result.session;
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.request(`/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
  }

  async reviewSession(
    sessionId: string,
    expectedRevision: number,
    options: {
      mode?: string;
      jurisdiction?: string;
      deepReview?: boolean;
      useLocalModel?: boolean;
    },
  ): Promise<ReviewJob> {
    const result = await this.request<{ job: ReviewJob }>(
      `/sessions/${encodeURIComponent(sessionId)}/review`,
      {
        method: "POST",
        timeoutMs: options.deepReview || options.useLocalModel ? 300_000 : 120_000,
        body: {
          expected_revision: expectedRevision,
          mode: options.mode,
          jurisdiction: options.jurisdiction,
          deep_review: options.deepReview ?? false,
          use_local_model: options.useLocalModel ?? false,
        },
      },
    );
    return result.job;
  }

  async decideIssue(
    sessionId: string,
    expectedRevision: number,
    issueId: string,
    decision: DecisionState,
  ): Promise<Record<string, unknown>> {
    return this.request(`/sessions/${encodeURIComponent(sessionId)}/decision`, {
      method: "POST",
      body: {
        expected_revision: expectedRevision,
        issue_id: issueId,
        decision,
      },
    });
  }

  async applySafeIssues(
    sessionId: string,
    expectedRevision: number,
    issueIds: string[],
  ): Promise<Record<string, unknown>> {
    return this.request(`/sessions/${encodeURIComponent(sessionId)}/apply-safe`, {
      method: "POST",
      body: {
        expected_revision: expectedRevision,
        issue_ids: issueIds,
      },
    });
  }

  async exportSession(
    sessionId: string,
    format: ExportFormat,
    destination: string,
  ): Promise<Record<string, unknown>> {
    return this.request(`/sessions/${encodeURIComponent(sessionId)}/export`, {
      method: "POST",
      timeoutMs: 60_000,
      body: { format, destination },
    });
  }

  async contextPreview(
    sessionId: string,
    maxCharacters = 12_000,
  ): Promise<Record<string, unknown>> {
    return this.request(
      `/sessions/${encodeURIComponent(sessionId)}/context-preview`,
      {
        method: "POST",
        body: { max_characters: maxCharacters, include_text: false },
      },
    );
  }

  private async request<T extends Record<string, unknown>>(
    path: string,
    options: {
      method?: "GET" | "POST" | "PATCH" | "DELETE";
      body?: Record<string, unknown>;
      timeoutMs?: number;
      authenticated?: boolean;
    } = {},
  ): Promise<T> {
    if (!this.connection) await this.connect();
    const connection = this.connection;
    if (!connection) throw new Error("AutoCite backend is not connected.");

    const controller = new AbortController();
    const timeout = window.setTimeout(
      () => controller.abort(),
      options.timeoutMs ?? 30_000,
    );
    try {
      const headers: Record<string, string> = {
        Accept: "application/json",
      };
      if (options.body) headers["Content-Type"] = "application/json";
      if (options.authenticated !== false) {
        headers.Authorization = `Bearer ${connection.token}`;
      }
      const response = await fetch(`${connection.endpoint}${path}`, {
        method: options.method ?? "GET",
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
        cache: "no-store",
      });
      const payload = (await response.json()) as ApiEnvelope;
      if (!response.ok) throw new ApiError(response.status, payload);
      return payload as T;
    } finally {
      window.clearTimeout(timeout);
    }
  }
}

export const backend = new BackendClient();
