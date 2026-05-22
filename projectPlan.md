# AI EdTech Platform — Implementation Plan

## Context
Build an AI-powered edTech SaaS from scratch. Professors upload course materials; students ask questions and get solutions that match the professor's expected format and style. The platform uses RAG over embedded course materials (Pinecone) and Claude API to generate tailored answers. Ingestion is autonomous via a custom MCP server that connects to Google Drive, YouTube, Canvas LMS, and a watched local folder.

---

## Tech Stack
| Layer | Choice |
|-------|--------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Vector DB | Pinecone (`text-embedding-3-small` @ 1536 dims, `cosine`) |
| LLM | Claude `claude-sonnet-4-6` with two-level prompt caching |
| Embeddings | OpenAI `text-embedding-3-small` |
| Frontend | React + Vite, Tailwind, shadcn/ui |
| DB | PostgreSQL (via SQLAlchemy + Alembic) |
| Queue | Celery + Redis (async ingestion jobs) |
| MCP | FastMCP Python SDK |
| Ingestion | Google Drive API, YouTube Transcript API, Canvas REST API, watchdog |

---

## Project Directory Structure

```
edtech-platform/
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── main.py
│   ├── config.py                     # Pydantic settings from env vars
│   ├── requirements.txt
│   ├── api/
│   │   ├── deps.py                   # DI: DB session, current user
│   │   └── routes/
│   │       ├── auth.py               # POST /auth/register, /auth/login, /auth/refresh
│   │       ├── courses.py            # CRUD /courses
│   │       ├── ingestion.py          # POST /ingest/{course_id}/upload|drive|youtube|canvas
│   │       ├── chat.py               # POST /chat/{course_id}, SSE stream
│   │       └── professor.py          # Style config, analytics
│   ├── core/
│   │   ├── chunker.py                # Chunking strategies per source type
│   │   ├── embedder.py               # OpenAI embedding wrapper
│   │   ├── pinecone_client.py        # Upsert/query helpers
│   │   ├── rag_pipeline.py           # RAG orchestrator (embed → retrieve → generate)
│   │   ├── prompt_builder.py         # Two-level cached system prompt assembly
│   │   └── celery_app.py             # Celery app + task definitions
│   ├── ingestion/
│   │   ├── pdf_parser.py             # PyMuPDF: PDF → text + page metadata
│   │   ├── pptx_parser.py            # python-pptx: slide text + speaker notes
│   │   ├── youtube_ingestor.py       # youtube-transcript-api + 60-sec windowed chunks
│   │   ├── drive_ingestor.py         # Google Drive API: list, download, export
│   │   ├── canvas_ingestor.py        # Canvas REST API: files + pages
│   │   └── folder_watcher.py         # watchdog observer thread
│   ├── models/
│   │   ├── db.py                     # SQLAlchemy Base + engine
│   │   ├── user.py, course.py, document.py, chat_session.py
│   └── schemas/
│       ├── auth.py, course.py, ingestion.py, chat.py
│
├── mcp_server/
│   ├── server.py                     # FastMCP entrypoint
│   └── tools/
│       ├── drive_tool.py, youtube_tool.py, canvas_tool.py, watcher_tool.py
│
└── frontend/
    ├── index.html
    ├── vite.config.ts
    ├── src/
    │   ├── main.tsx                  # app entry point
    │   ├── App.tsx                   # React Router route definitions
    │   ├── pages/
    │   │   ├── Login.tsx
    │   │   ├── Register.tsx
    │   │   ├── professor/
    │   │   │   ├── Dashboard.tsx
    │   │   │   ├── CourseIngest.tsx
    │   │   │   └── CourseStyle.tsx
    │   │   └── student/
    │   │       ├── Courses.tsx
    │   │       └── Chat.tsx
    │   ├── components/
    │   │   ├── chat/ChatWindow, MessageBubble, ChatInput, SourceCitations
    │   │   └── professor/IngestForm (tabbed), StyleEditor, MaterialsList
    │   ├── hooks/useChat.ts, useCourses.ts
    │   └── lib/api.ts, auth.ts, types.ts
```

---

## FastAPI Routes

