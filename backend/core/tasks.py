import asyncio
import os
import uuid
from pathlib import Path
from typing import Any, cast

import structlog

from core.celery_app import celery_app
from core.encryption import decrypt
from core.ingestion_service import (
    already_ingested,
    compute_content_hash,
    persist_document_and_vectors,
    update_job_status,
)
from ingestion.pdf_parser import chunk_pdf
from models import (
    CanvasConnection,
    CanvasSyncMode,
    IngestionJob,
    JobStatus,
    SessionLocal,
    SourceType,
)
from models.db import utcnow

logger = structlog.get_logger()


def _source_type_from_extension(filename: str) -> SourceType:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return SourceType.PDF
    if ext == ".pptx":
        return SourceType.PPTX
    if ext == ".docx":
        return SourceType.DOCX
    raise ValueError(f"Unsupported file extension: {ext}")


def _chunk_for_ext(ext: str, data: bytes, filename: str):
    if ext == "pdf":
        return chunk_pdf(data, filename=filename)
    if ext == "pptx":
        from ingestion.pptx_parser import chunk_pptx

        return chunk_pptx(data, filename=filename)
    if ext == "docx":
        from ingestion.docx_parser import chunk_docx

        return chunk_docx(data, filename=filename)
    raise ValueError(f"No parser for extension: {ext}")


@celery_app.task(name="core.tasks.ingest_uploaded_file")
def ingest_uploaded_file(job_id: str, course_id: str, file_path: str, original_filename: str) -> dict[str, Any]:
    db = SessionLocal()
    job = db.query(IngestionJob).filter(IngestionJob.id == uuid.UUID(job_id)).first()
    if job is None:
        db.close()
        return {"status": "error", "reason": "job_not_found"}

    try:
        update_job_status(db, job, status=JobStatus.RUNNING, total=1)
        db.commit()

        with open(file_path, "rb") as f:
            data = f.read()

        content_hash = compute_content_hash(data)
        existing = already_ingested(db, uuid.UUID(course_id), content_hash)
        if existing is not None:
            update_job_status(db, job, status=JobStatus.SKIPPED_DUPLICATE, processed_increment=1)
            db.commit()
            return {"status": "skipped_duplicate", "doc_id": str(existing.id)}

        source_type = _source_type_from_extension(original_filename)
        chunks = _chunk_for_ext(source_type.value, data, original_filename)

        doc = persist_document_and_vectors(
            db=db,
            course_id=uuid.UUID(course_id),
            filename=original_filename,
            title=original_filename,
            source_type=source_type,
            source_url=None,
            content_hash=content_hash,
            chunks=chunks,
        )

        update_job_status(db, job, status=JobStatus.COMPLETED, processed_increment=1)
        db.commit()

        try:
            os.remove(file_path)
        except OSError:
            pass

        return {"status": "completed", "doc_id": str(doc.id), "chunks_created": len(chunks)}

    except Exception as exc:
        db.rollback()
        logger.exception("ingest_uploaded_file.failed", job_id=job_id, error=str(exc))
        update_job_status(db, job, status=JobStatus.FAILED, failed_increment=1, error_message=str(exc))
        db.commit()
        return {"status": "failed", "reason": str(exc)}
    finally:
        db.close()


@celery_app.task(name="core.tasks.ingest_youtube_url")
def ingest_youtube_url(job_id: str, course_id: str, url: str, language: str = "en") -> dict[str, Any]:
    from ingestion.youtube_ingestor import (
        chunk_youtube_transcript,
        extract_video_id,
        fetch_transcript,
    )

    db = SessionLocal()
    job = db.query(IngestionJob).filter(IngestionJob.id == uuid.UUID(job_id)).first()
    if job is None:
        db.close()
        return {"status": "error", "reason": "job_not_found"}

    try:
        update_job_status(db, job, status=JobStatus.RUNNING, total=1)
        db.commit()

        video_id = extract_video_id(url)
        segments = fetch_transcript(video_id, language=language)
        joined = " ".join(s["text"] for s in segments).encode("utf-8")
        content_hash = compute_content_hash(joined)

        existing = already_ingested(db, uuid.UUID(course_id), content_hash)
        if existing is not None:
            update_job_status(db, job, status=JobStatus.SKIPPED_DUPLICATE, processed_increment=1)
            db.commit()
            return {"status": "skipped_duplicate", "doc_id": str(existing.id)}

        chunks = chunk_youtube_transcript(segments, video_id=video_id, title=video_id, url=url)
        doc = persist_document_and_vectors(
            db=db,
            course_id=uuid.UUID(course_id),
            filename=f"{video_id}.youtube",
            title=video_id,
            source_type=SourceType.YOUTUBE,
            source_url=url,
            content_hash=content_hash,
            chunks=chunks,
        )

        update_job_status(db, job, status=JobStatus.COMPLETED, processed_increment=1)
        db.commit()
        return {"status": "completed", "doc_id": str(doc.id), "chunks_created": len(chunks)}

    except Exception as exc:
        db.rollback()
        logger.exception("ingest_youtube_url.failed", job_id=job_id, error=str(exc))
        update_job_status(db, job, status=JobStatus.FAILED, failed_increment=1, error_message=str(exc))
        db.commit()
        return {"status": "failed", "reason": str(exc)}
    finally:
        db.close()


