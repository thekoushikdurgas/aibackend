"""
Chat method handlers
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, AsyncGenerator, Union

from app.services.llm import get_llm_provider, LLMConfig, LLMProviderFactory
from app.services.ai_service import ai_service
from app.services.memory import get_conversation_memory
from app.services.rag import RAGRetriever
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_chat_completions(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """Handle chat.completions method"""
    # Extract parameters
    message = params.get("message", "")
    if not message:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: message"
        )

    provider_name = params.get("provider")
    model = params.get("model")
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("max_tokens", 2048)
    context = params.get("context")
    conversation_id = params.get("conversation_id") or connection_id
    use_rag = params.get("use_rag", False)
    stream = params.get("stream", False)

    # Get LLM provider
    try:
        provider = get_llm_provider(provider_name)
    except Exception as e:
        raise JSONRPCError(JSONRPCErrorCode.PROVIDER_ERROR, f"Provider error: {str(e)}")

    # Build LLM config
    config = LLMConfig(
        model=model or provider.default_model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Get conversation history
    memory = get_conversation_memory()
    history = []
    if conversation_id:
        # Use sync version for backward compatibility
        history = memory.get_history_sync(conversation_id, max_messages=10)
        # Convert to format expected by provider
        history = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in history
        ]

    # Get RAG context if requested
    if use_rag:
        try:
            retriever = RAGRetriever()
            rag_context = retriever.retrieve_and_format(message, k=3)
            if rag_context:
                context = f"{context}\n\n{rag_context}" if context else rag_context
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    # Handle streaming
    if stream:
        return _stream_chat_response_enhanced(
            provider_name, config, message, context, history, conversation_id, memory
        )

    # Non-streaming response
    try:
        response = await provider.generate(
            prompt=message, config=config, context=context, conversation_history=history
        )

        # Store in memory if conversation_id provided
        if conversation_id:
            # Use sync version for backward compatibility
            memory.add_message_sync(conversation_id, "user", message)
            memory.add_message_sync(
                conversation_id,
                "assistant",
                response.text,
                metadata={
                    "provider": response.provider,
                    "model": response.model,
                    "usage": response.usage,
                },
            )

        return {
            "message": response.text,
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage,
            "finish_reason": response.finish_reason,
        }
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Chat completion failed: {str(e)}"
        )


async def _stream_chat_response_enhanced(
    provider_name: Optional[str],
    config: LLMConfig,
    message: str,
    context: Optional[str],
    history: list,
    conversation_id: Optional[str],
    memory,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream chat response using enhanced AIService with streaming optimization.
    """
    try:
        # Use AIService for optimized streaming
        async for chunk_data in ai_service.stream_response(
            prompt=message,
            provider_name=provider_name,
            model=config.model,
            config=config,
            context=context,
            conversation_history=history,
            enable_token_counting=True,
            enable_buffering=True,
        ):
            # Format for JSON-RPC 2.0 compatibility
            if chunk_data["type"] == "chunk":
                yield {
                    "type": "chunk",
                    "content": chunk_data["content"],
                    "index": chunk_data.get("index", 0),
                    "provider": chunk_data.get("provider"),
                    "model": chunk_data.get("model"),
                }
            elif chunk_data["type"] == "complete":
                # Store in memory
                full_response = chunk_data.get("full_content", "")
                provider = chunk_data.get("provider")
                model = chunk_data.get("model")

                if conversation_id and full_response:
                    # Use sync version for backward compatibility
                    memory.add_message_sync(conversation_id, "user", message)
                    memory.add_message_sync(
                        conversation_id,
                        "assistant",
                        full_response,
                        metadata={"provider": provider, "model": model},
                    )

                yield {
                    "type": "done",
                    "full_response": full_response,
                    "stats": chunk_data.get("stats", {}),
                    "provider": provider,
                    "model": model,
                }
            elif chunk_data["type"] == "error":
                yield {
                    "type": "error",
                    "error": chunk_data.get("error", "Unknown error"),
                }

    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        yield {"type": "error", "error": str(e)}