### Auth (`/api/v1/auth`)
- `POST /register` — `{email, password, role, name}` → `{user_id, token}`
- `POST /login` — `{email, password}` → `{access_token, refresh_token, user}`
- `POST /refresh` — `{refresh_token}` → `{access_token}`

### Courses (`/api/v1/courses`)
- `GET/POST /courses` — list all | create new
- `GET/PUT/DELETE /courses/{course_id}` — detail | update | delete
- `POST /courses/{course_id}/enroll` — student enrollment

### Ingestion (`/api/v1/ingest`)
- `POST /ingest/{course_id}/upload` — `multipart: files[]` → `{job_id}`
- `POST /ingest/{course_id}/drive` — `{folder_id, oauth_token}` → `{job_id}`
- `POST /ingest/{course_id}/youtube` — `{url}` → `{job_id}`
- `POST /ingest/{course_id}/canvas` — `{canvas_domain, canvas_token, canvas_course_id}` → `{job_id, webhook_compatible: bool}`
- `POST /ingest/{course_id}/canvas/enable-webhooks` — register webhook subscription, set `sync_mode="webhook"`
- `POST /webhooks/canvas` — receive incoming Canvas webhook events (no auth, signature-verified)
- `GET /ingest/jobs/{job_id}` — poll status/progress
- `GET/DELETE /ingest/{course_id}/materials/{doc_id}` — list | remove

### Chat (`/api/v1/chat`)
- `POST /chat/{course_id}` — `{question, session_id?}` → `{answer, sources, tokens_used}`
- `POST /chat/{course_id}/stream` — same, returns SSE (`text/event-stream`)
- `GET /chat/{course_id}/history` — session history

---

## Pinecone Schema

**Index**: `edtech-prod`, dimension `1536`, metric `cosine`
**Namespace per course**: `course-{course_id}`

**Metadata per vector**:
```python
{
    "chunk_id":        "doc_abc_chunk_004",
    "doc_id":          "doc_abc",
    "course_id":       "cs101",
    "source_type":     "pdf" | "pptx" | "youtube" | "drive" | "canvas" | "docx",
    "filename":        "week3_lecture.pdf",
    "title":           "Week 3: Sorting Algorithms",
    "chunk_index":     4,
    "chunk_total":     18,
    "page_number":     12,       # null for non-PDF
    "slide_number":    null,     # null for non-PPTX
    "timestamp_start": null,     # float seconds, YouTube only
    "timestamp_end":   null,
    "text":            "Quicksort works by...",
    "token_count":     312,
    "ingested_at":     "2026-05-21T10:30:00Z",
    "content_hash":    "sha256:abc123",   # dedup key
}
```

---

## Chunking Strategy

| Source | Strategy |
|--------|----------|
| PDF | PyMuPDF page text → split on double newlines → sliding window at 400 tokens (80-token overlap) if needed. Preserve page number. |
| PPTX | One chunk per slide (title + text frames + `[Notes]: ...`). Split at sentence boundary only if >400 tokens. |
| YouTube | Group transcript segments into 60-second windows, 15-second overlap. Store timestamp range. |
| Canvas pages | Strip HTML with BeautifulSoup → treat as plain text → paragraph-chunk like PDF. |
| DOCX | Extract paragraphs → same window strategy as PDF. |

Token counting: `tiktoken` with `cl100k_base`. Minimum chunk size: 50 tokens.

---

## RAG Pipeline (`backend/core/rag_pipeline.py`)

```python
async def query(course_id, question, session_id):
    # 1. Embed question (OpenAI text-embedding-3-small)
    q_vec = await embedder.embed(question)

    # 2. Pinecone query in course namespace, threshold 0.72
    chunks = pinecone_index.query(
        namespace=f"course-{course_id}",
        vector=q_vec, top_k=8, include_metadata=True,
        filter={"course_id": {"$eq": course_id}}
    )
    chunks = [m for m in chunks.matches if m.score > 0.72]

    # 3. Build two-level cached prompt (see below)
    # 4. Call Claude claude-sonnet-4-6, temperature=0.2, max_tokens=2048
    # 5. Persist turn to DB, return {answer, sources, tokens_used}
```

---

## Claude Prompt Structure with Caching (`backend/core/prompt_builder.py`)

Two cache breakpoints in the `system` array:

```python
system = [
    {
        # Cache point 1: static across ALL requests on the platform
        "type": "text",
        "text": "You are an AI teaching assistant... only answer from course context... cite sources...",
        "cache_control": {"type": "ephemeral"}
    },
    {
        # Cache point 2: static per course (reused for all student queries in a course)
        "type": "text",
        "text": f"COURSE: {course_name}\nPROFESSOR STYLE:\n{style_instructions}",
        "cache_control": {"type": "ephemeral"}
    }
]
messages = [
    *chat_history,  # full session history, trimmed by token budget (see below)
    {
        "role": "user",
        "content": f"COURSE CONTEXT:\n{joined_chunks}\n\nQUESTION:\n{question}"
    }
]
```

Cache savings: ~100-200 tokens/request from static block; 300-800 tokens/request from per-course style block.

### Chat History Strategy

Full history is always stored in the DB. What gets sent to Claude uses a **token-budget approach** rather than a fixed turn cutoff — this ensures students can reference any earlier question or answer within the same session:

```python
# backend/core/prompt_builder.py

HISTORY_TOKEN_BUDGET = 4000  # tokens reserved for chat history in context

def trim_history_to_budget(history: list[dict], budget: int) -> list[dict]:
    """
    Include as much history as fits within the token budget.
    Drops from the oldest end only — recent exchanges are always preserved.
    """
    total = 0
    trimmed = []
    for turn in reversed(history):
        tokens = count_tokens(turn["content"])
        if total + tokens > budget:
            break
        trimmed.insert(0, turn)
        total += tokens
    return trimmed
```

A typical study session of 20–30 exchanges (~3,000–4,000 tokens) fits entirely. Only unusually long sessions get trimmed, and only from the oldest end.

**Session persistence:**
- `session_id` is stored in `localStorage` on the frontend — refreshing the page reloads the same session
- `ChatWindow` calls `GET /chat/{course_id}/history?session_id=` on mount to restore the full visible history
- A "New Chat" button clears `localStorage` session ID and calls `DELETE /chat/sessions/{session_id}`

---

## MCP Server (`mcp_server/server.py`)

FastMCP server running as a separate Docker service. Calls FastAPI internal endpoints via `httpx` with `X-Internal-Key` header (bypasses JWT).

**Tools exposed**:
```python
@mcp.tool()
async def ingest_google_drive(folder_id, course_id, oauth_token, recursive=True) -> dict
    # → POST /api/v1/ingest/{course_id}/drive

@mcp.tool()
async def ingest_youtube(url, course_id, language="en") -> dict
    # → POST /api/v1/ingest/{course_id}/youtube

@mcp.tool()
async def ingest_canvas(course_id, canvas_domain, canvas_token, canvas_course_id) -> dict
    # → POST /api/v1/ingest/{course_id}/canvas

@mcp.tool()
async def watch_folder(path, course_id, file_extensions=[".pdf",".pptx",".docx"]) -> dict
    # Starts a watchdog Observer thread; on new file → POST upload endpoint

@mcp.tool()
async def get_ingestion_status(job_id) -> dict
    # → GET /api/v1/ingest/jobs/{job_id}
```

---

## Canvas LMS Integration (`backend/ingestion/canvas_ingestor.py`)

- **Auth**: `Authorization: Bearer {canvas_token}` header
- **Files**: `GET /api/v1/courses/{id}/files?content_types[]=application/pdf&...` → paginate via `Link` header → download via pre-signed `url` field
- **Pages**: `GET /api/v1/courses/{id}/pages` → fetch each `body` (HTML) → strip with BeautifulSoup
- **Pagination**: `asyncio.sleep(0.1)` between calls (Canvas rate limit: 700 req/hr)

### Canvas Sync Strategy

**Default (Option A) — Celery Beat periodic polling:**

A Celery Beat task re-polls every Canvas-connected course on a 6-hour schedule. The `content_hash` dedup ensures only new or changed files are re-embedded — unchanged files are skipped without any embedding calls.

```python
# backend/core/celery_app.py
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Re-sync all Canvas-connected courses every 6 hours
    sender.add_periodic_task(
        crontab(minute=0, hour="*/6"),
        sync_all_canvas_courses.s(),
    )

@celery.task
def sync_all_canvas_courses():
    courses = db.get_courses_with_canvas_connection(sync_mode="polling")
    for course in courses:
        canvas_ingestor.sync(course)   # skips unchanged files via content_hash
```

