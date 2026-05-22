import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from models.db import Base, utcnow


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    style_instructions = Column(Text, nullable=True, default="")

    professor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    professor = relationship("User", back_populates="courses_owned")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="course", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="course", cascade="all, delete-orphan")
    canvas_connection = relationship(
        "CanvasConnection", back_populates="course", uselist=False, cascade="all, delete-orphan"
    )


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime, default=utcnow, nullable=False)

    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
