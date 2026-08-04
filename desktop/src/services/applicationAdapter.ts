import type { ReviewDecision, ReviewItem } from "../lib/documentModel";

export interface BackendHealth {
  status: string;
  localFirst: boolean;
}

export interface DocumentSummary {
  sessionId: string;
  title: string;
  sourceFormat: string;
  fileName: string | null;
  mode: string;
  jurisdiction: string | null;
  documentType: string;
  revision: number;
  contentSha256: string;
  reviewRevision: number | null;
  hasReview: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentRecord extends DocumentSummary {
  text: string;
  mimeType: string | null;
}

export interface DocumentPage {
  items: DocumentSummary[];
  nextCursor: string | null;
}

export interface UpdateDocumentRequest {
  sessionId: string;
  text: string;
  expectedRevision: number;
  title?: string;
  mode?: string;
  jurisdiction?: string | null;
  documentType?: string;
}

export interface CreateDocumentRequest {
  title: string;
  text: string;
  sourceFormat: string;
  mode: string;
  jurisdiction: string | null;
  documentType: string;
}

export interface ImportDocumentRequest {
  fileName: string;
  mimeType: string | null;
  dataBase64: string;
  mode: string;
  jurisdiction: string | null;
  documentType: string;
}

export interface NativeDocumentFile {
  fileName: string;
  mimeType: string | null;
  dataBase64: string;
}

export interface ReviewSummary {
  itemCount: number;
  acceptedCount: number;
  pendingCount: number;
  rejectedCount: number;
}

export interface ReviewJobResult {
  job: { jobId: string; status: string };
  summary: ReviewSummary;
}

export interface ReviewItemsPage {
  sessionId: string;
  documentRevision: number;
  reviewRevision: number | null;
  items: ReviewItem[];
  offset: number;
  limit: number;
  total: number;
  nextOffset: number | null;
}

export interface ReviewDecisionRequest {
  sessionId: string;
  itemId: string;
  decision: ReviewDecision;
  expectedRevision: number;
}

export interface ReviewDecisionResult {
  itemId: string;
  decision: ReviewDecision;
}

export type ExportFormat = "docx" | "pdf" | "txt" | "md";

export interface ExportDocumentResult {
  filename: string;
  mimeType: string;
  dataBase64: string;
  sizeBytes?: number;
  sha256?: string;
}

export interface ApplicationAdapter {
  health(): Promise<BackendHealth>;
  listDocuments(cursor?: string | null): Promise<DocumentPage>;
  getDocument(sessionId: string): Promise<DocumentRecord>;
  createDocument(request: CreateDocumentRequest): Promise<DocumentRecord>;
  updateDocument(request: UpdateDocumentRequest): Promise<DocumentRecord>;
  importDocument(request: ImportDocumentRequest): Promise<DocumentRecord>;
  reviewDocument(sessionId: string): Promise<ReviewJobResult>;
  getReviewItems(sessionId: string): Promise<ReviewItemsPage>;
  setReviewDecision(request: ReviewDecisionRequest): Promise<ReviewDecisionResult>;
  exportDocument(
    sessionId: string,
    format: ExportFormat,
    tracked?: boolean,
  ): Promise<ExportDocumentResult>;
  openDocumentFile(): Promise<NativeDocumentFile | null>;
  saveExportFile(result: ExportDocumentResult): Promise<string | null>;
}
