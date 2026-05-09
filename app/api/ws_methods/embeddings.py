"""Embedding method handlers."""

from typing import Dict, Any, Optional
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.gemini.embeddings import GeminiEmbeddingService


async def handle_embeddings_gemini(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    service = GeminiEmbeddingService()
    if "texts" in params:
        texts = params.get("texts") or []
        if not texts:
            raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "texts cannot be empty")
        vectors = await service.embed_texts(texts)
        return {"embeddings": vectors, "count": len(vectors)}
    text = params.get("text")
    if not text:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing text or texts")
    vector = await service.embed_text(text)
    return {"embedding": vector, "dimensions": len(vector)}


def get_methods() -> Dict[str, Any]:
    return {"embeddings.gemini": handle_embeddings_gemini}
