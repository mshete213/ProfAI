from dataclasses import dataclass, field
from typing import Any

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")

MAX_CHUNK_TOKENS = 400
CHUNK_OVERLAP_TOKENS = 80
MIN_CHUNK_TOKENS = 50


@dataclass
class Chunk:
    text: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def _sliding_window(text: str, max_tokens: int, overlap: int) -> list[str]:
    tokens = _ENCODING.encode(text)
    if len(tokens) <= max_tokens:
        return [text]
    chunks = []
    step = max(1, max_tokens - overlap)
    for start in range(0, len(tokens), step):
        end = start + max_tokens
        window = tokens[start:end]
        if not window:
            break
        chunks.append(_ENCODING.decode(window))
        if end >= len(tokens):
            break
    return chunks


def chunk_by_paragraphs(
    text: str,
    extra_metadata: dict[str, Any] | None = None,
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
    min_tokens: int = MIN_CHUNK_TOKENS,
) -> list[Chunk]:
    """
    Split on double newlines first. Any paragraph exceeding max_tokens is sub-split via sliding window.
    Drops chunks below min_tokens.
    """
    extra_metadata = extra_metadata or {}
    if not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_tokens = 0

    def flush():
        nonlocal buffer, buffer_tokens
        if buffer:
            joined = "\n\n".join(buffer)
            tokens = count_tokens(joined)
            if tokens >= min_tokens:
                chunks.append(Chunk(text=joined, token_count=tokens, metadata=dict(extra_metadata)))
            buffer = []
            buffer_tokens = 0

    for paragraph in paragraphs:
        p_tokens = count_tokens(paragraph)

        if p_tokens > max_tokens:
            flush()
            for window in _sliding_window(paragraph, max_tokens, overlap):
                t = count_tokens(window)
                if t >= min_tokens:
                    chunks.append(Chunk(text=window, token_count=t, metadata=dict(extra_metadata)))
            continue

        if buffer_tokens + p_tokens > max_tokens:
            flush()

        buffer.append(paragraph)
        buffer_tokens += p_tokens

    flush()
    return chunks


def chunk_plain_text(
    text: str,
    extra_metadata: dict[str, Any] | None = None,
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
    min_tokens: int = MIN_CHUNK_TOKENS,
) -> list[Chunk]:
    """Pure sliding-window chunking (no paragraph awareness)."""
    extra_metadata = extra_metadata or {}
    if not text.strip():
        return []
    windows = _sliding_window(text, max_tokens, overlap)
    out = []
    for w in windows:
        t = count_tokens(w)
        if t >= min_tokens:
            out.append(Chunk(text=w, token_count=t, metadata=dict(extra_metadata)))
    return out
