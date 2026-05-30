"""File ingestion Kafka worker.

Subscribes to file.uploaded → downloads from MinIO → extracts text
→ chunks → embeds → stores in ChromaDB → publishes file.embedded.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from app.services.kafka import topics

logger = logging.getLogger(__name__)


async def handle_file_uploaded(
    topic: str,
    partition: int,
    offset: int,
    key: Optional[str],
    payload: Dict[str, Any],
) -> None:
    """Process a file.uploaded Kafka event — ingest into ChromaDB."""
    bucket = payload.get("bucket")
    minio_key = payload.get("key")
    file_metadata_id = payload.get("file_metadata_id")
    user_id = payload.get("user_id")
    filename = payload.get("filename", "unknown")

    if not bucket or not minio_key:
        logger.warning("file_ingestion: missing bucket/key in payload %s", payload)
        return

    logger.info("file_ingestion: processing %s/%s", bucket, minio_key)

    # 1. Download file bytes from MinIO
    try:
        from app.services.minio_service import download_bytes
        raw_bytes = await download_bytes(bucket, minio_key)
        if raw_bytes is None:
            logger.error("file_ingestion: MinIO download returned None for %s/%s", bucket, minio_key)
            return
    except Exception as exc:
        logger.error("file_ingestion: MinIO download error: %s", exc)
        return

    # 2. Extract text (PDF, DOCX, plain text)
    text = _extract_text(raw_bytes, filename)
    if not text.strip():
        logger.info("file_ingestion: no extractable text from %s", filename)
        return

    # 3. Chunk and embed into ChromaDB
    chunks = _chunk_text(text, chunk_size=1000, overlap=200)
    doc_ids = []
    try:
        from app.services.rag import get_shared_chroma_vector_store
        vector_store = get_shared_chroma_vector_store()
        if not vector_store._initialized:
            await vector_store.initialize()

        # Simple chunking: 1000 chars, 200 overlap
        for i, chunk in enumerate(chunks):
            doc_id = f"{file_metadata_id or minio_key.replace('/', '_')}_{i}"
            vector_store.add_document_sync(
                document_id=doc_id,
                content=chunk,
                metadata={
                    "file_metadata_id": file_metadata_id,
                    "user_id": user_id,
                    "filename": filename,
                    "bucket": bucket,
                    "minio_key": minio_key,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            doc_ids.append(doc_id)
        logger.info("file_ingestion: embedded %d chunks for %s", len(chunks), filename)
    except Exception as exc:
        logger.error("file_ingestion: ChromaDB embedding error: %s", exc)
        return

    # 4. Update PostgreSQL file_metadata.embedded_at
    if file_metadata_id:
        try:
            from app.database import AsyncSessionLocal
            from app.models.os_platform import FileMetadataModel
            from sqlalchemy import select
            from app.utils.helpers import utc_now

            async with AsyncSessionLocal() as db:
                row = (await db.execute(
                    select(FileMetadataModel).where(FileMetadataModel.id == file_metadata_id)
                )).scalar_one_or_none()
                if row:
                    row.embedding_id = doc_ids[0] if doc_ids else None
                    row.embedded_at = utc_now()
                    await db.commit()
        except Exception as exc:
            logger.warning("file_ingestion: DB update failed: %s", exc)

    # 5. Publish file.embedded event
    try:
        from app.services.kafka import publish_json
        await publish_json(
            topics.FILE_EMBEDDED,
            {
                "file_metadata_id": file_metadata_id,
                "filename": filename,
                "chunks": len(chunks),
                "user_id": user_id,
            },
            key=file_metadata_id,
        )
    except Exception as exc:
        logger.warning("file_ingestion: publish FILE_EMBEDDED failed: %s", exc)


def _extract_text(data: bytes, filename: str) -> str:
    """Extract text from bytes based on file type."""
    filename_lower = filename.lower()
    try:
        if filename_lower.endswith(".pdf"):
            import fitz  # PyMuPDF
            doc = fitz.open(stream=data, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)
        elif filename_lower.endswith(".docx"):
            from docx import Document
            import io
            doc = Document(io.BytesIO(data))
            return "\n".join(para.text for para in doc.paragraphs)
        else:
            # Try UTF-8 text
            return data.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Text extraction failed for %s: %s", filename, exc)
        return ""


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c for c in chunks if c.strip()]
