from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.deps import get_current_user
from models import Course, Document, User, get_db
from schemas.course import CourseCreate, CourseOut, CourseUpdate, CourseWithStats

router = APIRouter(prefix="/api/v1/courses", tags=["courses"])


def _get_owned_course(db: Session, course_id: UUID, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if course.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your course")
    return course


@router.get("", response_model=list[CourseWithStats])
def list_courses(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CourseWithStats]:
    courses = db.query(Course).filter(Course.owner_id == user.id).all()

    results = []
    for course in courses:
        doc_count = db.query(func.count(Document.id)).filter(Document.course_id == course.id).scalar() or 0
        course_out = CourseWithStats.model_validate(course)
        course_out.document_count = int(doc_count)
        results.append(course_out)
    return results


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CourseOut:
    course = Course(
        name=payload.name,
        description=payload.description,
        style_instructions=payload.style_instructions or "",
        owner_id=user.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseOut.model_validate(course)


@router.get("/{course_id}", response_model=CourseOut)
def get_course(
    course_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CourseOut:
    course = _get_owned_course(db, course_id, user)
    return CourseOut.model_validate(course)


@router.put("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CourseOut:
    course = _get_owned_course(db, course_id, user)
    if payload.name is not None:
        course.name = payload.name
    if payload.description is not None:
        course.description = payload.description
    if payload.style_instructions is not None:
        course.style_instructions = payload.style_instructions
    db.commit()
    db.refresh(course)
    return CourseOut.model_validate(course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    course = _get_owned_course(db, course_id, user)
    db.delete(course)
    db.commit()
