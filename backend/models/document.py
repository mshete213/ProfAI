import enum
import uuid

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from models.db import Base, utcnow


class SourceType(str, enum.Enum):
    PDF = "pdf"
    PPTX = "pptx"
    DOCX = "docx"
    YOUTUBE = "youtube"
    DRIVE = "drive"
    CANVAS = "canvas"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED_DUPLICATE = "skipped_duplicate"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)

    filename = Column(String(512), nullable=False)
    title = Column(String(512), nullable=True)
    source_type = Column(Enum(SourceType, name="source_type"), nullable=False)
    source_url = Column(Text, nullable=True)

    content_hash = Column(String(128), nullable=False, index=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    extra_metadata = Column("metadata", JSON, nullable=True)

    ingested_at = Column(DateTime, default=utcnow, nullable=False)

    course = relationship("Course", back_populates="documents")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)

    source_type = Column(Enum(SourceType, name="source_type"), nullable=False)
    status = Column(Enum(JobStatus, name="job_status"), default=JobStatus.QUEUED, nullable=False)

    total_items = Column(Integer, default=0, nullable=False)
    processed_items = Column(Integer, default=0, nullable=False)
    failed_items = Column(Integer, default=0, nullable=False)

    error_message = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
