import { clearSession, getAccessToken } from "./auth";
import type {
  CanvasIngestResponse,
  ChatMessage,
  ChatResponse,
  Course,
  DocumentMeta,
  IngestionJob,
  TokenPair,
  UserRole,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const { auth = true, headers = {}, ...rest } = options;
  const finalHeaders: Record<string, string> = { ...(headers as Record<string, string>) };

  if (auth) {
    const token = getAccessToken();
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  if (rest.body && !(rest.body instanceof FormData) && !finalHeaders["Content-Type"]) {
    finalHeaders["Content-Type"] = "application/json";
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...rest, headers: finalHeaders });

  if (resp.status === 401 && auth) {
    clearSession();
    window.location.href = "/login";
    throw new ApiError(401, "Unauthorized");
  }

  if (!resp.ok) {
    const text = await resp.text();
    let detail = text;
    try {
      detail = JSON.parse(text).detail ?? text;
    } catch {
      /* ignore */
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  // Auth
  register: (data: { email: string; password: string; name: string; role: UserRole }) =>
    request<TokenPair>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(data), auth: false }),
  login: (data: { email: string; password: string }) =>
    request<TokenPair>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(data), auth: false }),

  // Courses
  listCourses: () => request<Course[]>("/api/v1/courses"),
  createCourse: (data: { name: string; description?: string; style_instructions?: string }) =>
    request<Course>("/api/v1/courses", { method: "POST", body: JSON.stringify(data) }),
  getCourse: (id: string) => request<Course>(`/api/v1/courses/${id}`),
  updateCourse: (id: string, data: Partial<{ name: string; description: string; style_instructions: string }>) =>
    request<Course>(`/api/v1/courses/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteCourse: (id: string) => request<void>(`/api/v1/courses/${id}`, { method: "DELETE" }),
  enrollInCourse: (id: string) => request<void>(`/api/v1/courses/${id}/enroll`, { method: "POST" }),

  // Ingestion
  uploadFiles: (courseId: string, files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return request<{ job_id: string; status: string }>(
      `/api/v1/ingest/${courseId}/upload`,
      { method: "POST", body: fd }
    );
  },
  ingestYoutube: (courseId: string, url: string, language = "en") =>
    request<{ job_id: string; status: string }>(`/api/v1/ingest/${courseId}/youtube`, {
      method: "POST",
      body: JSON.stringify({ url, language }),
    }),
  ingestDrive: (courseId: string, folderId: string, oauthToken: string, recursive = true) =>
    request<{ job_id: string; status: string }>(`/api/v1/ingest/${courseId}/drive`, {
      method: "POST",
      body: JSON.stringify({ folder_id: folderId, oauth_token: oauthToken, recursive }),
    }),
  ingestCanvas: (
    courseId: string,
    data: { canvas_domain: string; canvas_token: string; canvas_course_id: number }
  ) =>
    request<CanvasIngestResponse>(`/api/v1/ingest/${courseId}/canvas`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  enableCanvasWebhooks: (courseId: string) =>
    request<{ status: string; subscription_id: string }>(
      `/api/v1/ingest/${courseId}/canvas/enable-webhooks`,
      { method: "POST" }
    ),
  getJob: (jobId: string) => request<IngestionJob>(`/api/v1/ingest/jobs/${jobId}`),
  listMaterials: (courseId: string) => request<DocumentMeta[]>(`/api/v1/ingest/${courseId}/materials`),
  deleteMaterial: (courseId: string, docId: string) =>
    request<void>(`/api/v1/ingest/${courseId}/materials/${docId}`, { method: "DELETE" }),

  // Chat
  chat: (courseId: string, question: string, sessionId?: string) =>
    request<ChatResponse>(`/api/v1/chat/${courseId}`, {
      method: "POST",
      body: JSON.stringify({ question, session_id: sessionId }),
    }),
  chatStream: async function* (
    courseId: string,
    question: string,
    sessionId?: string
  ): AsyncGenerator<{ event: string; data: any }> {
    const token = getAccessToken();
    const resp = await fetch(`${API_BASE}/api/v1/chat/${courseId}/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ question, session_id: sessionId }),
    });
    if (!resp.ok || !resp.body) throw new ApiError(resp.status, await resp.text());
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const segments = buf.split("\n\n");
      buf = segments.pop() ?? "";
      for (const seg of segments) {
        if (!seg.trim()) continue;
        let event = "message";
        let data = "";
        for (const line of seg.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data += line.slice(5).trim();
        }
        try {
          yield { event, data: JSON.parse(data) };
        } catch {
          yield { event, data };
        }
      }
    }
  },
  getChatHistory: (courseId: string, sessionId: string) =>
    request<ChatMessage[]>(`/api/v1/chat/${courseId}/history?session_id=${sessionId}`),
  deleteChatSession: (sessionId: string) =>
    request<void>(`/api/v1/chat/sessions/${sessionId}`, { method: "DELETE" }),
};