@celery_app.task(name="core.tasks.ingest_drive_folder")
def ingest_drive_folder(job_id: str, course_id: str, folder_id: str, oauth_token: str, recursive: bool = True) -> dict[str, Any]:
    from ingestion.drive_ingestor import download_file as drive_download, list_folder

    db = SessionLocal()
    job = db.query(IngestionJob).filter(IngestionJob.id == uuid.UUID(job_id)).first()
    if job is None:
        db.close()
        return {"status": "error", "reason": "job_not_found"}

    try:
        update_job_status(db, job, status=JobStatus.RUNNING)
        db.commit()

        files = list(list_folder(oauth_token, folder_id, recursive=recursive))
        update_job_status(db, job, total=len(files))
        db.commit()

        for file_meta in files:
            try:
                result = drive_download(oauth_token, file_meta)
                if result is None:
                    update_job_status(db, job, processed_increment=1)
                    db.commit()
                    continue
                data, ext = result
                content_hash = compute_content_hash(data)
                if already_ingested(db, uuid.UUID(course_id), content_hash) is not None:
                    update_job_status(db, job, processed_increment=1)
                    db.commit()
                    continue

                chunks = _chunk_for_ext(ext, data, file_meta["name"])
                persist_document_and_vectors(
                    db=db,
                    course_id=uuid.UUID(course_id),
                    filename=file_meta["name"],
                    title=file_meta["name"],
                    source_type=SourceType.DRIVE,
                    source_url=f"https://drive.google.com/file/d/{file_meta['id']}",
                    content_hash=content_hash,
                    chunks=chunks,
                )
                update_job_status(db, job, processed_increment=1)
                db.commit()
            except Exception as item_exc:
                logger.exception("ingest_drive_folder.item_failed", file=file_meta.get("name"), error=str(item_exc))
                update_job_status(db, job, failed_increment=1)
                db.commit()

        final_status = JobStatus.COMPLETED if cast(int, cast(object, job.failed_items)) == 0 else JobStatus.FAILED
        update_job_status(db, job, status=final_status)
        db.commit()
        return {"status": "completed", "files": len(files)}

    except Exception as exc:
        db.rollback()
        logger.exception("ingest_drive_folder.failed", job_id=job_id, error=str(exc))
        update_job_status(db, job, status=JobStatus.FAILED, error_message=str(exc))
        db.commit()
        return {"status": "failed", "reason": str(exc)}
    finally:
        db.close()


