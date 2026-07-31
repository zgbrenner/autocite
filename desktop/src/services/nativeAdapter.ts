import { invoke } from "@tauri-apps/api/core";

import type {
  ApplicationAdapter,
  BackendHealth,
  CreateDocumentRequest,
  DocumentPage,
  DocumentRecord,
  ExportDocumentResult,
  ExportFormat,
  ImportDocumentRequest,
  NativeDocumentFile,
  ReviewDecisionRequest,
  ReviewDecisionResult,
  ReviewItemsPage,
  ReviewJobResult,
  UpdateDocumentRequest,
} from "./applicationAdapter";

interface NativeBackendRequest {
  method: "GET" | "POST" | "PATCH";
  path: string;
  body?: unknown;
}

function camelizeKey(key: string): string {
  return key.replace(/_([a-z])/gu, (_match, letter: string) => letter.toUpperCase());
}

function camelize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(camelize);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, entry]) => [camelizeKey(key), camelize(entry)]),
    );
  }
  return value;
}

async function backendRequest<T>(request: NativeBackendRequest): Promise<T> {
  const response = await invoke<unknown>("backend_request", { request });
  return camelize(response) as T;
}

function pathFor(sessionId: string, suffix = ""): string {
  return `/app/documents/${encodeURIComponent(sessionId)}${suffix}`;
}

export function createNativeAdapter(): ApplicationAdapter {
  return {
    async health(): Promise<BackendHealth> {
      return backendRequest<BackendHealth>({ method: "GET", path: "/app/health" });
    },

    async listDocuments(cursor?: string | null): Promise<DocumentPage> {
      const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
      return backendRequest<DocumentPage>({
        method: "GET",
        path: `/app/documents${query}`,
      });
    },

    async getDocument(sessionId: string): Promise<DocumentRecord> {
      const response = await backendRequest<{ document: DocumentRecord }>({
        method: "GET",
        path: pathFor(sessionId),
      });
      return response.document;
    },

    async createDocument(request: CreateDocumentRequest): Promise<DocumentRecord> {
      const response = await backendRequest<{ document: DocumentRecord }>({
        method: "POST",
        path: "/app/documents",
        body: {
          title: request.title,
          text: request.text,
          source_format: request.sourceFormat,
          mode: request.mode,
          jurisdiction: request.jurisdiction,
          document_type: request.documentType,
        },
      });
      return response.document;
    },

    async updateDocument(request: UpdateDocumentRequest): Promise<DocumentRecord> {
      const response = await backendRequest<{ document: DocumentRecord }>({
        method: "PATCH",
        path: pathFor(request.sessionId),
        body: {
          text: request.text,
          expected_revision: request.expectedRevision,
          title: request.title,
          mode: request.mode,
          jurisdiction: request.jurisdiction,
          document_type: request.documentType,
        },
      });
      return response.document;
    },

    async importDocument(request: ImportDocumentRequest): Promise<DocumentRecord> {
      const response = await backendRequest<{ document: DocumentRecord }>({
        method: "POST",
        path: "/app/import",
        body: {
          file_name: request.fileName,
          mime_type: request.mimeType,
          data_base64: request.dataBase64,
          mode: request.mode,
          jurisdiction: request.jurisdiction,
          document_type: request.documentType,
        },
      });
      return response.document;
    },

    async reviewDocument(sessionId: string): Promise<ReviewJobResult> {
      return backendRequest<ReviewJobResult>({
        method: "POST",
        path: pathFor(sessionId, "/review"),
        body: {},
      });
    },

    async getReviewItems(sessionId: string): Promise<ReviewItemsPage> {
      return backendRequest<ReviewItemsPage>({
        method: "GET",
        path: pathFor(sessionId, "/review"),
      });
    },

    async setReviewDecision(
      request: ReviewDecisionRequest,
    ): Promise<ReviewDecisionResult> {
      const response = await backendRequest<{ item: ReviewDecisionResult }>({
        method: "POST",
        path: pathFor(request.sessionId, "/decisions"),
        body: {
          item_id: request.itemId,
          decision: request.decision,
          expected_revision: request.expectedRevision,
        },
      });
      return response.item;
    },

    async exportDocument(
      sessionId: string,
      format: ExportFormat,
      tracked = true,
    ): Promise<ExportDocumentResult> {
      return backendRequest<ExportDocumentResult>({
        method: "POST",
        path: pathFor(sessionId, "/export"),
        body: { format, tracked },
      });
    },

    async openDocumentFile(): Promise<NativeDocumentFile | null> {
      return invoke<NativeDocumentFile | null>("open_document_file");
    },

    async saveExportFile(result: ExportDocumentResult): Promise<string | null> {
      return invoke<string | null>("save_export_file", { file: result });
    },
  };
}
