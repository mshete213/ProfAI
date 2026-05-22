from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    style_instructions: str | None = ""


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    style_instructions: str | None = None


class CourseOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    style_instructions: str | None
    professor_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourseWithStats(CourseOut):
    document_count: int = 0
    enrollment_count: int = 0