Store per-course Canvas credentials in the `CanvasConnection` DB table:
```python
class CanvasConnection(Base):
    course_id: str
    canvas_domain: str
    canvas_token: str          # encrypted at rest
    canvas_course_id: int
    sync_mode: str             # "polling" | "webhook"
    webhook_subscription_id: str | None
    last_synced_at: datetime
```

---

**Upgrade path (Option B) — Real-time webhooks:**

On initial Canvas connection, run a compatibility check before falling back to polling:

```python
# backend/ingestion/canvas_ingestor.py

async def check_webhook_compatibility(canvas_domain: str, canvas_token: str) -> bool:
    """Returns True if this Canvas instance supports webhook subscriptions."""
    headers = {"Authorization": f"Bearer {canvas_token}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://{canvas_domain}/api/v1/webhooks_subscriptions",
            headers=headers
        )
    return r.status_code == 200   # 404 = not available; 200 = available

async def register_webhook(canvas_domain, canvas_token, canvas_course_id, callback_url) -> str:
    """Registers an HTTP webhook subscription. Returns subscription_id."""
    payload = {
        "subscription": {
            "ContextType": "Course",
            "ContextId": canvas_course_id,
            "EventTypes": ["attachment_created", "wiki_page_updated"],
            "Format": "live-event",
            "TransportType": "https",
            "TransportMetadata": {"Url": callback_url}
        }
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://{canvas_domain}/api/v1/webhooks_subscriptions",
            json=payload,
            headers={"Authorization": f"Bearer {canvas_token}"}
        )
        r.raise_for_status()
    return r.json()["id"]
```

New backend route to receive incoming webhook events:
```
POST /webhooks/canvas  →  verify signature → queue Celery ingestion job for the specific file
```

---

**Connection flow (backend route `POST /ingest/{course_id}/canvas`):**

```
1. Save canvas credentials to CanvasConnection (sync_mode="polling" initially)
2. Trigger immediate full sync (Celery job)
3. Run check_webhook_compatibility()
4. Return {job_id, webhook_compatible: bool} to frontend
```

**Frontend behavior after Canvas connection:**

- If `webhook_compatible: false` → show "Syncing every 6 hours" status badge. No prompt.
- If `webhook_compatible: true` → show upgrade prompt:

  > "Your institution supports real-time sync. Enable it and Canvas will push new materials instantly instead of syncing every 6 hours."
  > [Enable real-time sync] [Keep polling]

- If professor clicks "Enable real-time sync" → `POST /ingest/{course_id}/canvas/enable-webhooks` → registers subscription, updates `sync_mode` to `"webhook"` in DB, Celery Beat skips this course going forward.

---

## Google Drive Integration (`backend/ingestion/drive_ingestor.py`)

- OAuth2 with `drive.readonly` scope; store refresh token encrypted in DB
- List files: `service.files().list(q="'{folder_id}' in parents and trashed=false", fields="id,name,mimeType")`
- Google Docs → export as DOCX; Google Slides → export as PPTX
- Binary files → `get_media(fileId=...)`
- Dedup by SHA-256 of bytes against `content_hash` in Document table
- Recursive subfolder traversal with depth limit of 5

---

## Key Backend Dependencies (requirements.txt)

```
fastapi==0.115.5  uvicorn[standard]==0.32.1
sqlalchemy==2.0.36  alembic==1.14.0  psycopg2-binary==2.9.10
python-jose[cryptography]==3.3.0  passlib[bcrypt]==1.7.4  python-multipart==0.0.12
anthropic==0.40.0  openai==1.56.2  pinecone-client==5.0.1
pymupdf==1.25.1  python-pptx==1.0.2  python-docx==1.1.2  tiktoken==0.8.0
youtube-transcript-api==0.6.3
google-api-python-client==2.149.0  google-auth==2.36.0  google-auth-oauthlib==1.2.1
httpx==0.28.1  mcp==1.3.0  fastmcp==2.2.4  watchdog==6.0.0
celery==5.4.0  redis==5.2.0
pydantic==2.10.3  pydantic-settings==2.6.1  tenacity==9.0.0  structlog==24.4.0
beautifulsoup4==4.12.3
```

