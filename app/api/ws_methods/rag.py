"""
RAG (Retrieval-Augmented Generation) method handlers
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, AsyncGenerator

from app.services.rag import get_shared_chroma_vector_store
from app.config import settings
from app.services.rag.pipeline import rag_pipeline
from app.services.document_service import document_service
from app.services.rag_chat_service import rag_chat_service
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_rag_query(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle rag.query method using advanced RAG pipeline"""
    query = params.get("query", "")
    k = params.get("k", 5)
    max_context_length = params.get("max_context_length")
    collection_name = params.get("collection_name")
    enable_reranking = params.get("enable_reranking")
    filters = params.get("filters")

    if not query:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: query"
        )

    try:
        # Use advanced RAG pipeline
        result = await rag_pipeline.query(
            query=query,
            collection_name=collection_name,
            top_k=k,
            filters=filters,
            enable_reranking=enable_reranking,
            max_context_length=max_context_length,
        )

        if not isinstance(result, dict):
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                "Streaming RAG is not supported for rag.query; omit stream or use the streaming gateway",
            )
        return {
            "query": result["query"],
            "processed_query": result.get("processed_query", query),
            "context": result["context"],
            "sources": result["sources"],
            "num_sources": result["num_sources"],
            "context_length": result["context_length"],
            "k": k,
        }
    except Exception as e:
        logger.error(f"RAG query error: {e}", exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"RAG query failed: {str(e)}"
        )


async def handle_rag_ingest(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle rag.ingest method using advanced pipeline with chunking"""
    text = params.get("text", "")
    document_id = params.get("document_id")
    metadata = params.get("metadata", {})
    collection_name = params.get("collection_name")
    params.get("chunk_strategy", "recursive")

    if not text:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: text"
        )

    try:
        # Use pipeline for intelligent ingestion with chunking
        documents = [
            {
                "id": document_id or f"doc_{hash(text)}",
                "content": text,
                "metadata": metadata,
            }
        ]

        result = await rag_pipeline.ingest_documents(
            documents=documents, collection_name=collection_name
        )

        if result["success"]:
            return {
                "document_id": document_id or documents[0]["id"],
                "chunks_created": result["chunks_created"],
                "status": "ingested",
                "collection": result.get("collection"),
            }
        else:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR,
                result.get("message", "Ingestion failed"),
            )
    except Exception as e:
        logger.error(f"RAG ingest error: {e}", exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"RAG ingest failed: {str(e)}"
        )


async def handle_rag_delete(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle rag.delete method"""
    document_id = params.get("document_id")
    if not document_id:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: document_id"
        )

    try:
        vector_store = get_shared_chroma_vector_store()
        collection = params.get("collection_name") or settings.chroma_collection_name
        deleted = await vector_store.delete_document(collection, document_id)
        return {"document_id": document_id, "deleted": deleted}
    except Exception as e:
        logger.error(f"RAG delete error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"RAG delete failed: {str(e)}"
        )


async def handle_rag_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle rag.list method - list documents with pagination"""
    collection_name = params.get("collection_name")
    limit = params.get("limit", 100)
    offset = params.get("offset", 0)

    try:
        # Use document service for proper document listing with pagination
        result = await document_service.list_documents(
            collection_name=collection_name, limit=limit, offset=offset
        )

        return {
            "documents": result.get("documents", []),
            "count": result.get("count", 0),
            "collection": result.get("collection", collection_name or "durgasai_pages"),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"RAG list error: {e}", exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"RAG list failed: {str(e)}"
        )


async def handle_rag_chat(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Handle rag.chat method with streaming RAG-enhanced responses

    This method streams responses with retrieved document sources
    """
    query = params.get("query", "")
    provider = params.get("provider")
    model = params.get("model")
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("max_tokens", 2048)
    top_k = params.get("top_k", 5)
    collection_name = params.get("collection_name")
    filters = params.get("filters")
    enable_reranking = params.get("enable_reranking", False)
    max_context_length = params.get("max_context_length")

    if not query:
        yield {"type": "error", "error": "Missing required parameter: query"}
        return

    try:
        # Stream RAG chat response
        async for chunk in rag_chat_service.process_rag_stream(
            query=query,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_k=top_k,
            collection_name=collection_name,
            filters=filters,
            enable_reranking=enable_reranking,
            max_context_length=max_context_length,
        ):
            yield chunk
    except Exception as e:
        logger.error(f"RAG chat error: {e}", exc_info=True)
        yield {"type": "error", "error": str(e)}


async def handle_rag_documents_upload(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle rag.documents.upload method"""
    file_path = params.get("file_path")
    document_id = params.get("document_id")
    metadata = params.get("metadata", {})
    collection_name = params.get("collection_name")

    if not file_path:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: file_path"
        )

    try:
        result = await document_service.upload_document(
            file_path=file_path,
            document_id=document_id,
            metadata=metadata,
            collection_name=collection_name,
        )
        return result
    except Exception as e:
        logger.error(f"Document upload error: {e}", exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Document upload failed: {str(e)}"
        )


async def handle_rag_documents_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle rag.documents.list method"""
    collection_name = params.get("collection_name")
    limit = params.get("limit", 100)
    offset = params.get("offset", 0)

    try:
        result = await document_service.list_documents(
            collection_name=collection_name, limit=limit, offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Document list error: {e}", exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Document list failed: {str(e)}"
        )


async def handle_rag_documents_delete(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle rag.documents.delete method"""
    document_id = params.get("document_id")
    collection_name = params.get("collection_name")

    if not document_id:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: document_id"
        )

    try:
        result = await document_service.delete_document(
            document_id=document_id, collection_name=collection_name
        )
        return result
    except Exception as e:
        logger.error(f"Document delete error: {e}", exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Document delete failed: {str(e)}"
        )


async def handle_rag_documents_stats(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle rag.documents.stats method"""
    collection_name = params.get("collection_name")

    try:
        result = await document_service.get_stats(collection_name=collection_name)
        return result
    except Exception as e:
        logger.error(f"Document stats error: {e}", exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Document stats failed: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "rag.query": handle_rag_query,
        "rag.ingest": handle_rag_ingest,
        "rag.delete": handle_rag_delete,
        "rag.list": handle_rag_list,
        "rag.chat": handle_rag_chat,
        "rag.documents.upload": handle_rag_documents_upload,
        "rag.documents.list": handle_rag_documents_list,
        "rag.documents.delete": handle_rag_documents_delete,
        "rag.documents.stats": handle_rag_documents_stats,
    }
