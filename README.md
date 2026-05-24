# ProfAI

AI-powered personal study platform where students build their own knowledge base from course materials and chat with an AI assistant grounded in their content.

## What it does

Students create courses (subject areas), ingest materials from multiple sources, and chat with a RAG-powered assistant that answers questions using only their uploaded content. A Chrome extension lets students ingest files directly from Canvas (and other LMS platforms) with a single click. The same knowledge base is also accessible from Claude Desktop or any MCP-aware client via a per-user API key.

## Prereqs

- Python 3.12+
- Node 20+
- Redis + PostgreSQL running locally (via Homebrew or Docker)

## Setup

```bash
./setup.sh        # or: make setup
```

This will:
1. Create `.env` from `.env.example` (if not present)
2. Create a Python virtualenv at `.venv/`
3. Install backend + MCP Python deps
4. Run `npm install` in `frontend/`

After it finishes, **edit `.env`** and paste your real API keys:
- `ANTHROPIC_API_KEY` — from https://console.anthropic.com
- `OPENAI_API_KEY` — from https://platform.openai.com
- `PINECONE_API_KEY` — from https://app.pinecone.io
- `JWT_SECRET` — any random 32+ char string

## Run the full stack

Three separate terminals from the project root:

```bash
make backend-run     # FastAPI on :8000
make worker-run      # Celery worker + beat
make frontend-run    # Vite on :3000
```

Then open:
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

The MCP server is optional: `make mcp-run`.

## Architecture at a glance

```
[Student]
    │
    ├── Browser (React + Vite) ──► FastAPI ─┬─► Postgres   (users, courses, jobs, sessions)
    │                                       ├─► Pinecone   (embedded course chunks)
    │                                       ├─► Anthropic  (Claude — chat responses)
    │                                       ├─► OpenAI     (text-embedding-3-small)
    │                                       └─► Celery + Redis
    │                                              │
    │                                              ├─ PDF / PPTX / DOCX parsing
    │                                              ├─ YouTube transcripts
    │                                              ├─ Google Drive ingestion
    │                                              └─ Canvas LMS sync
    │
    ├── Chrome Extension ──────► FastAPI (same backend)
    │    Intercepts clicks on Canvas file links (.pdf / .pptx / .docx),
    │    maps LMS courses to ProfAI courses (one-time per course),
    │    and ingests files in the background while the browser
    │    downloads them normally.
    │
    └── MCP Server ────────────► FastAPI (per-user API key auth)
         ├─ query_course        (query your knowledge base from any MCP client)
         ├─ list_my_courses
         ├─ ingest_google_drive
         ├─ ingest_youtube
         ├─ watch_folder        (auto-ingest from a local directory)
         └─ get_ingestion_status
```

## Chrome Extension setup

1. Open `chrome://extensions` and enable **Developer mode**
2. Click **Load unpacked** and select the `extension/` folder
3. Click the ProfAI icon in the toolbar
4. Enter your backend URL (`http://localhost:8000`) and your API key (from Settings → API Key in the web app)
5. Navigate to any Canvas course page — clicking a PDF, PPTX, or DOCX link will automatically ingest it into the mapped ProfAI course

## MCP setup (Claude Desktop)

1. Register and log in to the web app
2. Go to **Settings → API Key** and generate your key
3. Add to your Claude Desktop MCP config:

```json
{
  "mcpServers": {
    "profai": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "BACKEND_URL": "http://localhost:8000",
        "API_KEY": "<your-api-key>"
      }
    }
  }
}
```

## Verification path

1. Register an account at http://localhost:3000/register
2. Create a course on the dashboard
3. Upload a PDF via the course's Ingest page; watch the job progress to "completed"
4. Open the chat — ask a question answerable from the PDF and verify:
   - Streaming response appears word-by-word
   - Source citations match the PDF
5. Install the Chrome extension, navigate to a Canvas course, click a file link — verify the ingestion toast appears and the file shows up in your course materials
6. Go to Settings → API Key, generate a key, and call `query_course` from an MCP client

## Project structure

```
backend/        FastAPI + Celery + Alembic
mcp_server/     FastMCP server (query + ingestion tools)
frontend/       Vite + React + Tailwind
extension/      Chrome MV3 browser extension
projectPlan.md  Full architecture document
```
