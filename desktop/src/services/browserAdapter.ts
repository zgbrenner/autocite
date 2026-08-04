import type { ReviewItem } from "../lib/documentModel";
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

function now(): string {
  return new Date().toISOString();
}

function fingerprint(text: string): string {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function textExport(
  document: DocumentRecord,
  format: ExportFormat,
): ExportDocumentResult {
  const payload = new TextEncoder().encode(document.text);
  const mimeTypes: Record<ExportFormat, string> = {
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    pdf: "application/pdf",
    txt: "text/plain; charset=utf-8",
    md: "text/markdown; charset=utf-8",
  };
  return {
    filename: `${document.title}.${format}`,
    mimeType: mimeTypes[format],
    dataBase64: bytesToBase64(payload),
    sizeBytes: payload.length,
  };
}

function seedDocument(): DocumentRecord {
  const timestamp = now();
  const text = [
    "# Motion to Dismiss",
    "",
    "The complaint should be dismissed because the pleading does not state a claim.",
    "",
    "See 42 USC § 1983. The Court should also review Smith v. Jones, 123 F.3d 456 (9th Cir. 2024).",
  ].join("\n");
  return {
    sessionId: "welcome-document",
    title: "Motion to dismiss",
    text,
    sourceFormat: "markdown",
    fileName: "motion-to-dismiss.md",
    mimeType: "text/markdown",
    mode: "bluepages",
    jurisdiction: "federal",
    documentType: "brief",
    revision: 1,
    contentSha256: fingerprint(text),
    reviewRevision: null,
    hasReview: false,
    createdAt: timestamp,
    updatedAt: timestamp,
  };
}

export function createBrowserAdapter(): ApplicationAdapter {
  const documents = new Map<string, DocumentRecord>();
  const reviews = new Map<string, ReviewItem[]>();
  const seed = seedDocument();
  documents.set(seed.sessionId, seed);

  const requireDocument = (sessionId: string): DocumentRecord => {
    const document = documents.get(sessionId);
    if (document === undefined) throw new Error(`Unknown document ${sessionId}`);
    return document;
  };

  const createDocument = async (
    request: CreateDocumentRequest,
  ): Promise<DocumentRecord> => {
    const timestamp = now();
    const sessionId = crypto.randomUUID();
    const document: DocumentRecord = {
      sessionId,
      title: request.title,
      text: request.text,
      sourceFormat: request.sourceFormat,
      fileName: `${request.title}.md`,
      mimeType: "text/markdown",
      mode: request.mode,
      jurisdiction: request.jurisdiction,
      documentType: request.documentType,
      revision: 1,
      contentSha256: fingerprint(request.text),
      reviewRevision: null,
      hasReview: false,
      createdAt: timestamp,
      updatedAt: timestamp,
    };
    documents.set(sessionId, document);
    return structuredClone(document);
  };

  return {
    async health(): Promise<BackendHealth> {
      return { status: "preview", localFirst: true };
    },

    async listDocuments(): Promise<DocumentPage> {
      return {
        items: [...documents.values()]
          .toSorted((left, right) => right.updatedAt.localeCompare(left.updatedAt))
          .map(({ text: _text, mimeType: _mimeType, ...summary }) => summary),
        nextCursor: null,
      };
    },

    async getDocument(sessionId: string): Promise<DocumentRecord> {
      return structuredClone(requireDocument(sessionId));
    },

    createDocument,

    async updateDocument(request: UpdateDocumentRequest): Promise<DocumentRecord> {
      const current = requireDocument(request.sessionId);
      if (current.revision !== request.expectedRevision) {
        throw new Error(
          `Revision conflict: expected ${request.expectedRevision}, found ${current.revision}.`,
        );
      }
      const updated: DocumentRecord = {
        ...current,
        title: request.title ?? current.title,
        text: request.text,
        mode: request.mode ?? current.mode,
        jurisdiction:
          request.jurisdiction === undefined
            ? current.jurisdiction
            : request.jurisdiction,
        documentType: request.documentType ?? current.documentType,
        revision: current.revision + 1,
        contentSha256: fingerprint(request.text),
        reviewRevision: null,
        hasReview: false,
        updatedAt: now(),
      };
      documents.set(request.sessionId, updated);
      reviews.delete(request.sessionId);
      return structuredClone(updated);
    },

    async importDocument(request: ImportDocumentRequest): Promise<DocumentRecord> {
      const binary = atob(request.dataBase64);
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      const text = new TextDecoder().decode(bytes);
      return createDocument({
        title: request.fileName.replace(/\.[^.]+$/u, ""),
        text,
        sourceFormat: request.fileName.split(".").pop() ?? "text",
        mode: request.mode,
        jurisdiction: request.jurisdiction,
        documentType: request.documentType,
      });
    },

    async reviewDocument(sessionId: string): Promise<ReviewJobResult> {
      const document = requireDocument(sessionId);
      const items: ReviewItem[] = [];
      const statute = "42 USC";
      const statuteStart = document.text.indexOf(statute);
      if (statuteStart >= 0) {
        items.push({
          itemId: `statute-${statuteStart}`,
          code: "STATUTE_ABBREVIATION",
          start: statuteStart,
          end: statuteStart + statute.length,
          original: statute,
          suggestion: "42 U.S.C.",
          message: "Use the standard United States Code abbreviation.",
          severity: "warning",
          confidence: "high",
          correctionLevel: "safe_auto_fix",
          provenance: "deterministic_logic",
          decision: "accepted",
          rule: "B12",
        });
      }
      reviews.set(sessionId, items);
      const reviewed: DocumentRecord = {
        ...document,
        reviewRevision: document.revision,
        hasReview: true,
      };
      documents.set(sessionId, reviewed);
      return {
        job: { jobId: crypto.randomUUID(), status: "completed" },
        summary: {
          itemCount: items.length,
          acceptedCount: items.filter((item) => item.decision === "accepted").length,
          pendingCount: items.filter((item) => item.decision === "pending").length,
          rejectedCount: items.filter((item) => item.decision === "rejected").length,
        },
      };
    },

    async getReviewItems(sessionId: string): Promise<ReviewItemsPage> {
      const document = requireDocument(sessionId);
      const items = structuredClone(reviews.get(sessionId) ?? []);
      return {
        sessionId,
        documentRevision: document.revision,
        reviewRevision: document.reviewRevision,
        items,
        offset: 0,
        limit: 100,
        total: items.length,
        nextOffset: null,
      };
    },

    async setReviewDecision(
      request: ReviewDecisionRequest,
    ): Promise<ReviewDecisionResult> {
      const document = requireDocument(request.sessionId);
      if (document.revision !== request.expectedRevision) {
        throw new Error("Revision conflict while saving a review decision.");
      }
      const items = reviews.get(request.sessionId) ?? [];
      const item = items.find((candidate) => candidate.itemId === request.itemId);
      if (item === undefined) throw new Error(`Unknown review item ${request.itemId}`);
      item.decision = request.decision;
      return { itemId: item.itemId, decision: item.decision };
    },

    async exportDocument(
      sessionId: string,
      format: ExportFormat,
    ): Promise<ExportDocumentResult> {
      return textExport(requireDocument(sessionId), format);
    },

    async openDocumentFile(): Promise<NativeDocumentFile | null> {
      return null;
    },

    async saveExportFile(): Promise<string | null> {
      return null;
    },
  };
}
