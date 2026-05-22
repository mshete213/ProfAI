"""
Personal Study Assistant MCP Server.

Exposes tools that wrap the backend's per-user authenticated API. Each tool
accepts an `api_key` (generated from the web UI under Settings → API Key) and
forwards it as a bearer token to the backend.

Tools:
- list_my_courses
- query_course
- ingest_google_drive
- ingest_youtube
- ingest_canvas
- watch_folder / stop_watching_folder / list_watched_folders
- get_ingestion_status
"""
import os

import httpx
import structlog
from mcp.server.fastmcp import FastMCP

from tools.watcher_tool import start_watcher, stop_watcher, list_watchers

logger = structlog.get_logger()

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

mcp = FastMCP("PersonalStudyAssistant")


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


async def _post(endpoint: str, api_key: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(f"{BACKEND_URL}{endpoint}", json=payload, headers=_headers(api_key))
        r.raise_for_status()
        return r.json()


async def _get(endpoint: str, api_key: str) -> dict | list:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(f"{BACKEND_URL}{endpoint}", headers=_headers(api_key))
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def list_my_courses(api_key: str) -> list[dict]:
    """List all your study courses.

    Args:
        api_key: Your personal API key (generated in the web UI under Settings).
    """
    result = await _get("/api/v1/courses", api_key)
    return result if isinstance(result, list) else []


@mcp.tool()
async def query_course(api_key: str, course_id: str, question: str) -> dict:
    """Ask a question against your course's knowledge base.

    Args:
        api_key: Your personal API key.
        course_id: The course UUID (use list_my_courses to find it).
        question: Natural-language question.
    """
    return await _post(
        f"/api/v1/chat/{course_id}",
        api_key,
        {"question": question, "session_id": None},
    )


@mcp.tool()
async def ingest_google_drive(
    api_key: str,
    folder_id: str,
    course_id: str,
    oauth_token: str,
    recursive: bool = True,
) -> dict:
    """
    Pull all supported files (PDF, DOCX, PPTX, Google Docs/Slides) from a
    Google Drive folder and ingest them into the specified course namespace.

    Args:
        api_key: Your personal API key.
        folder_id: Google Drive folder ID (from share URL)
        course_id: Target course UUID
        oauth_token: OAuth2 access token for Drive (drive.readonly scope)
        recursive: Whether to recurse into subfolders (default True, max depth 5)
    """
    return await _post(
        f"/api/v1/ingest/{course_id}/drive",
        api_key,
        {"folder_id": folder_id, "oauth_token": oauth_token, "recursive": recursive},
    )


@mcp.tool()
async def ingest_youtube(api_key: str, url: str, course_id: str, language: str = "en") -> dict:
    """
    Fetch the transcript from a YouTube video, chunk into 60-second windows
    with 15-second overlap, embed, and upsert into Pinecone.

    Args:
        api_key: Your personal API key.
        url: Full YouTube URL (e.g. https://www.youtube.com/watch?v=...)
        course_id: Target course UUID
        language: Transcript language code (default 'en')
    """
    return await _post(
        f"/api/v1/ingest/{course_id}/youtube",
        api_key,
        {"url": url, "language": language},
    )


@mcp.tool()
async def ingest_canvas(
    api_key: str,
    course_id: str,
    canvas_domain: str,
    canvas_token: str,
    canvas_course_id: int,
) -> dict:
    """
    Connect a Canvas course and pull all current files + pages.

    Args:
        api_key: Your personal API key.
        course_id: Internal platform course UUID
        canvas_domain: Canvas instance domain (e.g. 'university.instructure.com')
        canvas_token: Your Canvas API token
        canvas_course_id: Numeric Canvas course ID
    """
    return await _post(
        f"/api/v1/ingest/{course_id}/canvas",
        api_key,
        {
            "canvas_domain": canvas_domain,
            "canvas_token": canvas_token,
            "canvas_course_id": canvas_course_id,
        },
    )


@mcp.tool()
async def watch_folder(
    api_key: str,
    path: str,
    course_id: str,
    file_extensions: list[str] | None = None,
) -> dict:
    """
    Start a watchdog observer on a local directory. New files matching the
    given extensions are automatically uploaded to the backend for ingestion.

    Args:
        api_key: Your personal API key.
        path: Absolute path to watch (must be accessible by MCP server container)
        course_id: Target course UUID for all discovered files
        file_extensions: List of extensions to watch (default: pdf, pptx, docx)
    """
    return start_watcher(
        path=path,
        course_id=course_id,
        file_extensions=file_extensions or [".pdf", ".pptx", ".docx"],
        backend_url=BACKEND_URL,
        api_key=api_key,
    )


@mcp.tool()
async def stop_watching_folder(path: str, course_id: str) -> dict:
    """Stop watching a previously-registered folder."""
    return stop_watcher(course_id, path)


@mcp.tool()
async def list_watched_folders() -> dict:
    """List all currently active folder watchers."""
    return {"watchers": list_watchers()}


@mcp.tool()
async def get_ingestion_status(api_key: str, job_id: str) -> dict:
    """Poll the status of a background ingestion job.

    Args:
        api_key: Your personal API key.
        job_id: Job ID returned by any ingest_* tool
    """
    result = await _get(f"/api/v1/ingest/jobs/{job_id}", api_key)
    return result if isinstance(result, dict) else {"result": result}


if __name__ == "__main__":
    logger.info("starting_mcp_server", backend=BACKEND_URL)
    mcp.run()
