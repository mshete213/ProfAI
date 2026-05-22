import io

from docx import Document as DocxDocument

from core.chunker import Chunk, chunk_by_paragraphs


def chunk_docx(data: bytes, filename: str, title: str | None = None) -> list[Chunk]:
    doc = DocxDocument(io.BytesIO(data))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)

    return chunk_by_paragraphs(
        full_text,
        extra_metadata={
            "filename": filename,
            "title": title or filename,
            "source_type": "docx",
        },
    )
