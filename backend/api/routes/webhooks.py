from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.tasks import ingest_canvas_course
from models import CanvasConnection, IngestionJob, JobStatus, SourceType, get_db

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/canvas", status_code=status.HTTP_202_ACCEPTED)
async def canvas_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    Canvas Live Events webhook receiver. Triggered when a tracked event fires
    in a Canvas course (e.g. attachment_created, wiki_page_updated). Queues a
    re-sync for the affected course — the content_hash dedup ensures only
    new/changed material is actually re-embedded.

    NOTE: For production, verify the HMAC signature in the Authorization header
    against your Canvas shared secret. This stub trusts the payload.
    """
    body: dict[str, Any] = await request.json()
    event_name = body.get("metadata", {}).get("event_name") or body.get("event_name")
    canvas_course_id = body.get("metadata", {}).get("context_id") or body.get("context_id")

    if canvas_course_id is None:
        logger.warning("canvas_webhook.missing_context_id", body=body)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing context_id")

    try:
        canvas_course_id_int = int(canvas_course_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid context_id")

    conn = (
        db.query(CanvasConnection)
        .filter(CanvasConnection.canvas_course_id == canvas_course_id_int)
        .first()
    )
    if conn is None:
        logger.info("canvas_webhook.no_connection", canvas_course_id=canvas_course_id_int, event=event_name)
        return {"status": "ignored", "reason": "no_connection"}

    job = IngestionJob(
        course_id=conn.course_id,
        source_type=SourceType.CANVAS,
        status=JobStatus.QUEUED,
        payload={"trigger": "webhook", "event_name": event_name},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    ingest_canvas_course.delay(str(job.id), str(conn.course_id))

    return {"status": "queued", "job_id": str(job.id), "event_name": event_name}
