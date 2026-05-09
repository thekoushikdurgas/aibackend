"""
Advanced RAG Pipeline with Hybrid Search, Reranking, and Context Assembly
"""

import logging
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
import re

from app.config import settings
from .base import VectorDBBase, VectorSearchResult
from .vectorstore import ChromaVectorStore
from .chunking import DocumentChunker
from .embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Production-ready RAG pipeline with:
    - Query preprocessing (expansion, rewriting)
    - Hybrid search (vector + keyword + metadata)
    - Reranking (optional, requires Cohere API)
    - Context assembly with citation tracking
    """

    def __init__(
        self,
        vector_store: Optional[VectorDBBase] = None,
        chunker: Optional[DocumentChunker] = None,
    ):
        """
        Initialize RAG pipeline.

        Args:
            vector_store: Vector database instance (uses ChromaDB default if None)
            chunker: Document chunker instance (uses default if None)
        """
        self.vector_store = vector_store or ChromaVectorStore()
        self.chunker = chunker or DocumentChunker()
        self.embedding_service = get_embedding_service()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the pipeline and vector store."""
        if not self._initialized:
            if isinstance(self.vector_store, ChromaVectorStore):
                await self.vector_store.initialize()
            self._initialized = True
            logger.info("RAG Pipeline initialized")

    async def query(
        self,
        query: str,
        collection_name: Optional[str] = None,
        top_k: int = 5,
        stream: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        enable_reranking: Optional[bool] = None,
        max_context_length: Optional[int] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Execute RAG pipeline query with hybrid search and optional reranking.

        Args:
            query: User query
            collection_name: Collection to search (uses default if None)
            top_k: Number of results to return
            stream: Whether to stream response (not implemented yet)
            filters: Optional metadata filters
            enable_reranking: Enable reranking (uses config default if None)
            max_context_length: Max context length (uses config default if None)

        Returns:
            Dict with response, sources, and context
        """
        await self.initialize()

        if stream:
            from app.services.rag_chat_service import rag_chat_service

            async def _stream() -> AsyncGenerator[Dict[str, Any], None]:
                async for chunk in rag_chat_service.process_rag_stream(
                    query=query,
                    top_k=top_k,
                    collection_name=collection_name,
                    filters=filters,
                    enable_reranking=bool(enable_reranking),
                    max_context_length=max_context_length,
                ):
                    yield chunk

            return _stream()

        # Step 1: Preprocess query
        processed_query = self._preprocess_query(query)

        # Step 2: Generate query embedding
        query_embedding = self.embedding_service.embed_text(processed_query)

        # Step 3: Retrieve relevant documents
        collection = collection_name or (
            self.vector_store.collection_name
            if hasattr(self.vector_store, "collection_name")
            else settings.chroma_collection_name
        )

        # Retrieve more candidates if reranking enabled
        retrieve_k = (
            top_k * 2 if (enable_reranking or settings.rag_enable_reranking) else top_k
        )

        retrieved_docs = await self.vector_store.search(
            collection_name=collection,
            query_embedding=query_embedding,
            top_k=retrieve_k,
            filter=filters,
        )

        # Step 4: Apply hybrid search (keyword matching boost)
        if settings.rag_enable_hybrid_search:
            retrieved_docs = self._apply_hybrid_search(
                query=processed_query, results=retrieved_docs
            )

        # Step 5: Rerank if enabled
        if enable_reranking or settings.rag_enable_reranking:
            retrieved_docs = await self._rerank(
                query=processed_query, documents=retrieved_docs, top_k=top_k
            )
        else:
            # Just take top_k
            retrieved_docs = retrieved_docs[:top_k]

        # Step 6: Build context
        max_length = max_context_length or settings.rag_context_max_length
        context = self._build_context(retrieved_docs, max_length=max_length)

        return {
            "query": query,
            "processed_query": processed_query,
            "context": context,
            "sources": [
                {
                    "id": doc.id,
                    "content": doc.content[:500],  # Preview
                    "metadata": doc.metadata,
                    "score": doc.score,
                }
                for doc in retrieved_docs
            ],
            "num_sources": len(retrieved_docs),
            "context_length": len(context),
        }

    async def ingest_documents(
        self, documents: List[Dict[str, Any]], collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest documents into vector database with intelligent chunking.

        Args:
            documents: List of document dicts with 'content', 'id', 'metadata'
            collection_name: Collection name (uses default if None)

        Returns:
            Ingestion result with counts
        """
        await self.initialize()

        collection = collection_name or (
            self.vector_store.collection_name
            if hasattr(self.vector_store, "collection_name")
            else settings.chroma_collection_name
        )

        # Chunk documents
        chunks = self.chunker.chunk_documents(documents)

        if not chunks:
            return {
                "success": False,
                "chunks_created": 0,
                "message": "No chunks created from documents",
            }

        # Extract text content for embedding
        texts = [chunk["content"] for chunk in chunks]

        # Generate embeddings in batch
        embeddings = self.embedding_service.embed_texts(texts)

        # Prepare documents for insertion
        doc_list = []
        for chunk, embedding in zip(chunks, embeddings):
            doc_list.append(
                {
                    "id": chunk["id"],
                    "content": chunk["content"],
                    "metadata": chunk["metadata"],
                }
            )

        # Insert into vector DB
        await self.vector_store.create_collection(collection)
        await self.vector_store.add_documents(
            collection_name=collection, documents=doc_list, embeddings=embeddings
        )

        logger.info(f"Ingested {len(chunks)} chunks into '{collection}'")

        return {
            "success": True,
            "chunks_created": len(chunks),
            "documents_processed": len(documents),
            "collection": collection,
        }

    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess query: expansion, rewriting, cleaning.

        Args:
            query: Original query

        Returns:
            Processed query
        """
        # Clean whitespace
        query = re.sub(r"\s+", " ", query).strip()

        # Query expansion: Add synonyms and related terms
        query = self._expand_query(query)

        # Query rewriting: Reformulate for better retrieval
        query = self._rewrite_query(query)

        return query

    def _expand_query(self, query: str) -> str:
        """
        Expand query with synonyms and related terms for better retrieval.

        Args:
            query: Original query

        Returns:
            Expanded query with related terms
        """
        # Common technical term expansions (acronyms to full terms)
        expansions = {
            r"\bAI\b": "AI artificial intelligence",
            r"\bML\b": "ML machine learning",
            r"\bDL\b": "DL deep learning",
            r"\bNLP\b": "NLP natural language processing",
            r"\bAPI\b": "API application programming interface",
            r"\bRAG\b": "RAG retrieval augmented generation",
            r"\bLLM\b": "LLM large language model",
            r"\bGPT\b": "GPT generative pre-trained transformer",
        }

        expanded_query = query
        for pattern, replacement in expansions.items():
            expanded_query = re.sub(
                pattern, replacement, expanded_query, flags=re.IGNORECASE
            )

        return expanded_query

    def _rewrite_query(self, query: str) -> str:
        """
        Rewrite query to improve retrieval effectiveness.
        Removes stop words while preserving important terms and structure.

        Args:
            query: Original or expanded query

        Returns:
            Rewritten query optimized for retrieval
        """
        # Common stop words that don't help with semantic search
        # Note: We keep some stop words that might be important for context
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
        }

        words = query.split()

        # For very short queries (1-2 words), keep as-is
        if len(words) <= 2:
            return query

        # For longer queries, filter out stop words but preserve structure
        # Keep important words (longer words, technical terms, question words)
        important_words = []
        for word in words:
            word_lower = word.lower()
            # Keep if: not a stop word, or longer than 3 chars, or is a question word
            if (
                word_lower not in stop_words
                or len(word) > 3
                or word_lower in ["what", "how", "why", "when", "where", "who", "which"]
            ):
                important_words.append(word)

        # Reconstruct query
        if len(important_words) < 2:
            # If filtering removed too much, use original
            rewritten = query
        else:
            rewritten = " ".join(important_words)

        # Normalize spacing
        rewritten = re.sub(r"\s+", " ", rewritten).strip()

        # Ensure we don't return empty or too short queries
        if len(rewritten) < 3:
            rewritten = query

        return rewritten

    def _apply_hybrid_search(
        self, query: str, results: List[VectorSearchResult]
    ) -> List[VectorSearchResult]:
        """
        Apply hybrid search: boost results with keyword matches.

        Args:
            query: Search query
            results: Vector search results

        Returns:
            Re-scored results
        """
        if not results:
            return results

        query_words = [w for w in query.lower().split() if w]
        vector_rank = {item.id: idx for idx, item in enumerate(results, start=1)}

        keyword_rank = {}
        ranked_by_keyword = sorted(
            results,
            key=lambda item: sum(1 for w in query_words if w in item.content.lower()),
            reverse=True,
        )
        for idx, item in enumerate(ranked_by_keyword, start=1):
            keyword_rank[item.id] = idx

        # Reciprocal Rank Fusion for vector + keyword ranking.
        k_rrf = 60
        fused = []
        for item in results:
            v_rank = vector_rank.get(item.id, len(results))
            k_rank = keyword_rank.get(item.id, len(results))
            fused_score = (1 / (k_rrf + v_rank)) + (1 / (k_rrf + k_rank))
            fused.append(
                VectorSearchResult(
                    id=item.id,
                    content=item.content,
                    metadata=item.metadata,
                    score=fused_score,
                )
            )

        fused.sort(key=lambda x: x.score, reverse=True)
        return fused

    async def _rerank(
        self, query: str, documents: List[VectorSearchResult], top_k: int = 5
    ) -> List[VectorSearchResult]:
        """
        Rerank documents using Cohere API if available.

        Args:
            query: Search query
            documents: Initial search results
            top_k: Number of top results to return

        Returns:
            Reranked results
        """
        if not documents:
            return []

        try:
            from app.services.cohere.reranking import CohereReranker

            reranker = CohereReranker()

            # Extract document texts
            doc_texts = [doc.content for doc in documents]

            # Rerank
            rerank_result = await reranker.rerank(
                query=query, documents=doc_texts, top_n=top_k
            )

            # Map back to original results with new scores
            reranked = []
            for result in rerank_result.get("results", []):
                original_idx = result.get("index", 0)
                if original_idx < len(documents):
                    original = documents[original_idx]
                    reranked.append(
                        VectorSearchResult(
                            id=original.id,
                            content=original.content,
                            metadata=original.metadata,
                            score=result.get("relevance_score", original.score),
                        )
                    )

            logger.info(
                f"Reranked {len(documents)} documents, returning top {len(reranked)}"
            )
            return reranked[:top_k]

        except ImportError:
            logger.debug("Cohere reranking not available, skipping")
            return documents[:top_k]
        except Exception as e:
            logger.warning(f"Reranking failed: {e}, returning original results")
            return documents[:top_k]

    def _build_context(
        self, documents: List[VectorSearchResult], max_length: int = 4000
    ) -> str:
        """
        Build context string from retrieved documents with citations.

        Args:
            documents: Retrieved documents
            max_length: Maximum context length

        Returns:
            Formatted context string
        """
        if not documents:
            return ""

        context_parts = []
        total_length = 0

        for i, doc in enumerate(documents, 1):
            # Extract source info
            metadata = doc.metadata or {}
            metadata.get("url", metadata.get("source", "Unknown"))
            title = metadata.get("title", "")
            score = doc.score

            # Format citation
            citation = f"[Source {i}"
            if title:
                citation += f": {title}"
            citation += f" (relevance: {score:.2f})]"

            # Build context part
            part = f"{citation}\n{doc.content}\n\n"

            # Check length limit
            if total_length + len(part) > max_length:
                # Try to fit partial content
                remaining = max_length - total_length - len(citation) - 10
                if remaining > 100:
                    part = f"{citation}\n{doc.content[:remaining]}...\n\n"
                else:
                    break

            context_parts.append(part)
            total_length += len(part)

        return "".join(context_parts).strip()


# Global pipeline instance
rag_pipeline = RAGPipeline()