---

## Key Frontend Dependencies (package.json)

```
react@18, react-dom@18
vite@5, @vitejs/plugin-react
react-router-dom@6
tailwindcss@3, @tailwindcss/typography
shadcn/ui (radix-ui primitives), lucide-react
react-markdown, remark-gfm, rehype-highlight
react-hook-form, zod, @hookform/resolvers
swr, jose, js-cookie
```

---

## Frontend Page Structure

Routing via React Router v6. All routes are client-side — FastAPI serves all data.

**Professor**:
- `/professor/dashboard` — course grid with stats
- `/professor/courses/:courseId/ingest` — `IngestForm` (4 tabs: Upload / Google Drive / YouTube / Canvas)
- `/professor/courses/:courseId/style` — `StyleEditor` (free-text style instructions + example Q&A pairs)

**Student**:
- `/student/courses` — enrolled course list
- `/student/courses/:courseId/chat` — `ChatWindow` with streaming SSE, markdown rendering, collapsible `SourceCitations`

**Auth**:
- `/login`, `/register` — form pages, redirect to role-appropriate dashboard on success

---

## Docker Compose Services

| Service | Port | Notes |
|---------|------|-------|
| `backend` | 8000 | FastAPI, `--reload` in dev |
| `worker` | — | Celery worker, 4 concurrency |
| `mcp_server` | — | FastMCP server |
| `frontend` | 3000 | Vite dev server |
| `postgres` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 (Celery broker) |

Shared volumes: `uploaded_files` (backend ↔ worker), `watch_folder` (backend ↔ mcp_server).

---

## Verification Plan

1. **Infrastructure**: `docker compose up postgres redis` → `alembic upgrade head` → verify tables
2. **Auth**: Register professor + student, get JWT, create a course
3. **Ingestion**: Upload a PDF → poll job until `completed` → verify vectors in Pinecone console
4. **Dedup**: Re-upload same PDF → expect `skipped_duplicate`
5. **YouTube**: Ingest a YouTube URL → confirm `source_type:youtube` chunks in Pinecone
6. **RAG**: `POST /chat/{course_id}` with a relevant question → answer must cite filename/page and follow professor style
7. **Cache**: Second query → `tokens_used.cache_read > 0`
8. **SSE streaming**: `curl -N` the stream endpoint → chunked response visible
9. **MCP**: Start mcp_server → call `ingest_youtube` tool → verify job queued
10. **Folder watcher**: Drop a PDF into watched volume → verify auto-ingested within 10 seconds
11. **Canvas polling**: Connect a Canvas course → verify `sync_mode="polling"` in DB → wait for Celery Beat tick → confirm new files ingested
12. **Canvas webhook compatibility check**: Connect Canvas with an admin token on a compatible instance → verify `webhook_compatible: true` returned → confirm upgrade prompt appears in frontend
13. **Canvas webhook upgrade**: Click "Enable real-time sync" → verify `sync_mode="webhook"` in DB + `webhook_subscription_id` populated → upload a file to Canvas → confirm ingestion triggered within 30 seconds via `POST /webhooks/canvas`
14. **Canvas webhook incompatible instance**: Connect Canvas with a token from a non-Data-Services instance → verify `webhook_compatible: false` → confirm no prompt shown, polling badge displayed
15. **Frontend E2E**: Professor uploads PDF, sets style instructions; student asks question and gets styled streaming answer with citations
12. **Authorization**: Student querying a non-enrolled course → `403 Forbidden`
13. **Large PDF**: 300-page textbook → completes under 5 minutes, no OOM
14. **No-context fallback**: Ask off-topic question → receives configured fallback message

---

## Implementation Order (Critical Path)

1. Docker Compose + Postgres + Alembic models
2. Auth routes (JWT)
3. Course CRUD
4. Core: `embedder.py` + `pinecone_client.py`
5. `chunker.py` + `pdf_parser.py` — simplest ingestor first
6. Celery job infrastructure + `ingestion.py` upload route
7. `rag_pipeline.py` + `prompt_builder.py` + `chat.py` — working RAG query
8. Remaining ingestors: pptx, youtube, canvas, drive
9. MCP server with all 5 tools
10. Next.js frontend: auth → professor dashboard → student chat
