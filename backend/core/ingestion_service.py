import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy.orm import Session

from core.chunker import Chunk
from core.embedder import embed_batch
from core.pinecone_client import upsert_chunks
from models import Document, IngestionJob, JobStatus, SourceType
from models.db import utcnow


def compute_content_hash(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def already_ingested(db: Session, course_id: uuid.UUID, content_hash: str) -> Document | None:
    return (
        db.query(Document)
        .filter(Document.course_id == course_id, Document.content_hash == content_hash)
        .first()
    )


def persist_document_and_vectors(
    db: Session,
    course_id: uuid.UUID,
    filename: str,
    title: str | None,
    source_type: SourceType,
    source_url: str | None,
    content_hash: str,
    chunks: list[Chunk],
) -> Document:
    """
    Embeds all chunks, upserts to Pinecone, and creates a Document row.
    Caller is responsible for transaction boundaries.
    """
    if not chunks:
        # Still record the doc, but with 0 chunks, so the dedup key is captured.
        doc = Document(
            course_id=course_id,
            filename=filename,
            title=title or filename,
            source_type=source_type,
            source_url=source_url,
            content_hash=content_hash,
            chunk_count=0,
        )
        db.add(doc)
        db.flush()
        return doc

    doc_id = uuid.uuid4()
    texts = [c.text for c in chunks]
    embeddings = embed_batch(texts)

    vectors: list[dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings, strict=True)):
        meta = dict(chunk.metadata)
        meta.update(
            {
                "chunk_id": f"{doc_id}_chunk_{i:04d}",
                "doc_id": str(doc_id),
                "course_id": str(course_id),
                "chunk_index": i,
                "chunk_total": len(chunks),
                "text": chunk.text,
                "token_count": chunk.token_count,
                "ingested_at": now_iso,
                "content_hash": content_hash,
                "filename": meta.get("filename", filename),
                "title": meta.get("title", title or filename),
                "source_type": meta.get("source_type", source_type.value),
            }
        )
        vectors.append({"id": meta["chunk_id"], "values": emb, "metadata": meta})

    upsert_chunks(str(course_id), vectors)

    doc = Document(
        id=doc_id,
        course_id=course_id,
        filename=filename,
        title=title or filename,
        source_type=source_type,
        source_url=source_url,
        content_hash=content_hash,
        chunk_count=len(chunks),
    )
    db.add(doc)
    db.flush()
    return doc


def update_job_status(
    db: Session,
    job: IngestionJob,
    *,
    status: JobStatus | None = None,
    processed_increment: int = 0,
    failed_increment: int = 0,
    total: int | None = None,
    error_message: str | None = None,
) -> None:
    if status is not None:
        setattr(job, "status", status)
        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.SKIPPED_DUPLICATE):
            setattr(job, "completed_at", utcnow())
    if processed_increment:
        setattr(job, "processed_items", cast(int, cast(object, job.processed_items)) + processed_increment)
    if failed_increment:
        setattr(job, "failed_items", cast(int, cast(object, job.failed_items)) + failed_increment)
    if total is not None:
        setattr(job, "total_items", total)
    if error_message is not None:
        setattr(job, "error_message", error_message)
    db.flush()
