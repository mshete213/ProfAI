import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.rag_pipeline import query, stream_query
from models import ChatSession, Course, CourseEnrollment, User, UserRole, get_db
from schemas.chat import ChatMessageOut, ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def _ensure_chat_access(db: Session, course_id: UUID, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if user.role == UserRole.PROFESSOR:
        if course.professor_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your course")
        return course

    enrolled = (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.course_id == course_id, CourseEnrollment.student_id == user.id)
        .first()
    )
    if not enrolled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enrolled in this course")
    return course


@router.post("/{course_id}", response_model=ChatResponse)
def chat(
    course_id: UUID,
    payload: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:
    course = _ensure_chat_access(db, course_id, user)
    result = query(
        db=db,
        course=course,
        student_id=user.id,
        question=payload.question,
        session_id=payload.session_id,
    )
    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        session_id=UUID(result["session_id"]),
        tokens_used=result["tokens_used"],
    )


@router.post("/{course_id}/stream")
async def chat_stream(
    course_id: UUID,
    payload: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    course = _ensure_chat_access(db, course_id, user)

    async def event_generator():
        async for event in stream_query(
            db=db,
            course=course,
            student_id=user.id,
            question=payload.question,
            session_id=payload.session_id,
        ):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{course_id}/history", response_model=list[ChatMessageOut])
def get_history(
    course_id: UUID,
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ChatMessageOut]:
    _ensure_chat_access(db, course_id, user)
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session or session.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.student_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")
    return [ChatMessageOut.model_validate(m) for m in session.messages]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.student_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")
    db.delete(session)
    db.commit()
