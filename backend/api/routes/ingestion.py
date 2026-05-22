import asyncio
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from config import get_settings
from core.encryption import encrypt
from core.pinecone_client import delete_by_doc_id
from core.tasks import (
    ingest_canvas_course,
    ingest_drive_folder,
    ingest_uploaded_file,
    ingest_youtube_url,
)
from ingestion.canvas_ingestor import check_webhook_compatibility, register_webhook
from models import (
    CanvasConnection,
    CanvasSyncMode,
    Course,
    Document,
    IngestionJob,
    JobStatus,
    SourceType,
    User,
    get_db,
)
from schemas.ingestion import (
    CanvasIngestRequest,
    CanvasIngestResponse,
    DocumentOut,
    DriveIngestRequest,
    JobCreatedOut,
    JobOut,
    YouTubeIngestRequest,
)

settings = get_settings()

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


def _verify_course_owned(db: Session, course_id: UUID, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if course.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your course")
    return course


_ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".docx"}


@router.post("/{course_id}/upload", response_model=JobCreatedOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_files(
    course_id: UUID,
    files: Annotated[list[UploadFile], File(...)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JobCreatedOut:
    _verify_course_owned(db, course_id, user)

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")

    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {ext}. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}",
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
        contents = await f.read()
        dest.write_bytes(contents)
        ingest_uploaded_file.delay(str(job.id), str(course_id), str(dest), original)

    return JobCreatedOut(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JobOut:
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    course = db.query(Course).filter(Course.id == job.course_id).first()
    if course is None or course.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    return JobOut.model_validate(job)


@router.get("/{course_id}/materials", response_model=list[DocumentOut])
def list_materials(
    course_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[DocumentOut]:
    _verify_course_owned(db, course_id, user)
    docs = (
        db.query(Document)
        .filter(Document.course_id == course_id)
        .order_by(Document.ingested_at.desc())
        .all()
    )
    return [DocumentOut.model_validate(d) for d in docs]


@router.delete("/{course_id}/materials/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    course_id: UUID,
    doc_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    _verify_course_owned(db, course_id, user)
    doc = db.query(Document).filter(Document.id == doc_id, Document.course_id == course_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        delete_by_doc_id(str(course_id), str(doc_id))
    except Exception:
        pass

    db.delete(doc)
    db.commit()


@router.post("/{course_id}/youtube", response_model=JobCreatedOut, status_code=status.HTTP_202_ACCEPTED)
def ingest_youtube(
    course_id: UUID,
    payload: YouTubeIngestRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JobCreatedOut:
    _verify_course_owned(db, course_id, user)
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
def ingest_drive(
    course_id: UUID,
    payload: DriveIngestRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JobCreatedOut:
    _verify_course_owned(db, course_id, user)
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


@router.post("/{course_id}/canvas", response_model=CanvasIngestResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_canvas(
    course_id: UUID,
    payload: CanvasIngestRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CanvasIngestResponse:
    _verify_course_owned(db, course_id, user)

    conn = db.query(CanvasConnection).filter(CanvasConnection.course_id == course_id).first()
    encrypted_token = encrypt(payload.canvas_token)

    if conn is None:
        conn = CanvasConnection(
            course_id=course_id,
            canvas_domain=payload.canvas_domain,
            canvas_token_encrypted=encrypted_token,
            canvas_course_id=payload.canvas_course_id,
            sync_mode=CanvasSyncMode.POLLING,
        )
        db.add(conn)
    else:
        conn.canvas_domain = payload.canvas_domain
        conn.canvas_token_encrypted = encrypted_token
        conn.canvas_course_id = payload.canvas_course_id

    webhook_compatible = asyncio.run(
        check_webhook_compatibility(payload.canvas_domain, payload.canvas_token)
    )
    conn.webhook_compatible = "true" if webhook_compatible else "false"
    db.commit()

    job = IngestionJob(
        course_id=course_id,
        source_type=SourceType.CANVAS,
        status=JobStatus.QUEUED,
        payload={"canvas_course_id": payload.canvas_course_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    ingest_canvas_course.delay(str(job.id), str(course_id))

    return CanvasIngestResponse(
        job_id=job.id,
        status=job.status,
        webhook_compatible=webhook_compatible,
    )


@router.post("/{course_id}/canvas/enable-webhooks", status_code=status.HTTP_200_OK)
def enable_canvas_webhooks(
    course_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    from core.encryption import decrypt

    _verify_course_owned(db, course_id, user)
    conn = db.query(CanvasConnection).filter(CanvasConnection.course_id == course_id).first()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Canvas connection")
    if conn.webhook_compatible != "true":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Canvas instance does not support webhooks",
        )

    canvas_token = decrypt(conn.canvas_token_encrypted)
    subscription_id = asyncio.run(
        register_webhook(
            conn.canvas_domain,
            canvas_token,
            conn.canvas_course_id,
            settings.canvas_webhook_public_url,
        )
    )
    conn.sync_mode = CanvasSyncMode.WEBHOOK
    conn.webhook_subscription_id = subscription_id
    db.commit()
    return {"status": "enabled", "subscription_id": subscription_id}
