from typing import cast

import fitz  # PyMuPDF

from core.chunker import Chunk, chunk_by_paragraphs


def parse_pdf_bytes(data: bytes) -> list[tuple[int, str]]:
    """Returns list of (page_number, text). Pages are 1-indexed."""
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        return [(i + 1, cast(str, doc.load_page(i).get_text("text"))) for i in range(doc.page_count)]
    finally:
        doc.close()


def parse_pdf_path(path: str) -> list[tuple[int, str]]:
    with open(path, "rb") as f:
        return parse_pdf_bytes(f.read())


def chunk_pdf(data: bytes, filename: str, title: str | None = None) -> list[Chunk]:
    pages = parse_pdf_bytes(data)
    all_chunks: list[Chunk] = []
    for page_num, text in pages:
        if not text.strip():
            continue
        page_chunks = chunk_by_paragraphs(
            text,
            extra_metadata={
                "filename": filename,
                "title": title or filename,
                "page_number": page_num,
                "source_type": "pdf",
            },
        )
        all_chunks.extend(page_chunks)
    return all_chunks