def _sync_canvas_for_connection(db, conn: CanvasConnection, job: IngestionJob | None = None) -> dict[str, Any]:
    from ingestion.canvas_ingestor import (
        CANVAS_FILE_MIMES,
        chunk_canvas_page,
        download_file as canvas_download,
        fetch_page_body,
        list_course_files,
        list_course_pages,
    )

    canvas_domain = cast(str, cast(object, conn.canvas_domain))
    canvas_course_id = cast(int, cast(object, conn.canvas_course_id))
    canvas_token = decrypt(cast(str, cast(object, conn.canvas_token_encrypted)))
    course_id = cast(uuid.UUID, cast(object, conn.course_id))

    async def _run() -> dict[str, Any]:
        files = await list_course_files(canvas_domain, canvas_token, canvas_course_id)
        pages = await list_course_pages(canvas_domain, canvas_token, canvas_course_id)

        total = len(files) + len(pages)
        if job:
            update_job_status(db, job, total=total)
            db.commit()

        ingested = 0
        skipped = 0
        failed = 0

        for f in files:
            try:
                ext = CANVAS_FILE_MIMES.get(f.get("content-type") or f.get("content_type") or "")
                if not ext:
                    continue
                data = await canvas_download(f["url"])
                content_hash = compute_content_hash(data)
                if already_ingested(db, course_id, content_hash) is not None:
                    skipped += 1
                    if job:
                        update_job_status(db, job, processed_increment=1)
                        db.commit()
                    continue
                chunks = _chunk_for_ext(ext, data, f["display_name"])
                persist_document_and_vectors(
                    db=db,
                    course_id=course_id,
                    filename=f["display_name"],
                    title=f["display_name"],
                    source_type=SourceType.CANVAS,
                    source_url=f.get("url"),
                    content_hash=content_hash,
                    chunks=chunks,
                )
                ingested += 1
                if job:
                    update_job_status(db, job, processed_increment=1)
                    db.commit()
            except Exception as item_exc:
                failed += 1
                logger.exception("canvas.file_failed", file=f.get("display_name"), error=str(item_exc))
                if job:
                    update_job_status(db, job, failed_increment=1)
                    db.commit()

        for p in pages:
            try:
                full = await fetch_page_body(
                    canvas_domain, canvas_token, canvas_course_id, p["url"]
                )
                body_html = full.get("body") or ""
                if not body_html.strip():
                    if job:
                        update_job_status(db, job, processed_increment=1)
                        db.commit()
                    continue
                content_hash = compute_content_hash(body_html.encode("utf-8"))
                if already_ingested(db, course_id, content_hash) is not None:
                    skipped += 1
                    if job:
                        update_job_status(db, job, processed_increment=1)
                        db.commit()
                    continue
                chunks = chunk_canvas_page(body_html, full.get("title", p.get("title", "page")), full.get("html_url", ""))
                persist_document_and_vectors(
                    db=db,
                    course_id=course_id,
                    filename=f"canvas-page-{p['url']}",
                    title=full.get("title", p.get("title", "page")),
                    source_type=SourceType.CANVAS,
                    source_url=full.get("html_url"),
                    content_hash=content_hash,
                    chunks=chunks,
                )
                ingested += 1
                if job:
                    update_job_status(db, job, processed_increment=1)
                    db.commit()
            except Exception as item_exc:
                failed += 1
                logger.exception("canvas.page_failed", url=p.get("url"), error=str(item_exc))
                if job:
                    update_job_status(db, job, failed_increment=1)
                    db.commit()

        return {"files": len(files), "pages": len(pages), "ingested": ingested, "skipped": skipped, "failed": failed}

    result = asyncio.run(_run())
    setattr(conn, "last_synced_at", utcnow())
    db.flush()
    return result


@celery_app.task(name="core.tasks.ingest_canvas_course")
def ingest_canvas_course(job_id: str, course_id: str) -> dict[str, Any]:
    db = SessionLocal()
    job = db.query(IngestionJob).filter(IngestionJob.id == uuid.UUID(job_id)).first()
    conn = db.query(CanvasConnection).filter(CanvasConnection.course_id == uuid.UUID(course_id)).first()
    if job is None or conn is None:
        db.close()
        return {"status": "error", "reason": "missing_job_or_connection"}

    try:
        update_job_status(db, job, status=JobStatus.RUNNING)
        db.commit()
        result = _sync_canvas_for_connection(db, conn, job)
        update_job_status(db, job, status=JobStatus.COMPLETED)
        db.commit()
        return {"status": "completed", **result}
    except Exception as exc:
        db.rollback()
        logger.exception("ingest_canvas_course.failed", error=str(exc))
        update_job_status(db, job, status=JobStatus.FAILED, error_message=str(exc))
        db.commit()
        return {"status": "failed", "reason": str(exc)}
    finally:
        db.close()


@celery_app.task(name="core.tasks.sync_all_canvas_courses")
def sync_all_canvas_courses() -> dict[str, Any]:
    db = SessionLocal()
    try:
        conns = (
            db.query(CanvasConnection)
            .filter(CanvasConnection.sync_mode == CanvasSyncMode.POLLING)
            .all()
        )
        results = []
        for conn in conns:
            try:
                result = _sync_canvas_for_connection(db, conn, job=None)
                db.commit()
                results.append({"course_id": str(conn.course_id), **result})
            except Exception as exc:
                db.rollback()
                logger.exception("canvas.beat_sync_failed", course_id=str(conn.course_id), error=str(exc))
        return {"status": "ok", "synced": len(results), "results": results}
    finally:
        db.close()


@celery_app.task(name="core.tasks.ingest_local_path")
def ingest_local_path(course_id: str, file_path: str) -> dict[str, Any]:
    """Used by the folder watcher when a new file lands in a watched directory."""
    db = SessionLocal()
    job = IngestionJob(
        course_id=uuid.UUID(course_id),
        source_type=SourceType.PDF,
        status=JobStatus.QUEUED,
        total_items=1,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return ingest_uploaded_file(str(job.id), course_id, file_path, Path(file_path).name)
