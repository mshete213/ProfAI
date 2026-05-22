from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from models.document import JobStatus, SourceType


class JobOut(BaseModel):
    id: UUID
    course_id: UUID
    source_type: SourceType
    status: JobStatus
    total_items: int
    processed_items: int
    failed_items: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class JobCreatedOut(BaseModel):
    job_id: UUID
    status: JobStatus


class DocumentOut(BaseModel):
    id: UUID
    course_id: UUID
    filename: str
    title: str | None
    source_type: SourceType
    source_url: str | None
    content_hash: str
    chunk_count: int
    ingested_at: datetime

    class Config:
        from_attributes = True


class YouTubeIngestRequest(BaseModel):
    url: str
    language: str = "en"


class DriveIngestRequest(BaseModel):
    folder_id: str
    oauth_token: str
    recursive: bool = True


class CanvasIngestRequest(BaseModel):
    canvas_domain: str
    canvas_token: str
    canvas_course_id: int


class CanvasIngestResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    webhook_compatible: bool
