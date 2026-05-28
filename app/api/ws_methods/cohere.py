"""Cohere WebSocket method handlers."""

from typing import Dict, Any, Optional

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.cohere.summarization import CohereSummarizer
from app.services.cohere.embeddings import CohereEmbeddings
from app.services.cohere.classification import CohereClassifier


async def handle_cohere_summarize(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    text = params.get("text")
    if not text:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing text")
    service = CohereSummarizer()
    return await service.summarize(
        text=text,
        model=params.get("model"),
        length=params.get("length"),
        format=params.get("format"),
        extractiveness=params.get("extractiveness"),
        temperature=params.get("temperature"),
    )


async def handle_cohere_embed(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    texts = params.get("texts")
    if not texts:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing texts")
    service = CohereEmbeddings()
    return await service.embed(
        texts=texts,
        model=params.get("model"),
        input_type=params.get("input_type", "search_document"),
        truncate=params.get("truncate", "END"),
    )


async def handle_cohere_classify(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    inputs = params.get("inputs")
    examples = params.get("examples")
    if not inputs or not examples:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing inputs/examples")
    service = CohereClassifier()
    return await service.classify(
        inputs=inputs,
        examples=examples,
        model=params.get("model"),
        truncate=params.get("truncate", "END"),
    )


def get_methods() -> Dict[str, Any]:
    return {
        "cohere.summarize": handle_cohere_summarize,
        "cohere.embed": handle_cohere_embed,
        "cohere.classify": handle_cohere_classify,
    }
