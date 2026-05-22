"""
Internal routes consumed by the MCP server. Auth via X-Internal-Key header.

The public /api/v1/ingest routes require a professor JWT — these mirror routes
exist so autonomous MCP tools can trigger ingestion without a user context.
"""
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import verify_internal_key
from config import get_settings
from core.tasks import ingest_drive_folder, ingest_uploaded_file, ingest_youtube_url
from models import Course, IngestionJob, JobStatus, SourceType, get_db
from schemas.ingestion import DriveIngestRequest, JobCreatedOut, JobOut, YouTubeIngestRequest

settings = get_settings()

router = APIRouter(
    prefix="/api/v1/internal/ingest",
    tags=["internal"],
    dependencies=[Depends(verify_internal_key)],
)


def _verify_course_exists(db: Session, course_id: UUID) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


@router.post("/{course_id}/youtube", response_model=JobCreatedOut, status_code=status.HTTP_202_ACCEPTED)
def internal_ingest_youtube(
    course_id: UUID,
    payload: YouTubeIngestRequest,
    db: Annotated[Session, Depends(get_db)],
) -> JobCreatedOut:
    _verify_course_exists(db, course_id)
    job = IngestionJob(
        course_id=course_id,
        source_type=SourceType.YOUTUBE,
        status=JobStatus.QUEUED,
        total_items=1,
        payload={"url": payload.url, "language": payload.language},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    ingest_youtube_url.delay(str(job.id), str(course_id), payload.url, payload.language)
    return JobCreatedOut(job_id=job.id, status=job.status)


@router.post("/{course_id}/drive", response_model=JobCreatedOut, status_code=status.HTTP_202_ACCEPTED)
def internal_ingest_drive(
    course_id: UUID,
    payload: DriveIngestRequest,
    db: Annotated[Session, Depends(get_db)],
) -> JobCreatedOut:
    _verify_course_exists(db, course_id)
    job = IngestionJob(
        course_id=course_id,
        source_type=SourceType.DRIVE,
        status=JobStatus.QUEUED,
        payload={"folder_id": payload.folder_id, "recursive": payload.recursive},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    ingest_drive_folder.delay(
        str(job.id), str(course_id), payload.folder_id, payload.oauth_token, payload.recursive
    )
    return JobCreatedOut(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobOut)
def internal_get_job(
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> JobOut:
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobOut.model_validate(job)


_ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".docx"}


@router.post("/{course_id}/upload", response_model=JobCreatedOut, status_code=status.HTTP_202_ACCEPTED)
async def internal_upload(
    course_id: UUID,
    files: Annotated[list[UploadFile], File(...)],
    db: Annotated[Session, Depends(get_db)],
) -> JobCreatedOut:
    _verify_course_exists(db, course_id)
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")
    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {ext}",
            )

    job = IngestionJob(
        course_id=course_id,
        source_type=SourceType.PDF,
        status=JobStatus.QUEUED,
        total_items=len(files),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    job_upload_dir = Path(settings.upload_dir) / str(job.id)
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        original = f.filename or "upload"
        dest = job_upload_dir / original
        dest.write_bytes(await f.read())
        ingest_uploaded_file.delay(str(job.id), str(course_id), str(dest), original)

    return JobCreatedOut(job_id=job.id, status=job.status)
