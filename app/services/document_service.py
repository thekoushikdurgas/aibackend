"""
Document Management Service for RAG
Handles document upload, processing, and management
"""

import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.rag import ChromaVectorStore, DocumentChunker, get_embedding_service
from app.services.rag.document_loader import DocumentLoader
from app.config import settings

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service for managing documents in the RAG system
    """

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        chunker: Optional[DocumentChunker] = None,
    ):
        """
        Initialize document service

        Args:
            vector_store: Vector store instance (uses default if None)
            chunker: Document chunker instance (uses default if None)
        """
        self.vector_store = vector_store or ChromaVectorStore()
        self.chunker = chunker or DocumentChunker()
        self.embedding_service = get_embedding_service()
        # Get upload directory from settings or use default
        upload_dir = getattr(settings, "upload_dir", None)
        if not upload_dir:
            # Use data directory if available, otherwise temp
            data_dir = getattr(settings, "chroma_persist_dir", "./data/chroma")
            upload_dir = str(Path(data_dir).parent / "uploads")
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the service"""
        if not self._initialized:
            await self.vector_store.initialize()
            self._initialized = True
            logger.info("DocumentService initialized")

    async def upload_document(
        self,
        file_path: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload and process a document

        Args:
            file_path: Path to the document file
            document_id: Optional document ID (generated if None)
            metadata: Optional metadata to attach
            collection_name: Optional collection name

        Returns:
            Dict with document_id, chunks_created, status
        """
        await self.initialize()

        # Generate document ID if not provided
        if not document_id:
            document_id = f"doc_{uuid.uuid4().hex[:12]}"

        # Load document
        filename, pages = await DocumentLoader.load_document(file_path)

        # Prepare metadata
        doc_metadata = {
            "filename": filename,
            "file_path": str(file_path),
            "uploaded_at": datetime.utcnow().isoformat(),
            "total_pages": len(pages),
            "file_type": pages[0].get("type", "unknown") if pages else "unknown",
            **(metadata or {}),
        }

        # Process each page/section
        all_chunks: list[dict[str, Any]] = []
        chunk_ids = []
        chunk_embeddings = []
        chunk_metadatas = []

        for page in pages:
            # Chunk the page content
            chunks = self.chunker.chunk_text(
                text=page["content"],
                metadata={
                    **doc_metadata,
                    "source": page["source"],
                    "page": page.get("page", 1),
                },
                document_id=document_id,
            )

            # Generate embeddings for chunks
            chunk_contents = [chunk["content"] for chunk in chunks]
            embeddings = self.embedding_service.embed_texts(chunk_contents)

            # Prepare for batch insert
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{len(all_chunks)}"
                all_chunks.append(chunk)
                chunk_ids.append(chunk_id)
                chunk_embeddings.append(embeddings[i])
                # Ensure document_id is in metadata for deletion
                chunk_meta = chunk.get("metadata", {})
                chunk_meta["document_id"] = document_id
                chunk_metadatas.append(chunk_meta)

        # Add to vector store
        if chunk_ids:
            await self.vector_store.add_documents(
                collection_name=collection_name or self.vector_store.collection_name,
                documents=[
                    {
                        "id": chunk_id,
                        "content": chunk["content"],
                        "metadata": chunk_meta,
                    }
                    for chunk_id, chunk, chunk_meta in zip(
                        chunk_ids, all_chunks, chunk_metadatas
                    )
                ],
                embeddings=chunk_embeddings,
            )

        logger.info(f"Uploaded document {document_id}: {len(chunk_ids)} chunks created")

        return {
            "document_id": document_id,
            "filename": filename,
            "chunks_created": len(chunk_ids),
            "pages": len(pages),
            "status": "uploaded",
            "collection": collection_name or self.vector_store.collection_name,
        }

    async def list_documents(
        self, collection_name: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """
        List documents in the vector store

        Args:
            collection_name: Collection to list from
            limit: Maximum number of documents to return
            offset: Offset for pagination

        Returns:
            Dict with documents list and count
        """
        await self.initialize()

        collection = collection_name or self.vector_store.collection_name

        # Get all chunks from the collection
        collection_obj = self.vector_store.get_collection()
        all_results = collection_obj.get(include=["metadatas", "documents"])

        # Aggregate chunks by document_id
        documents_map = {}

        for i, chunk_id in enumerate(all_results.get("ids", [])):
            metadata = (
                all_results.get("metadatas", [{}])[i]
                if i < len(all_results.get("metadatas", []))
                else {}
            )
            document_id = metadata.get("document_id")

            # If no document_id in metadata, try to extract from chunk_id
            if not document_id and "_chunk_" in chunk_id:
                # Extract document_id from chunk_id format: "doc_xxx_chunk_N"
                parts = chunk_id.split("_chunk_")
                if len(parts) > 0:
                    document_id = parts[0]

            if document_id:
                if document_id not in documents_map:
                    # Get document content preview (first chunk)
                    content_preview = ""
                    if i < len(all_results.get("documents", [])):
                        content_preview = (
                            all_results.get("documents", [])[i][:200]
                            if all_results.get("documents", [])[i]
                            else ""
                        )

                    documents_map[document_id] = {
                        "id": document_id,
                        "filename": metadata.get("filename", f"Document {document_id}"),
                        "source": metadata.get("source", "N/A"),
                        "category": metadata.get("category", "N/A"),
                        "created_at": metadata.get(
                            "uploaded_at", metadata.get("added_at", "N/A")
                        ),
                        "total_pages": metadata.get("total_pages", 1),
                        "file_type": metadata.get("file_type", "unknown"),
                        "chunk_count": 0,
                        "preview": content_preview,
                    }

                documents_map[document_id]["chunk_count"] += 1

        # Convert to list and sort by created_at (most recent first)
        documents = list(documents_map.values())
        documents.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Apply pagination
        total_count = len(documents)
        paginated_documents = documents[offset : offset + limit]

        return {
            "documents": paginated_documents,
            "count": total_count,
            "collection": collection,
            "limit": limit,
            "offset": offset,
        }

    async def delete_document(
        self, document_id: str, collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a document and all its chunks

        Args:
            document_id: Document ID to delete
            collection_name: Collection name

        Returns:
            Dict with deletion status
        """
        await self.initialize()

        collection = collection_name or self.vector_store.collection_name

        # Delete all chunks for this document
        # ChromaDB doesn't support wildcard deletion, so we need to get all chunks first
        # Try to delete by document_id in metadata, or by ID prefix
        deleted_count = 0
        try:
            # First try metadata filter (if document_id is stored in metadata)
            deleted_count = await self.vector_store.delete_by_metadata(
                collection_name=collection, filter={"document_id": document_id}
            )
            if deleted_count > 0:
                logger.info(
                    f"Deleted {deleted_count} chunks by metadata filter for document {document_id}"
                )
        except Exception as e:
            logger.debug(
                f"Metadata filter deletion failed: {e}, trying ID prefix match"
            )

        # If metadata filter didn't work, try to get all chunks and filter by ID prefix
        if deleted_count == 0:
            try:
                # Get all chunks and filter by ID prefix
                # Note: This is inefficient for large collections
                # A better approach would be to maintain a document-to-chunks mapping
                collection_obj = self.vector_store.get_collection()
                all_results = collection_obj.get(include=[])

                # Find chunks with matching document_id prefix
                matching_ids = []
                for chunk_id in all_results.get("ids", []):
                    if chunk_id.startswith(document_id + "_chunk_"):
                        matching_ids.append(chunk_id)

                if matching_ids:
                    collection_obj.delete(ids=matching_ids)
                    deleted_count = len(matching_ids)
                    logger.info(
                        f"Deleted {deleted_count} chunks by ID prefix for document {document_id}"
                    )
            except Exception as e:
                logger.warning(f"Could not delete document {document_id}: {e}")
                deleted_count = 0

        logger.info(f"Deleted document {document_id}: {deleted_count} chunks removed")

        return {
            "document_id": document_id,
            "chunks_deleted": deleted_count,
            "status": "deleted",
        }

    async def get_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about the vector store

        Args:
            collection_name: Collection name

        Returns:
            Dict with statistics
        """
        await self.initialize()

        collection = collection_name or self.vector_store.collection_name
        count = await self.vector_store.count(collection)

        # Get embedding dimension
        dimension = self.embedding_service.dimension

        return {
            "collection": collection,
            "total_chunks": count,
            "embedding_model": self.embedding_service.model_name,
            "embedding_dimension": dimension,
            "chunk_size": self.chunker.chunk_size,
            "chunk_overlap": self.chunker.chunk_overlap,
        }

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        collection_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for documents using semantic search

        Args:
            query: Search query
            top_k: Number of results to return
            collection_name: Collection to search
            filters: Optional metadata filters

        Returns:
            List of search results
        """
        await self.initialize()

        collection = collection_name or self.vector_store.collection_name

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)

        # Search vector store
        results = await self.vector_store.search(
            collection_name=collection,
            query_embedding=query_embedding,
            top_k=top_k,
            filter=filters,
        )

        # Format results
        return [
            {
                "id": result.id,
                "content": result.content,
                "metadata": result.metadata,
                "score": result.score,
            }
            for result in results
        ]


# Global instance
document_service = DocumentService()
