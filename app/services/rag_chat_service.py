"""
RAG Chat Service
Integrates RAG retrieval with LLM chat for context-aware responses
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime

from app.services.rag import rag_pipeline, ChromaVectorStore
from app.services.llm import get_llm_provider, LLMConfig
from app.config import settings

logger = logging.getLogger(__name__)


class RAGChatService:
    """
    Service for RAG-enhanced chat with streaming support
    """

    def __init__(self, vector_store: Optional[ChromaVectorStore] = None):
        """
        Initialize RAG chat service

        Args:
            vector_store: Vector store instance (uses default if None)
        """
        self.vector_store = vector_store or ChromaVectorStore()
        self.rag_pipeline = rag_pipeline
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the service"""
        if not self._initialized:
            await self.rag_pipeline.initialize()
            self._initialized = True
            logger.info("RAGChatService initialized")

    async def process_rag_stream(
        self,
        query: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_k: int = 5,
        collection_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        enable_reranking: bool = False,
        max_context_length: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process RAG query with streaming LLM response

        Args:
            query: User query
            provider: LLM provider name
            model: Model name
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            top_k: Number of documents to retrieve
            collection_name: Collection to search
            filters: Optional metadata filters
            enable_reranking: Enable reranking
            max_context_length: Max context length

        Yields:
            Dict with type ('retrieving', 'streaming', 'sources', 'complete') and data
        """
        await self.initialize()

        # Step 1: Retrieve relevant documents
        yield {
            "type": "retrieving",
            "message": "Searching knowledge base...",
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Use RAG pipeline to retrieve documents
            rag_raw = await self.rag_pipeline.query(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                filters=filters,
                enable_reranking=enable_reranking,
                max_context_length=max_context_length,
            )
            assert isinstance(rag_raw, dict)
            rag_result = rag_raw

            retrieved_docs = rag_result.get("sources", [])
            context = rag_result.get("context", "")

            # Step 2: Build prompt with context
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(query, context, retrieved_docs)

            # Step 3: Stream LLM response
            yield {
                "type": "streaming",
                "message": "Generating response...",
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Get LLM provider
            llm_provider = get_llm_provider(provider or settings.default_llm_provider)

            # Build LLM config
            llm_config = LLMConfig(
                model=model or settings.default_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Stream response
            full_response = ""
            # Build messages for chat
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            async for chunk in llm_provider.stream(
                prompt=user_prompt,
                config=llm_config,
                context=context,
                conversation_history=[messages[0]],  # System message as history
            ):
                if chunk:
                    full_response += chunk
                    yield {
                        "type": "chunk",
                        "content": chunk,
                        "timestamp": datetime.utcnow().isoformat(),
                    }

            # Step 4: Send retrieved documents metadata
            if retrieved_docs:
                doc_metadata = []
                for doc in retrieved_docs:
                    # Handle both VectorSearchResult objects and dicts
                    if hasattr(doc, "id"):
                        # VectorSearchResult object
                        doc_metadata.append(
                            {
                                "id": doc.id,
                                "source": (
                                    doc.metadata.get("source", "Unknown")
                                    if hasattr(doc, "metadata")
                                    else "Unknown"
                                ),
                                "preview": (
                                    (doc.content[:200] + "...")
                                    if hasattr(doc, "content")
                                    and len(doc.content) > 200
                                    else (
                                        doc.content if hasattr(doc, "content") else ""
                                    )
                                ),
                                "relevance": (
                                    doc.score if hasattr(doc, "score") else 0.0
                                ),
                                "page": (
                                    doc.metadata.get("page", 1)
                                    if hasattr(doc, "metadata")
                                    else 1
                                ),
                            }
                        )
                    else:
                        # Dict format from pipeline
                        doc_metadata.append(
                            {
                                "id": doc.get("id", ""),
                                "source": doc.get("metadata", {}).get(
                                    "source", "Unknown"
                                ),
                                "preview": (
                                    (doc.get("content", "")[:200] + "...")
                                    if len(doc.get("content", "")) > 200
                                    else doc.get("content", "")
                                ),
                                "relevance": doc.get("score", 0.0),
                                "page": doc.get("metadata", {}).get("page", 1),
                            }
                        )

                yield {
                    "type": "sources",
                    "documents": doc_metadata,
                    "count": len(doc_metadata),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Step 5: Send completion
            yield {
                "type": "complete",
                "total_tokens": len(full_response.split()),
                "documents_used": len(retrieved_docs),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"RAG chat error: {e}", exc_info=True)
            yield {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _build_system_prompt(self) -> str:
        """Build system prompt for RAG chat"""
        return """You are a helpful AI assistant that answers questions based on the provided context documents.

Instructions:
- Use the context documents to provide accurate, detailed answers
- Cite sources using [Source 1], [Source 2], etc. when referencing specific documents
- If the context doesn't contain relevant information, say so clearly
- Provide comprehensive answers that synthesize information from multiple sources when relevant
- Maintain a helpful and professional tone"""

    def _build_user_prompt(self, query: str, context: str, sources: List[Any]) -> str:
        """Build user prompt with context"""
        prompt = f"Question: {query}\n\n"

        if context:
            prompt += "Context Documents:\n"
            for i, source in enumerate(sources, 1):
                # Handle both VectorSearchResult objects and dicts
                if hasattr(source, "content"):
                    source_content = source.content
                    source_meta = source.metadata if hasattr(source, "metadata") else {}
                    source_name = source_meta.get("source", "Unknown")
                else:
                    source_content = source.get("content", "")
                    source_meta = source.get("metadata", {})
                    source_name = source_meta.get("source", "Unknown")

                prompt += f"\n[Source {i}] {source_name}\n{source_content}\n"

            prompt += "\n"

        prompt += "Please answer the question based on the context documents above. Use citations [Source N] when referencing specific information."

        return prompt


# Global instance
rag_chat_service = RAGChatService()
