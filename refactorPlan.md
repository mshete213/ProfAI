# Plan: Remove Professor Role → Student-Only SaaS

## Context

The project is a RAG-powered course chatbot platform with a binary professor/student model. Professors create courses, ingest materials, and configure style; students enroll and chat. The goal is to collapse this into a student-owned model: each student creates their own "courses" (subject areas), ingests their own materials (slides, YouTube, Drive, Canvas, PDFs), and chats with their personal knowledge base. The MCP server expands from ingestion-only to also expose a `query_course` tool, making the student's knowledge base usable directly from Claude Desktop or any MCP-aware client.

---

## Architecture Changes

### What goes away
- `UserRole` enum (`PROFESSOR` / `STUDENT`) — all users are students
- `CourseEnrollment` table — students own courses directly, no enrollment needed
- `professor_id` on courses — replaced by `owner_id`
- `require_professor()` dependency — all authenticated users can ingest/manage
- Shared-secret internal API (`X-Internal-Key`, `/api/v1/internal/*`) — MCP auth moves to per-user API keys
- Professor UI pages and components
- Role selection on the register page

### What replaces them
- `owner_id: UUID` on `Course` → FK to the student who created it
- `api_key: str` on `User` → randomly-generated, used by MCP clients instead of shared secret
- New MCP tools: `query_course` and `list_my_courses`
- Student-facing ingestion UI (a new `CourseIngest` page under student routes)
- API key settings page in the web UI

---

## Implementation Steps

### 1. Database Models (`/backend/models/`)

**`user.py`**
- Delete `UserRole` enum (lines 11–13)
- Remove `role` column from `User`
- Remove `courses_owned` relationship
- Add `api_key = Column(String, unique=True, nullable=True)` field

**`course.py`**
- Rename `professor_id` → `owner_id`, point FK to `users.id`
- Rename relationship `professor` → `owner`, update `back_populates`
- Delete the `CourseEnrollment` model entirely

### 2. Database Migration (Alembic)

Create a new revision in `/backend/alembic/versions/`:
- `op.add_column('users', sa.Column('api_key', sa.String(), nullable=True))`
- `op.drop_column('users', 'role')`
- `op.drop_type('user_role')` (drop the PostgreSQL enum type)
- `op.alter_column('courses', 'professor_id', new_column_name='owner_id')`
- `op.drop_table('course_enrollments')`

### 3. Auth & Dependencies (`/backend/api/deps.py`, `/backend/api/routes/auth.py`, `/backend/core/security.py`)

**`deps.py`**
- Remove `require_professor()` and `require_student()` functions
- Update `get_current_user()` to accept **both** JWT (`Authorization: Bearer <jwt>`) and API key (`Authorization: Bearer <api_key>`):
  - Try JWT decode first
  - If it fails, look up `User` by `api_key` field
  - This is the only place that needs to change for a future OAuth migration

**`auth.py`**
- Remove `role` parameter from the registration request schema
- Remove role from JWT payload in `create_access_token()` / `create_refresh_token()` (in `security.py`)
- Add `POST /api/v1/users/me/api-key` endpoint: generates a `secrets.token_urlsafe(32)` key, stores it on the user, returns it once

**`security.py`**
- Drop `role` from the token subject dict

### 4. API Routes

**`courses.py`** (`/backend/api/routes/courses.py`)
- `GET /courses`: return courses where `owner_id == user.id` (remove the enrollment JOIN branch)
- `POST /courses`: any authenticated user can create (remove `require_professor`)
- `PUT/DELETE /courses/{id}`: check `course.owner_id == user.id` instead of professor dep
- Remove `POST /courses/{id}/enroll` endpoint

**`ingestion.py`** (`/backend/api/routes/ingestion.py`)
- Replace `professor: Annotated[User, Depends(require_professor)]` with `user: Annotated[User, Depends(get_current_user)]` on all endpoints
- Replace `_verify_course_owned()` (professor check) with the same logic checking `course.owner_id == user.id`
- Canvas: update `ingest_canvas` to use the requesting user's stored Canvas token (not a professor's)

**`chat.py`** (`/backend/api/routes/chat.py`)
- Simplify `_ensure_chat_access()`: only check `course.owner_id == user.id` (remove enrollment branch and professor branch)
- Remove `student_id` references — sessions now belong to the course owner

**`internal.py`** — **Delete this file entirely.** The MCP server will authenticate via user API keys through the standard routes. Remove `/api/v1/internal/*` from the router registration in `main.py`.

**`auth.py`** — add the API key generation endpoint described above.

### 5. Prompt Builder (`/backend/core/prompt_builder.py`)

Update system prompt text:
- Replace "The professor has reviewed these materials..." → "You are a personal study assistant..."
- Replace professor-centric framing with student-centric framing (e.g., "These are your course materials")

### 6. MCP Server (`/mcp_server/`)

