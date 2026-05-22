from typing import Any

from config import get_settings
from core.chunker import count_tokens

settings = get_settings()

STATIC_SYSTEM_PROMPT = (
    "You are a personal study assistant. Your job is to help the user understand "
    "their own course material accurately. You ONLY answer questions using the "
    "provided COURSE CONTEXT. If the answer is not in the context, respond with: "
    "\"This isn't covered in your course materials.\" Never fabricate facts. Always "
    "cite the source filename and page/slide/timestamp you drew from, using inline "
    "references like [source: filename.pdf, p. 12]."
)


def build_system_blocks(course_name: str, style_instructions: str) -> list[dict[str, Any]]:
    """Two cache breakpoints: static block + per-course style block."""
    course_block_text = (
        f"COURSE: {course_name}\n\n"
        f"USER'S PREFERRED RESPONSE STYLE:\n{style_instructions or '(no specific style instructions provided)'}\n\n"
        "These are the user's own course materials. When answering, strictly follow "
        "the above style and format guidance."
    )
    return [
        {
            "type": "text",
            "text": STATIC_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": course_block_text,
            "cache_control": {"type": "ephemeral"},
        },
    ]


def format_chunks_for_prompt(chunks: list[dict[str, Any]]) -> str:
    """Build the COURSE CONTEXT block from retrieved Pinecone chunks."""
    if not chunks:
        return "(no relevant material retrieved)"

    parts = []
    for c in chunks:
        meta = c.get("metadata", {})
        filename = meta.get("filename", "unknown")
        locator = ""
        if meta.get("page_number"):
            locator = f"p. {meta['page_number']}"
        elif meta.get("slide_number"):
            locator = f"slide {meta['slide_number']}"
        elif meta.get("timestamp_start") is not None:
            t = int(meta["timestamp_start"])
            locator = f"t={t}s"
        header = f"[source: {filename}{', ' + locator if locator else ''}]"
        parts.append(f"{header}\n{meta.get('text', '')}")
    return "\n\n---\n\n".join(parts)


def trim_history_to_budget(history: list[dict[str, Any]], budget: int | None = None) -> list[dict[str, Any]]:
    """
    Token-budget approach: include as much history as fits, dropping only from the oldest end.
    Each history entry is {"role": "user"|"assistant", "content": str}.
    """
    if budget is None:
        budget = settings.history_token_budget
    if not history:
        return []
    total = 0
    trimmed: list[dict[str, Any]] = []
    for turn in reversed(history):
        tokens = count_tokens(turn.get("content", ""))
        if total + tokens > budget and trimmed:
            break
        trimmed.insert(0, turn)
        total += tokens
    return trimmed


def build_user_message(question: str, chunks: list[dict[str, Any]]) -> str:
    return f"COURSE CONTEXT (retrieved from your materials):\n\n{format_chunks_for_prompt(chunks)}\n\nQUESTION:\n{question}"