async def _stream_chat_response(
    provider,
    config: LLMConfig,
    message: str,
    context: Optional[str],
    history: list,
    conversation_id: Optional[str],
    memory,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Legacy streaming function (kept for backward compatibility).
    Prefer _stream_chat_response_enhanced for new code.
    """
    # Send start message
    yield {"type": "start", "provider": provider.provider_name, "model": config.model}

    # Stream response
    full_response = ""
    try:
        async for chunk in provider.stream(
            prompt=message, config=config, context=context, conversation_history=history
        ):
            full_response += chunk
            yield {"type": "chunk", "content": chunk}

        # Send completion
        yield {"type": "done", "full_response": full_response}

        # Store in memory
        if conversation_id:
            # Use sync version for backward compatibility
            memory.add_message_sync(conversation_id, "user", message)
            # Extract provider/model from last chunk if available
            provider = None
            model = None
            # Note: full_response already contains the complete message
            memory.add_message_sync(
                conversation_id,
                "assistant",
                full_response,
                metadata={"provider": provider, "model": model},
            )

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield {"type": "error", "error": str(e)}


async def handle_chat_providers(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle chat.providers method - list available providers"""
    providers = []
    for name in LLMProviderFactory.list_providers():
        try:
            provider = LLMProviderFactory.get_provider(name)
            healthy = await provider.health_check()
            models = await provider.list_models() if healthy else []
            providers.append(
                {
                    "name": name,
                    "status": "available" if healthy else "unavailable",
                    "models": models[:10],
                }
            )
        except Exception as e:
            providers.append(
                {"name": name, "status": "error", "error": str(e), "models": []}
            )

    return {"providers": providers}


async def handle_chat_provider_models(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle chat.providers.{provider_name}.models method"""
    provider_name = params.get("provider_name")
    if not provider_name:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: provider_name"
        )

    try:
        provider = LLMProviderFactory.get_provider(provider_name)
        healthy = await provider.health_check()

        if not healthy:
            return {"provider": provider_name, "status": "unavailable", "models": []}

        models = await provider.list_models()

        return {
            "provider": provider_name,
            "status": "available",
            "default_model": provider.default_model,
            "models": models,
        }
    except ValueError:
        raise JSONRPCError(
            JSONRPCErrorCode.PROVIDER_ERROR, f"Provider '{provider_name}' not found"
        )
    except Exception as e:
        logger.error(f"Error listing models for {provider_name}: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Error listing models: {str(e)}"
        )


async def handle_chat_conversations_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle chat.conversations.list method"""
    limit = params.get("limit", 50)
    memory = get_conversation_memory()
    conversations = await memory.list_conversations(limit)
    return {"conversations": conversations}


async def handle_chat_conversations_get(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle chat.conversations.get method"""
    conversation_id = params.get("conversation_id")
    if not conversation_id:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Missing required parameter: conversation_id",
        )

    memory = get_conversation_memory()
    conversation = await memory.get_conversation(conversation_id)

    if conversation is None:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            f"Conversation '{conversation_id}' not found",
        )

    return conversation.to_dict()


async def handle_chat_conversations_delete(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle chat.conversations.delete method"""
    conversation_id = params.get("conversation_id")
    if not conversation_id:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Missing required parameter: conversation_id",
        )

    memory = get_conversation_memory()
    deleted = await memory.delete_conversation(conversation_id)

    if not deleted:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            f"Conversation '{conversation_id}' not found",
        )

    return {"deleted": True, "conversation_id": conversation_id}


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "chat.completions": handle_chat_completions,
        "chat.providers": handle_chat_providers,
        "chat.providers.models": handle_chat_provider_models,
        "chat.conversations.list": handle_chat_conversations_list,
        "chat.conversations.get": handle_chat_conversations_get,
        "chat.conversations.delete": handle_chat_conversations_delete,
    }