**`server.py`**
- Replace `_headers()` (which adds `X-Internal-Key`) with `_headers(api_key: str)` that adds `Authorization: Bearer <api_key>`
- All tool calls must accept `api_key: str` as a parameter (students configure this in their MCP client config)
- Change all backend URLs from `/api/v1/internal/ingest/...` → `/api/v1/ingest/...` (standard authenticated routes)

**Add `query_course` tool:**
```python
@mcp.tool()
def query_course(api_key: str, course_id: str, question: str) -> str:
    """Query your study materials for a specific course."""
    r = httpx.post(f"{BACKEND_URL}/api/v1/chat/{course_id}",
                   headers={"Authorization": f"Bearer {api_key}"},
                   json={"message": question})
    return r.json()["response"]
```

**Add `list_my_courses` tool:**
```python
@mcp.tool()
def list_my_courses(api_key: str) -> list[dict]:
    """List all your study courses."""
    r = httpx.get(f"{BACKEND_URL}/api/v1/courses",
                  headers={"Authorization": f"Bearer {api_key}"})
    return r.json()
```

**Remove** the `ingest_canvas` tool's special-case "requires professor UI session" bailout — students can now authenticate Canvas directly.

**`watcher_tool.py`** — update the POST URL to `/api/v1/ingest/{course_id}/upload` with user API key header.

**Remove** `INTERNAL_MCP_API_KEY` env var from `docker-compose.yml` and config.

### 7. Frontend (`/frontend/src/`)

**Delete entirely:**
- `pages/professor/Dashboard.tsx`
- `pages/professor/CourseIngest.tsx`
- `pages/professor/CourseStyle.tsx`
- `components/professor/IngestForm.tsx`
- `components/professor/MaterialsList.tsx`
- `components/professor/StyleEditor.tsx`

**`lib/types.ts`**
- Change `UserRole = "professor" | "student"` → `UserRole = "student"` (or just remove the type and inline `"student"` where used)
- Add `api_key?: string` to the `User` type

**`pages/Register.tsx`**
- Remove the professor/student toggle buttons and the `role` state field
- Registration always creates a student

**`App.tsx`**
- Remove all `/professor/*` routes
- Change `<ProtectedRoute role="professor">` guards to plain `<ProtectedRoute>` (auth-only)
- Add route: `/student/courses/:courseId/ingest` → new `StudentCourseIngest` page
- Add route: `/settings/api-key` → new `ApiKeySettings` page

**`components/shared/ProtectedRoute.tsx`**
- Remove `role` prop; only check `isAuthenticated`

**`components/shared/Navbar.tsx`**
- Remove role badge

**New pages to create:**
- `pages/student/CourseIngest.tsx` — ingestion form (copy from `professor/CourseIngest.tsx`, adapt ownership checks)
- `pages/student/CourseCreate.tsx` — create a new course (currently professor-only)
- `pages/settings/ApiKeySettings.tsx` — show/regenerate API key for MCP use

**`pages/student/Courses.tsx`**
- Remove enrollment form (no longer needed)
- Add "Create course" button → links to `CourseCreate`
- Add "Add materials" button per course → links to `CourseIngest`

### 8. Config & Environment

**`/backend/config.py`**
- Remove `internal_mcp_api_key` setting

**`/docker-compose.yml`**
- Remove `INTERNAL_MCP_API_KEY` env var from `backend` and `mcp_server` services
- Add `BACKEND_URL` (public-facing URL) to `mcp_server` service for standard routes

---

## OAuth Migration Path (Future)

When ready to add OAuth: only `deps.py:get_current_user()` changes. The API-key branch becomes an OAuth token introspection call. No routes, tools, or frontend pages need to change because the `Authorization: Bearer <token>` header interface is identical.

---

## Verification

1. **Registration**: Register a new user — confirm no role field in request or response, `GET /users/me` returns no role.
2. **Course CRUD**: Create, update, delete a course as the registered student.
3. **Ingestion**: Upload a PDF to a course as that student; confirm Celery job completes and Pinecone has vectors.
4. **Chat (web UI)**: Chat with the course; confirm RAG retrieval returns relevant context.
5. **API key**: Hit `POST /api/v1/users/me/api-key`; confirm key is returned and stored.
6. **MCP query**: In MCP client config, set `api_key` to the generated key; call `query_course(course_id, "what is quicksort?")` — confirm it returns a grounded answer.
7. **MCP ingestion**: Call `ingest_youtube(api_key, course_id, url)` from MCP client — confirm job queued and materials appear.
8. **Access isolation**: Create two student accounts; confirm student B cannot GET/POST/DELETE on student A's courses (expect 403).
9. **No internal routes**: Confirm `GET /api/v1/internal/...` returns 404.
10. **Frontend**: Confirm professor pages 404, register page has no role toggle, student dashboard shows create/ingest buttons.
testestest