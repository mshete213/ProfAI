import asyncio
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from core.chunker import Chunk, chunk_by_paragraphs

CANVAS_FILE_MIMES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


def _parse_link_header(link_header: str) -> dict[str, str]:
    """Parse RFC 5988 Link header into {rel: url}."""
    links = {}
    if not link_header:
        return links
    for part in link_header.split(","):
        section = part.strip().split(";")
        if len(section) < 2:
            continue
        url = section[0].strip()[1:-1]
        for s in section[1:]:
            m = re.search(r'rel="?([^"]+)"?', s.strip())
            if m:
                links[m.group(1)] = url
    return links


async def _paginated_get(client: httpx.AsyncClient, url: str, headers: dict) -> list[dict]:
    results: list[dict] = []
    next_url: str | None = url
    while next_url:
        resp = await client.get(next_url, headers=headers)
        resp.raise_for_status()
        results.extend(resp.json())
        next_url = _parse_link_header(resp.headers.get("Link", "")).get("next")
        await asyncio.sleep(0.1)  # rate-limit friendliness
    return results


async def check_webhook_compatibility(canvas_domain: str, canvas_token: str) -> bool:
    headers = {"Authorization": f"Bearer {canvas_token}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(
                f"https://{canvas_domain}/api/v1/webhooks_subscriptions", headers=headers
            )
        except httpx.HTTPError:
            return False
    return r.status_code == 200


async def register_webhook(
    canvas_domain: str,
    canvas_token: str,
    canvas_course_id: int,
    callback_url: str,
) -> str:
    payload = {
        "subscription": {
            "ContextType": "Course",
            "ContextId": str(canvas_course_id),
            "EventTypes": ["attachment_created", "wiki_page_updated"],
            "Format": "live-event",
            "TransportType": "https",
            "TransportMetadata": {"Url": callback_url},
        }
    }
    headers = {"Authorization": f"Bearer {canvas_token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            f"https://{canvas_domain}/api/v1/webhooks_subscriptions",
            json=payload,
            headers=headers,
        )
        r.raise_for_status()
    body = r.json()
    return str(body.get("id") or body.get("subscription", {}).get("id"))


async def list_course_files(canvas_domain: str, canvas_token: str, course_id: int) -> list[dict]:
    headers = {"Authorization": f"Bearer {canvas_token}"}
    content_filter = "&".join(f"content_types[]={m}" for m in CANVAS_FILE_MIMES.keys())
    url = (
        f"https://{canvas_domain}/api/v1/courses/{course_id}/files?per_page=50&{content_filter}"
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await _paginated_get(client, url, headers)


async def list_course_pages(canvas_domain: str, canvas_token: str, course_id: int) -> list[dict]:
    headers = {"Authorization": f"Bearer {canvas_token}"}
    url = f"https://{canvas_domain}/api/v1/courses/{course_id}/pages?per_page=50"
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await _paginated_get(client, url, headers)


async def fetch_page_body(
    canvas_domain: str, canvas_token: str, course_id: int, page_url: str
) -> dict:
    headers = {"Authorization": f"Bearer {canvas_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"https://{canvas_domain}/api/v1/courses/{course_id}/pages/{page_url}",
            headers=headers,
        )
        r.raise_for_status()
        return r.json()


async def download_file(file_url: str) -> bytes:
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        r = await client.get(file_url)
        r.raise_for_status()
        return r.content


def chunk_canvas_page(html_body: str, page_title: str, page_url: str) -> list[Chunk]:
    text = BeautifulSoup(html_body or "", "html.parser").get_text(separator="\n\n").strip()
    if not text:
        return []
    return chunk_by_paragraphs(
        text,
        extra_metadata={
            "filename": f"canvas-page-{page_title}",
            "title": page_title,
            "source_type": "canvas",
            "source_url": page_url,
        },
    )
