from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from models.chat_session import MessageRole


class ChatRequest(BaseModel):
    question: str
    session_id: UUID | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    session_id: UUID
    tokens_used: dict[str, int]


class ChatMessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    sources: list[dict[str, Any]] | None
    tokens_used: dict[str, int] | None
    created_at: datetime

    class Config:
        from_attributes = True
