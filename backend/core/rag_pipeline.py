import uuid
from typing import Any, AsyncIterator

from anthropic import Anthropic
from sqlalchemy.orm import Session

from config import get_settings
from core.chunker import count_tokens
from core.embedder import embed
from core.pinecone_client import query_chunks
from core.prompt_builder import (
    build_system_blocks,
    build_user_message,
    trim_history_to_budget,
)
from models import ChatMessage, ChatSession, Course, MessageRole

settings = get_settings()

_anthropic: Anthropic | None = None


def _get_anthropic() -> Anthropic:
    global _anthropic
    if _anthropic is None:
        _anthropic = Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic


def _get_or_create_session(
    db: Session, course_id: uuid.UUID, user_id: uuid.UUID, session_id: uuid.UUID | None
) -> ChatSession:
    if session_id is not None:
        existing = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if existing and existing.course_id == course_id and existing.student_id == user_id:
            return existing
    session = ChatSession(course_id=course_id, student_id=user_id)
    db.add(session)
    db.flush()
    return session


def _load_history(db: Session, session: ChatSession) -> list[dict[str, str]]:
    return [
        {"role": m.role.value, "content": m.content}
        for m in session.messages
    ]


def _retrieve_context(course_id: uuid.UUID, question: str) -> list[dict[str, Any]]:
    q_vec = embed(question)
    return query_chunks(
        course_id=str(course_id),
        vector=q_vec,
        top_k=settings.rag_top_k,
        score_threshold=settings.rag_score_threshold,
    )


def query(
    db: Session,
    course: Course,
    user_id: uuid.UUID,
    question: str,
    session_id: uuid.UUID | None,
) -> dict[str, Any]:
    """Single-shot (non-streaming) RAG query."""
    session = _get_or_create_session(db, course.id, user_id, session_id)
    history = _load_history(db, session)
    chunks = _retrieve_context(course.id, question)

    system_blocks = build_system_blocks(course.name, course.style_instructions or "")
    trimmed_history = trim_history_to_budget(history)
    user_content = build_user_message(question, chunks)

    messages = [*trimmed_history, {"role": "user", "content": user_content}]

    client = _get_anthropic()
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        temperature=0.2,
        system=system_blocks,
        messages=messages,
    )
    answer = response.content[0].text if response.content else ""

    sources = [c.get("metadata", {}) for c in chunks]
    tokens_used = {
        "input": response.usage.input_tokens,
        "output": response.usage.output_tokens,
        "cache_read": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        "cache_creation": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
    }

    user_msg = ChatMessage(
        session_id=session.id,
        role=MessageRole.USER,
        content=question,
        token_count=count_tokens(question),
    )
    assistant_msg = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=answer,
        sources=sources,
        tokens_used=tokens_used,
        token_count=count_tokens(answer),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    return {
        "answer": answer,
        "sources": sources,
        "session_id": str(session.id),
        "tokens_used": tokens_used,
    }


async def stream_query(
    db: Session,
    course: Course,
    user_id: uuid.UUID,
    question: str,
    session_id: uuid.UUID | None,
) -> AsyncIterator[dict[str, Any]]:
    """
    Stream the response as SSE-friendly dicts.
    Yields events: {"event": "session", "data": {...}}, {"event": "chunk", "data": "..."},
    {"event": "sources", "data": [...]}, {"event": "done", "data": {...}}.
    """
    session = _get_or_create_session(db, course.id, user_id, session_id)
    history = _load_history(db, session)
    chunks = _retrieve_context(course.id, question)
    sources = [c.get("metadata", {}) for c in chunks]

    system_blocks = build_system_blocks(course.name, course.style_instructions or "")
    trimmed_history = trim_history_to_budget(history)
    user_content = build_user_message(question, chunks)
    messages = [*trimmed_history, {"role": "user", "content": user_content}]

    yield {"event": "session", "data": {"session_id": str(session.id)}}
    yield {"event": "sources", "data": sources}

    client = _get_anthropic()
    answer_parts: list[str] = []
    tokens_used: dict[str, int] = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}

    with client.messages.stream(
        model=settings.anthropic_model,
        max_tokens=2048,
        temperature=0.2,
        system=system_blocks,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            answer_parts.append(text)
            yield {"event": "chunk", "data": text}
        final = stream.get_final_message()
        if final and final.usage:
            tokens_used = {
                "input": final.usage.input_tokens,
                "output": final.usage.output_tokens,
                "cache_read": getattr(final.usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation": getattr(final.usage, "cache_creation_input_tokens", 0) or 0,
            }

    answer = "".join(answer_parts)

    user_msg = ChatMessage(
        session_id=session.id,
        role=MessageRole.USER,
        content=question,
        token_count=count_tokens(question),
    )
    assistant_msg = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=answer,
        sources=sources,
        tokens_used=tokens_used,
        token_count=count_tokens(answer),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    yield {"event": "done", "data": {"tokens_used": tokens_used, "session_id": str(session.id)}}
