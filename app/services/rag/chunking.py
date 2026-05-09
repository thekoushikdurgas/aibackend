"""
Document Chunking Strategies for RAG
Supports semantic, recursive, and sliding window chunking approaches.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from app.services.rag.text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
)

from app.config import settings

logger = logging.getLogger(__name__)


class DocumentChunker:
    """
    Intelligent document chunking with multiple strategies.
    Preserves metadata and document structure.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        strategy: str = "recursive",
    ):
        """
        Initialize document chunker.

        Args:
            chunk_size: Characters per chunk (uses config default if None)
            chunk_overlap: Overlap between chunks (uses config default if None)
            strategy: Chunking strategy - "recursive", "semantic", or "sliding"
        """
        self.chunk_size = chunk_size or settings.rag_chunk_size
        self.chunk_overlap = chunk_overlap or settings.rag_chunk_overlap
        self.strategy = strategy

        self.splitter: Union[RecursiveCharacterTextSplitter, CharacterTextSplitter]

        # Initialize splitters based on strategy
        if strategy == "recursive":
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""],
                length_function=len,
            )
        elif strategy == "semantic":
            # Semantic chunking respects sentence/paragraph boundaries
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n\n", "\n\n", "\n", ". ", "! ", "? ", " ", ""],
                length_function=len,
            )
        elif strategy == "sliding":
            # Sliding window with fixed overlap
            self.splitter = CharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separator="",
                length_function=len,
            )
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into smaller segments with metadata preservation.

        Args:
            text: Text content to chunk
            metadata: Optional metadata to attach to all chunks
            document_id: Optional document identifier

        Returns:
            List of chunk dicts with content and metadata
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        # Split text into chunks
        chunks = self.splitter.split_text(text)

        chunked_docs = []
        base_metadata = metadata.copy() if metadata else {}

        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                **base_metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk),
                "strategy": self.strategy,
            }

            if document_id:
                chunk_metadata["document_id"] = document_id
                chunk_metadata["chunk_id"] = f"{document_id}_chunk_{i}"
            else:
                chunk_metadata["chunk_id"] = f"chunk_{i}"

            chunked_docs.append(
                {
                    "id": chunk_metadata["chunk_id"],
                    "content": chunk,
                    "metadata": chunk_metadata,
                }
            )

        logger.info(
            f"Created {len(chunks)} chunks from document "
            f"(strategy: {self.strategy}, size: {self.chunk_size}, overlap: {self.chunk_overlap})"
        )
        return chunked_docs

    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk multiple documents.

        Args:
            documents: List of document dicts with 'content' and optional 'metadata', 'id'

        Returns:
            List of all chunks from all documents
        """
        all_chunks = []

        for doc in documents:
            text = doc.get("content", "")
            if not text:
                logger.warning(
                    f"Skipping document with no content: {doc.get('id', 'unknown')}"
                )
                continue

            metadata = {k: v for k, v in doc.items() if k != "content"}
            document_id = doc.get("id") or metadata.get("document_id")

            chunks = self.chunk_text(
                text=text, metadata=metadata, document_id=document_id
            )
            all_chunks.extend(chunks)

        logger.info(
            f"Chunked {len(documents)} documents into {len(all_chunks)} total chunks"
        )
        return all_chunks

    def chunk_with_sliding_window(
        self,
        text: str,
        window_size: Optional[int] = None,
        step_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk text with sliding window approach (overlapping windows).

        Args:
            text: Text content
            window_size: Size of each window (uses chunk_size if None)
            step_size: Step size between windows (uses chunk_size - chunk_overlap if None)
            metadata: Optional metadata

        Returns:
            List of overlapping chunk dicts
        """
        window_size = window_size or self.chunk_size
        step_size = step_size or (self.chunk_size - self.chunk_overlap)

        chunks: List[Dict[str, Any]] = []
        base_metadata = metadata.copy() if metadata else {}

        for i in range(0, len(text), step_size):
            chunk_text = text[i : i + window_size]
            if not chunk_text.strip():
                continue

            chunk_metadata = {
                **base_metadata,
                "chunk_index": len(chunks),
                "window_start": i,
                "window_end": min(i + window_size, len(text)),
                "strategy": "sliding_window",
            }

            chunks.append(
                {
                    "id": f"sliding_chunk_{len(chunks)}",
                    "content": chunk_text,
                    "metadata": chunk_metadata,
                }
            )

        logger.info(f"Created {len(chunks)} sliding window chunks")
        return chunks


# Global chunker instance with default settings
chunker = DocumentChunker(
    chunk_size=settings.rag_chunk_size,
    chunk_overlap=settings.rag_chunk_overlap,
    strategy="recursive",
)
