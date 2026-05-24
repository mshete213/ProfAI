# ProfAI

AI-powered personal study platform where students build their own knowledge base from course materials and chat with an AI assistant grounded in their content.

See `projectPlan.md` for the full architecture and design decisions.

## What it does

Students create courses (subject areas), ingest materials from multiple sources, and chat with a RAG-powered assistant that answers questions using only their uploaded content. The same knowledge base is also accessible directly from Claude Desktop or any MCP-aware client via a per-user API key.

## Prereqs

- Python 3.12+
- Node 20+
- Docker Desktop (for `make up` — the easiest path)

## One-command setup

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

```bash
make up           # docker compose up -d
```

Then open:
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

Tail logs with `make logs`. Stop with `make down`.

## Local dev (without Docker)

Need Postgres + Redis running locally (or `docker compose up -d postgres redis`), then in three terminals:

```bash
make backend-run     # FastAPI on :8000
make worker-run      # Celery worker + beat
make frontend-run    # Vite on :3000
```

The MCP server is optional for local dev: `make mcp-run`.

## Architecture at a glance

```
[Student]
    │
    ▼
React + Vite ─── HTTPS ──► FastAPI ─┬─► Postgres   (users, courses, jobs, sessions)
                                    ├─► Pinecone   (embedded course chunks)
                                    ├─► Anthropic  (Claude with prompt caching)
                                    ├─► OpenAI     (embeddings)
                                    └─► Celery + Redis
                                           │
                                           ├─ PDF/PPTX/DOCX parsing
                                           ├─ YouTube transcripts
                                           ├─ Google Drive ingestion
                                           └─ Canvas LMS sync

MCP Server ──► FastAPI (per-user API key auth)
 ├─ query_course        (query your knowledge base from any MCP client)
 ├─ list_my_courses     (list your courses)
 ├─ ingest_google_drive
 ├─ ingest_youtube
 ├─ watch_folder        (auto-ingest from a local directory)
 └─ get_ingestion_status
```

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

You can then call `query_course`, `list_my_courses`, and ingestion tools directly from Claude.

## Verification path

1. Register an account at http://localhost:3000/register
2. Create a course on the dashboard
3. Upload a PDF via the course's Ingest page; watch the job progress to "completed"
4. Open the chat — ask a question answerable from the PDF and verify:
   - Streaming response appears word-by-word
   - Source citations match the PDF
5. Go to Settings → API Key, generate a key, and call `query_course` from an MCP client

## Project structure

```
backend/        FastAPI + Celery + Alembic
mcp_server/     FastMCP server (query + ingestion tools)
frontend/       Vite + React + Tailwind
docker-compose.yml
projectPlan.md  Full architecture document
```
