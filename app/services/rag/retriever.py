"""
RAG Retriever - Document retrieval and context building
"""

import logging
from typing import Any, Dict, List, Optional
import re

from app.models.schemas import PageData
from app.utils.helpers import generate_hash
from .vectorstore import ChromaVectorStore, get_shared_chroma_vector_store

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    Retrieval-Augmented Generation retriever.
    Handles document ingestion, chunking, and retrieval.
    """

    def __init__(self, vector_store: Optional[ChromaVectorStore] = None):
        """
        Initialize RAG retriever.

        Args:
            vector_store: Vector store instance (creates default if not provided)
        """
        self.vector_store = vector_store or get_shared_chroma_vector_store()

    def ingest_page(
        self,
        page_data: PageData,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingest a page into the vector store.

        Args:
            page_data: Page data to ingest
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            metadata: Additional metadata

        Returns:
            Ingestion result with document ID and chunk count
        """
        # Extract text content
        text_content = self._extract_text(page_data)

        if not text_content:
            return {
                "success": False,
                "document_id": None,
                "chunks_created": 0,
                "message": "No text content to ingest",
            }

        # Generate document ID based on URL
        doc_id = generate_hash(page_data.url)

        # Create chunks
        chunks = self._create_chunks(text_content, chunk_size, chunk_overlap)

        # Prepare base metadata
        base_metadata = {
            "url": page_data.url,
            "title": page_data.title or "",
            "domain": page_data.domain or "",
            "doc_id": doc_id,
        }

        if metadata:
            base_metadata.update(metadata)

        # Create documents for each chunk
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            documents.append(
                {
                    "id": chunk_id,
                    "content": chunk,
                    "metadata": {
                        **base_metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    },
                }
            )

        # Delete existing documents for this URL
        # Use sync version for backward compatibility
        self.vector_store.delete_by_metadata_sync({"url": page_data.url})

        # Add new documents (use sync version)
        self.vector_store.add_documents_sync(documents)

        logger.info(f"Ingested page {page_data.url}: {len(chunks)} chunks")

        return {
            "success": True,
            "document_id": doc_id,
            "chunks_created": len(chunks),
            "message": f"Successfully ingested {len(chunks)} chunks",
        }

    def _jaccard_chunks(self, a: str, b: str) -> float:
        wa = set(a.lower().split())
        wb = set(b.lower().split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    def retrieve_mmr(
        self,
        query: str,
        k: int = 12,
        final_k: int = 6,
        filter: Optional[Dict[str, Any]] = None,
        lambda_param: float = 0.65,
    ) -> List[Dict[str, Any]]:
        """
        Maximal Marginal Relevance: diversity among top-k vector hits.
        """
        results = self.retrieve(query, k=k, filter=filter)
        if not results:
            return []
        if len(results) <= final_k:
            return results
        selected: List[Dict[str, Any]] = [results[0]]
        remaining = results[1:]
        while len(selected) < final_k and remaining:
            best_i = 0
            best_score = -1e9
            for i, cand in enumerate(remaining):
                rel = float(cand.get("score", 0))
                div = max(
                    self._jaccard_chunks(
                        cand.get("content") or "", s.get("content") or ""
                    )
                    for s in selected
                )
                mmr = lambda_param * rel - (1.0 - lambda_param) * div
                if mmr > best_score:
                    best_score = mmr
                    best_i = i
            selected.append(remaining.pop(best_i))
        return selected

    def retrieve(
        self, query: str, k: int = 5, filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            k: Number of results
            filter: Optional metadata filter

        Returns:
            List of relevant documents with scores
        """
        # Use sync version for backward compatibility
        return self.vector_store.search_sync(query, k=k, filter=filter)

    def retrieve_and_format(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        max_context_length: int = 4000,
    ) -> str:
        """
        Retrieve relevant documents and format as context string.

        Args:
            query: Search query
            k: Number of results
            filter: Optional metadata filter
            max_context_length: Maximum length of context

        Returns:
            Formatted context string
        """
        results = self.retrieve(query, k=k, filter=filter)

        if not results:
            return ""

        # Build context string
        context_parts = []
        total_length = 0

        for i, result in enumerate(results, 1):
            content = result["content"]
            metadata = result.get("metadata", {})
            score = result.get("score", 0)

            # Format source info
            source = metadata.get("url", "Unknown source")
            title = metadata.get("title", "")

            part = (
                f"[Source {i}: {title or source} (relevance: {score:.2f})]\n{content}\n"
            )

            if total_length + len(part) > max_context_length:
                break

            context_parts.append(part)
            total_length += len(part)

        return "\n".join(context_parts)

    async def retrieve_with_reranking(
        self,
        query: str,
        k: int = 10,
        rerank_top_n: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve with Cohere reranking for improved relevance.

        Args:
            query: Search query
            k: Number of initial candidates to retrieve
            rerank_top_n: Number of top results after reranking
            filter: Optional metadata filter

        Returns:
            List of reranked documents with relevance scores
        """
        # Get initial candidates
        results = self.retrieve(query, k=k, filter=filter)

        if not results:
            return []

        # Extract documents for reranking
        documents = [r["content"] for r in results]

        try:
            # Rerank with Cohere
            from app.services.cohere import CohereReranker

            reranker = CohereReranker()
            rerank_result = await reranker.rerank(
                query=query, documents=documents, top_n=rerank_top_n
            )

            # Map back to original results with new scores
            reranked = []
            for result in rerank_result.get("results", []):
                original_idx = result["index"]
                if original_idx < len(results):
                    original = results[original_idx].copy()
                    original["relevance_score"] = result.get("relevance_score", 0)
                    original["score"] = result.get("relevance_score", 0)  # Update score
                    reranked.append(original)

            return reranked
        except Exception as e:
            logger.warning(f"Cohere reranking failed, returning original results: {e}")
            # Fallback to original results
            return results

    def delete_page(self, url: str) -> int:
        """
        Delete all chunks for a page.

        Args:
            url: Page URL

        Returns:
            Number of chunks deleted
        """
        # Use sync version for backward compatibility
        return self.vector_store.delete_by_metadata_sync({"url": url})

    def search_by_url(self, url: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific URL.

        Args:
            url: Page URL

        Returns:
            List of documents
        """
        # Use a dummy query and filter by URL
        return self.retrieve("", k=100, filter={"url": url})

    def bootstrap_page_sources(
        self,
        page_data: PageData,
        chunk_size: int = 800,
        chunk_overlap: int = 80,
        max_chunks: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        When the vector store has no hits, build in-memory "sources" from the current page text
        so Council Grounded/Verified mode can still cite [S#] from page content.
        """
        text = self._extract_text(page_data)
        if not text.strip():
            return []
        chunks = self._create_chunks(text, chunk_size, chunk_overlap)[:max_chunks]
        out: List[Dict[str, Any]] = []
        for i, ch in enumerate(chunks):
            out.append(
                {
                    "id": f"page_bootstrap_{i}",
                    "content": ch,
                    "metadata": {
                        "url": page_data.url,
                        "title": page_data.title or "",
                        "doc_id": "bootstrap",
                    },
                    "score": 0.5,
                }
            )
        return out

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        # Use sync version for backward compatibility
        count = self.vector_store.count_sync()
        return {
            "total_chunks": count,
            "collection_name": self.vector_store.collection_name,
        }

    def _extract_text(self, page_data: PageData) -> str:
        """Extract text content from page data"""
        # Try to get clean text from HTML
        if page_data.html or page_data.body_html:
            try:
                from app.utils.html_parser import HTMLParser

                html_content = (page_data.html or page_data.body_html) or ""
                if html_content:
                    parser = HTMLParser(html_content)
                    return parser.get_text_content(max_length=50000)
            except Exception as e:
                logger.warning(f"Failed to parse HTML: {e}")

        # Fallback: combine available text fields
        parts = []
        if page_data.title:
            parts.append(page_data.title)

        return "\n".join(parts)

    def _create_chunks(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> List[str]:
        """
        Split text into overlapping chunks.
        Tries to split on sentence boundaries.
        """
        if not text:
            return []

        # Clean text
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to find a good break point
            if end < len(text):
                # Look for sentence end
                for sep in [". ", "! ", "? ", "\n", "; ", ", "]:
                    last_sep = text.rfind(sep, start + chunk_size // 2, end)
                    if last_sep != -1:
                        end = last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap
            start = end - chunk_overlap
            if start >= len(text):
                break

        return chunks
