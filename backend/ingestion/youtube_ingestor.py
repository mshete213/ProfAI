import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi

from core.chunker import Chunk, count_tokens

WINDOW_SECONDS = 60.0
OVERLAP_SECONDS = 15.0


def extract_video_id(url: str) -> str:
    """Accepts standard youtube.com/watch?v=, youtu.be/, and youtube.com/embed/ formats."""
    parsed = urlparse(url)
    if parsed.hostname in ("youtu.be",):
        return parsed.path.lstrip("/")
    if parsed.hostname and "youtube.com" in parsed.hostname:
        if parsed.path == "/watch":
            q = parse_qs(parsed.query)
            return q.get("v", [""])[0]
        m = re.match(r"^/embed/([\w-]+)", parsed.path)
        if m:
            return m.group(1)
        m = re.match(r"^/shorts/([\w-]+)", parsed.path)
        if m:
            return m.group(1)
    if re.match(r"^[A-Za-z0-9_-]{11}$", url):
        return url
    raise ValueError(f"Could not extract YouTube video ID from: {url}")


def fetch_transcript(video_id: str, language: str = "en") -> list[dict]:
    """Returns [{text, start, duration}, ...]."""
    return YouTubeTranscriptApi.get_transcript(video_id, languages=[language, "en"])


def chunk_youtube_transcript(
    segments: list[dict],
    video_id: str,
    title: str,
    url: str,
) -> list[Chunk]:
    if not segments:
        return []

    chunks: list[Chunk] = []
    window_start = segments[0]["start"]
    window_end = window_start + WINDOW_SECONDS
    buffer_text: list[str] = []
    buffer_seg_start = window_start
    buffer_seg_end = window_start

    def flush(start: float, end: float, text_parts: list[str]):
        text = " ".join(text_parts).strip()
        if not text:
            return
        tokens = count_tokens(text)
        if tokens < 10:
            return
        chunks.append(
            Chunk(
                text=text,
                token_count=tokens,
                metadata={
                    "filename": f"{video_id}.youtube",
                    "title": title,
                    "source_type": "youtube",
                    "source_url": url,
                    "timestamp_start": float(start),
                    "timestamp_end": float(end),
                },
            )
        )

    for seg in segments:
        seg_start = seg["start"]
        seg_end = seg["start"] + seg.get("duration", 0)
        if seg_start >= window_end:
            flush(buffer_seg_start, buffer_seg_end, buffer_text)
            # Slide window forward with overlap
            window_start = max(window_end - OVERLAP_SECONDS, seg_start)
            window_end = window_start + WINDOW_SECONDS
            buffer_text = []
            buffer_seg_start = seg_start
        if not buffer_text:
            buffer_seg_start = seg_start
        buffer_text.append(seg["text"])
        buffer_seg_end = seg_end

    flush(buffer_seg_start, buffer_seg_end, buffer_text)
    return chunks
