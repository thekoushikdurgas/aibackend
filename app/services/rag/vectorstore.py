"""
ChromaDB Vector Store Integration
Implements VectorDBBase interface for multi-backend support.
"""

import logging
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.utils.helpers import utc_now
from .embeddings import get_embedding_service
from .base import VectorDBBase, VectorSearchResult

logger = logging.getLogger(__name__)


class ChromaVectorStore(VectorDBBase):
    """
    ChromaDB vector store for storing and retrieving page embeddings.
    """

    def __init__(
        self, persist_dir: Optional[str] = None, collection_name: Optional[str] = None
    ):
        """
        Initialize ChromaDB vector store.

        Args:
            persist_dir: Directory to persist the database
            collection_name: Name of the collection to use
        """
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name or settings.chroma_collection_name
        self._client: Optional[Any] = None
        self._collection = None
        self._embedding_service = None
        self._initialized = False

    @property
    def client(self) -> Any:
        """Get or create ChromaDB client"""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
            )
            logger.info(f"ChromaDB client initialized at {self.persist_dir}")
        return self._client

    @property
    def embedding_service(self):
        """Get embedding service"""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    async def initialize(self) -> None:
        """Initialize the vector database connection (VectorDBBase interface)"""
        if not self._initialized:
            _ = self.client  # Initialize client
            _ = self.get_collection()  # Initialize collection
            self._initialized = True
            logger.info("ChromaDB initialized")

    def get_collection(self):
        """Get or create the collection"""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name, metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Using collection: {self.collection_name}")
        return self._collection

    async def create_collection(
        self, collection_name: str, dimension: Optional[int] = None
    ) -> None:
        """
        Create or get a collection (VectorDBBase interface).

        Args:
            collection_name: Name of the collection
            dimension: Embedding dimension (not used for ChromaDB, auto-detected)
        """
        self.collection_name = collection_name
        _ = self.get_collection()
        logger.info(f"Collection '{collection_name}' ready")

    async def add_document(
        self,
        collection_name: str,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a single document (VectorDBBase interface).

        Args:
            collection_name: Collection name (uses default if different)
            document_id: Unique document identifier
            content: Text content
            embedding: Vector embedding
            metadata: Optional metadata

        Returns:
            Document ID
        """
        if collection_name != self.collection_name:
            await self.create_collection(collection_name)

        return self.add_document_sync(document_id, content, metadata, embedding)

    def add_document_sync(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """
        Add a single document to the vector store.

        Args:
            document_id: Unique identifier for the document
            content: Text content to store
            metadata: Optional metadata dictionary
            embedding: Pre-computed embedding (generated if not provided)

        Returns:
            Document ID
        """
        collection = self.get_collection()

        # Generate embedding if not provided
        if embedding is None:
            embedding = self.embedding_service.embed_text(content)

        # Prepare metadata
        meta = metadata or {}
        meta["added_at"] = utc_now().isoformat()
        meta["content_preview"] = content[:200]

        # Ensure metadata values are valid types for ChromaDB
        cleaned_meta = self._clean_metadata(meta)

        collection.add(
            ids=[document_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[cleaned_meta],
        )

        logger.debug(f"Added document: {document_id}")
        return document_id

    async def add_documents(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> List[str]:
        """
        Add multiple documents in batch (VectorDBBase interface).

        Args:
            collection_name: Collection name
            documents: List of dicts with 'id', 'content', 'metadata'
            embeddings: List of embedding vectors

        Returns:
            List of document IDs
        """
        if collection_name != self.collection_name:
            await self.create_collection(collection_name)

        return self.add_documents_sync(documents, embeddings)

    def add_documents_sync(
        self,
        documents: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """
        Add multiple documents to the vector store (sync version).

        Args:
            documents: List of document dicts with 'id', 'content', 'metadata'
            embeddings: Optional pre-computed embeddings

        Returns:
            List of document IDs
        """
        collection = self.get_collection()

        ids = []
        contents = []
        metadatas = []

        for doc in documents:
            ids.append(doc["id"])
            contents.append(doc["content"])

            meta = doc.get("metadata", {})
            meta["added_at"] = utc_now().isoformat()
            meta["content_preview"] = doc["content"][:200]
            metadatas.append(self._clean_metadata(meta))

        # Generate embeddings if not provided
        if embeddings is None:
            embeddings = self.embedding_service.embed_texts(contents)

        collection.add(
            ids=ids, embeddings=embeddings, documents=contents, metadatas=metadatas
        )

        logger.info(f"Added {len(ids)} documents")
        return ids

    async def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """
        Search for similar documents (VectorDBBase interface).

        Args:
            collection_name: Collection to search
            query_embedding: Query vector embedding
            top_k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of VectorSearchResult objects
        """
        if collection_name != self.collection_name:
            await self.create_collection(collection_name)

        collection = self.get_collection()

        # Search with embedding
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter,
            include=["documents", "metadatas", "distances"],
        )

        # Convert to VectorSearchResult objects
        search_results = []
        for i in range(len(results["ids"][0])):
            search_results.append(
                VectorSearchResult(
                    id=results["ids"][0][i],
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    score=1
                    - results["distances"][0][i],  # Convert distance to similarity
                )
            )

        return search_results

    def search_sync(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        include_embeddings: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents (sync version, accepts query string).

        Args:
            query: Search query string
            k: Number of results to return
            filter: Optional metadata filter
            include_embeddings: Whether to include embeddings in results

        Returns:
            List of search results with content, metadata, and scores
        """
        collection = self.get_collection()

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)

        # Build include list
        include = ["documents", "metadatas", "distances"]
        if include_embeddings:
            include.append("embeddings")

        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter,
            include=include,
        )

        # Format results
        formatted = []
        for i in range(len(results["ids"][0])):
            result = {
                "id": results["ids"][0][i],
                "content": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "score": 1
                - results["distances"][0][i],  # Convert distance to similarity
            }
            if include_embeddings and results.get("embeddings"):
                result["embedding"] = results["embeddings"][0][i]
            formatted.append(result)

        return formatted

    async def get_document(
        self, collection_name: str, document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID (VectorDBBase interface).

        Args:
            collection_name: Collection name
            document_id: Document ID

        Returns:
            Document dict or None
        """
        if collection_name != self.collection_name:
            await self.create_collection(collection_name)

        collection = self.get_collection()

        results = collection.get(ids=[document_id], include=["documents", "metadatas"])

        if not results["ids"]:
            return None

        return {
            "id": results["ids"][0],
            "content": results["documents"][0] if results["documents"] else "",
            "metadata": results["metadatas"][0] if results["metadatas"] else {},
        }

    async def delete_document(self, collection_name: str, document_id: str) -> bool:
        """
        Delete a document by ID (VectorDBBase interface).

        Args:
            collection_name: Collection name
            document_id: Document ID

        Returns:
            True if deleted
        """
        if collection_name != self.collection_name:
            await self.create_collection(collection_name)

        collection = self.get_collection()

        try:
            collection.delete(ids=[document_id])
            logger.debug(f"Deleted document: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    async def delete_by_metadata(
        self, collection_name: str, filter: Dict[str, Any]
    ) -> int:
        """
        Delete documents matching metadata filter (VectorDBBase interface).

        Args:
            collection_name: Collection name
            filter: Metadata filter

        Returns:
            Number of documents deleted
        """
        if collection_name != self.collection_name:
            await self.create_collection(collection_name)

        collection = self.get_collection()

        # Get matching IDs
        results = collection.get(where=filter, include=[])
        ids = results["ids"]

        if ids:
            collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents matching filter")

        return len(ids)

    async def count(self, collection_name: str) -> int:
        """
        Get document count in collection (VectorDBBase interface).

        Args:
            collection_name: Collection name

        Returns:
            Number of documents
        """
        if collection_name != self.collection_name:
            await self.create_collection(collection_name)

        return self.get_collection().count()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check vector database health (VectorDBBase interface).

        Returns:
            Health status dict
        """
        try:
            _ = self.client
            _ = self.get_collection()
            return {
                "status": "healthy",
                "type": "chromadb",
                "collection": self.collection_name,
                "count": self.get_collection().count(),
            }
        except Exception as e:
            return {"status": "unhealthy", "type": "chromadb", "error": str(e)}

    async def close(self) -> None:
        """
        Close the connection (VectorDBBase interface).
        ChromaDB doesn't require explicit closing, but we can clean up references.
        """
        self._collection = None
        self._client = None
        self._initialized = False
        logger.info("ChromaDB connection closed")

    # Legacy sync methods for backward compatibility
    def get_document_sync(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Legacy sync version"""
        collection = self.get_collection()
        results = collection.get(ids=[document_id], include=["documents", "metadatas"])
        if not results["ids"]:
            return None
        return {
            "id": results["ids"][0],
            "content": results["documents"][0] if results["documents"] else "",
            "metadata": results["metadatas"][0] if results["metadatas"] else {},
        }

    def delete_document_sync(self, document_id: str) -> bool:
        """Legacy sync version"""
        collection = self.get_collection()
        try:
            collection.delete(ids=[document_id])
            return True
        except Exception:
            return False

    def count_sync(self) -> int:
        """Legacy sync version"""
        return self.get_collection().count()

    def delete_by_metadata_sync(self, filter: Dict[str, Any]) -> int:
        """
        Delete documents matching metadata filter (sync version for backward compatibility).

        Args:
            filter: Metadata filter

        Returns:
            Number of documents deleted
        """
        collection = self.get_collection()

        # Get matching IDs
        results = collection.get(where=filter, include=[])
        ids = results["ids"]

        if ids:
            collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents matching filter")

        return len(ids)

    def reset(self):
        """Reset the collection (delete all documents)"""
        self.client.delete_collection(self.collection_name)
        self._collection = None
        logger.warning(f"Reset collection: {self.collection_name}")

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean metadata to ensure valid types for ChromaDB.
        ChromaDB only accepts str, int, float, or bool values.
        """
        cleaned = {}
        for key, value in metadata.items():
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            elif isinstance(value, (list, dict)):
                # Convert complex types to JSON string
                import json

                cleaned[key] = json.dumps(value)
            else:
                cleaned[key] = str(value)
        return cleaned


_shared_chroma_store: Optional[ChromaVectorStore] = None


def get_shared_chroma_vector_store() -> ChromaVectorStore:
    """
    Default-process ChromaDB store (single client + collection).

    Avoids creating a new PersistentClient on every GraphQL / WS path that touches RAG,
    which previously produced noisy logs and extra disk churn.
    """
    global _shared_chroma_store
    if _shared_chroma_store is None:
        _shared_chroma_store = ChromaVectorStore()
    return _shared_chroma_store
