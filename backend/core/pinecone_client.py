from typing import Any

from pinecone import Pinecone, ServerlessSpec

from config import get_settings

settings = get_settings()

_pc: Pinecone | None = None
_index = None


def _get_pinecone() -> Pinecone:
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=settings.pinecone_api_key)
    return _pc


def _ensure_index():
    pc = _get_pinecone()
    existing = [idx.name for idx in pc.list_indexes()]
    if settings.pinecone_index_name not in existing:
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=settings.embedding_dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )


def get_index():
    global _index
    if _index is None:
        _ensure_index()
        _index = _get_pinecone().Index(settings.pinecone_index_name)
    return _index


def namespace_for_course(course_id: str) -> str:
    return f"course-{course_id}"


def upsert_chunks(course_id: str, vectors: list[dict[str, Any]], batch_size: int = 100) -> int:
    """
    Upsert a list of {id, values, metadata} dicts into the course namespace.
    Returns total count upserted.
    """
    if not vectors:
        return 0
    index = get_index()
    namespace = namespace_for_course(course_id)
    total = 0
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        index.upsert(vectors=batch, namespace=namespace)
        total += len(batch)
    return total


def query_chunks(
    course_id: str,
    vector: list[float],
    top_k: int = 8,
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    index = get_index()
    namespace = namespace_for_course(course_id)
    response = index.query(
        namespace=namespace,
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        filter={"course_id": {"$eq": course_id}},
    )
    matches = response.get("matches", []) if isinstance(response, dict) else response.matches
    out = []
    for m in matches:
        score = m["score"] if isinstance(m, dict) else m.score
        meta = m["metadata"] if isinstance(m, dict) else m.metadata
        if score_threshold is not None and score < score_threshold:
            continue
        out.append({"score": score, "metadata": meta})
    return out


def delete_by_doc_id(course_id: str, doc_id: str) -> None:
    index = get_index()
    index.delete(
        namespace=namespace_for_course(course_id),
        filter={"doc_id": {"$eq": doc_id}},
    )


def delete_namespace(course_id: str) -> None:
    index = get_index()
    try:
        index.delete(delete_all=True, namespace=namespace_for_course(course_id))
    except Exception:
        # Namespace may not exist if no vectors were ever upserted; safe to ignore.
        pass
