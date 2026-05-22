# EdTech RAG Platform

AI-powered edTech SaaS where professors upload course materials and students get tailored answers via RAG.

See `projectPlan.md` for the full architecture and design decisions.

## Who installs what

This is a **web SaaS**, so end users (professors and students) never install anything — they just visit the app in a browser. The setup steps below are for developers running the stack locally, and for ops deploying it to a server.

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
[Student/Professor]
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
                                             └─ Canvas LMS sync (polling + webhook)

  MCP Server ──► FastAPI (X-Internal-Key auth)
   ├─ ingest_google_drive
   ├─ ingest_youtube
   ├─ ingest_canvas (documentation; pro UI required)
   ├─ watch_folder (auto-ingest from a directory)
   └─ get_ingestion_status
```

## Verification path

1. Register a professor account at http://localhost:3000/register
2. Create a course on the dashboard
3. Upload a PDF in the course's Materials page; watch the job progress to "completed"
4. Open the course's Style page and add response style instructions
5. Register a student account, enroll in the course via its UUID
6. Open the chat — ask a question that's answerable from the PDF. Verify:
   - Streaming response appears word-by-word
   - Source citations match the PDF
   - Style matches the professor's instructions

## Project structure

```
backend/        FastAPI + Celery + Alembic
mcp_server/     FastMCP autonomous ingestion server
frontend/       Vite + React + Tailwind
docker-compose.yml
projectPlan.md  Full architecture document
```
