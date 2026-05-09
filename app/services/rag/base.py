"""
Abstract Vector Database Interface
Supports multiple vector database backends (ChromaDB, Pinecone, Milvus, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class VectorSearchResult:
    """Result from vector database search"""

    id: str
    content: str
    metadata: Dict[str, Any]
    score: float  # Similarity score (0-1, higher is better)


class VectorDBBase(ABC):
    """
    Abstract base class for vector database implementations.
    All vector DB backends must implement this interface.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector database connection"""
        pass

    @abstractmethod
    async def create_collection(
        self, collection_name: str, dimension: Optional[int] = None
    ) -> None:
        """
        Create or get a collection.

        Args:
            collection_name: Name of the collection
            dimension: Embedding dimension (optional, auto-detected if None)
        """
        pass

    @abstractmethod
    async def add_document(
        self,
        collection_name: str,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a single document to the collection.

        Args:
            collection_name: Target collection
            document_id: Unique document identifier
            content: Text content
            embedding: Vector embedding
            metadata: Optional metadata

        Returns:
            Document ID
        """
        pass

    @abstractmethod
    async def add_documents(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> List[str]:
        """
        Add multiple documents in batch.

        Args:
            collection_name: Target collection
            documents: List of dicts with 'id', 'content', 'metadata'
            embeddings: List of embedding vectors

        Returns:
            List of document IDs
        """
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """
        Search for similar documents.

        Args:
            collection_name: Collection to search
            query_embedding: Query vector embedding
            top_k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def get_document(
        self, collection_name: str, document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.

        Args:
            collection_name: Collection name
            document_id: Document identifier

        Returns:
            Document dict or None
        """
        pass

    @abstractmethod
    async def delete_document(self, collection_name: str, document_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            collection_name: Collection name
            document_id: Document identifier

        Returns:
            True if deleted, False otherwise
        """
        pass

    @abstractmethod
    async def delete_by_metadata(
        self, collection_name: str, filter: Dict[str, Any]
    ) -> int:
        """
        Delete documents matching metadata filter.

        Args:
            collection_name: Collection name
            filter: Metadata filter dict

        Returns:
            Number of documents deleted
        """
        pass

    @abstractmethod
    async def count(self, collection_name: str) -> int:
        """
        Get document count in collection.

        Args:
            collection_name: Collection name

        Returns:
            Number of documents
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check vector database health.

        Returns:
            Health status dict
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the connection and cleanup resources"""
        pass
