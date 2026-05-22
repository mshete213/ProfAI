from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.deps import get_current_user, require_professor
from models import (
    Course,
    CourseEnrollment,
    Document,
    User,
    UserRole,
    get_db,
)
from schemas.course import CourseCreate, CourseOut, CourseUpdate, CourseWithStats

router = APIRouter(prefix="/api/v1/courses", tags=["courses"])


def _get_owned_course(db: Session, course_id: UUID, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if course.professor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your course")
    return course


def _ensure_access(db: Session, course_id: UUID, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if user.role == UserRole.PROFESSOR and course.professor_id == user.id:
        return course

    if user.role == UserRole.STUDENT:
        enrollment = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.course_id == course_id, CourseEnrollment.student_id == user.id)
            .first()
        )
        if enrollment:
            return course

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this course")


@router.get("", response_model=list[CourseWithStats])
def list_courses(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CourseWithStats]:
    if user.role == UserRole.PROFESSOR:
        courses = db.query(Course).filter(Course.professor_id == user.id).all()
    else:
        courses = (
            db.query(Course)
            .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
            .filter(CourseEnrollment.student_id == user.id)
            .all()
        )

    results = []
    for course in courses:
        doc_count = db.query(func.count(Document.id)).filter(Document.course_id == course.id).scalar() or 0
        enroll_count = (
            db.query(func.count(CourseEnrollment.id)).filter(CourseEnrollment.course_id == course.id).scalar() or 0
        )
        course_out = CourseWithStats.model_validate(course)
        course_out.document_count = int(doc_count)
        course_out.enrollment_count = int(enroll_count)
        results.append(course_out)
    return results


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    professor: Annotated[User, Depends(require_professor)],
    db: Annotated[Session, Depends(get_db)],
) -> CourseOut:
    course = Course(
        name=payload.name,
        description=payload.description,
        style_instructions=payload.style_instructions or "",
        professor_id=professor.id,
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
    course = _ensure_access(db, course_id, user)
    return CourseOut.model_validate(course)


@router.put("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    professor: Annotated[User, Depends(require_professor)],
    db: Annotated[Session, Depends(get_db)],
) -> CourseOut:
    course = _get_owned_course(db, course_id, professor)
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
    professor: Annotated[User, Depends(require_professor)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    course = _get_owned_course(db, course_id, professor)
    # NOTE: Pinecone namespace cleanup is handled in core.pinecone_client (called from a future hook).
    db.delete(course)
    db.commit()


@router.post("/{course_id}/enroll", status_code=status.HTTP_204_NO_CONTENT)
def enroll(
    course_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can enroll")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    existing = (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.course_id == course_id, CourseEnrollment.student_id == user.id)
        .first()
    )
    if existing:
        return

    enrollment = CourseEnrollment(student_id=user.id, course_id=course_id)
    db.add(enrollment)
    db.commit()
