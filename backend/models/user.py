import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from models.db import Base, utcnow


class UserRole(str, enum.Enum):
    PROFESSOR = "professor"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, name="user_role"), nullable=False)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    courses_owned = relationship("Course", back_populates="professor", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", back_populates="student", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="student", cascade="all, delete-orphan")
