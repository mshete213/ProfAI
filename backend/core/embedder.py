from typing import Sequence

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings

settings = get_settings()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def embed(text: str) -> list[float]:
    response = _get_client().embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def embed_batch(texts: Sequence[str]) -> list[list[float]]:
    """Embed multiple texts in a single API call. OpenAI accepts up to 2048 inputs per call."""
    if not texts:
        return []
    response = _get_client().embeddings.create(
        model=settings.embedding_model,
        input=list(texts),
    )
    # Preserve input order
    return [d.embedding for d in sorted(response.data, key=lambda d: d.index)]
