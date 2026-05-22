export type UserRole = "professor" | "student";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface Course {
  id: string;
  name: string;
  description: string | null;
  style_instructions: string | null;
  professor_id: string;
  created_at: string;
  updated_at: string;
  document_count?: number;
  enrollment_count?: number;
}

export type SourceType = "pdf" | "pptx" | "docx" | "youtube" | "drive" | "canvas";
export type JobStatus = "queued" | "running" | "completed" | "failed" | "skipped_duplicate";

export interface IngestionJob {
  id: string;
  course_id: string;
  source_type: SourceType;
  status: JobStatus;
  total_items: number;
  processed_items: number;
  failed_items: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface DocumentMeta {
  id: string;
  course_id: string;
  filename: string;
  title: string | null;
  source_type: SourceType;
  source_url: string | null;
  content_hash: string;
  chunk_count: number;
  ingested_at: string;
}

export interface ChatSource {
  filename?: string;
  title?: string;
  page_number?: number;
  slide_number?: number;
  timestamp_start?: number;
  timestamp_end?: number;
  source_url?: string;
  text?: string;
  source_type?: SourceType;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  session_id: string;
  tokens_used: {
    input: number;
    output: number;
    cache_read: number;
    cache_creation: number;
  };
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  sources: ChatSource[] | null;
  tokens_used: Record<string, number> | null;
  created_at: string;
}

export interface CanvasIngestResponse {
  job_id: string;
  status: JobStatus;
  webhook_compatible: boolean;
}
