"""
Unified AI Service Layer - Abstraction over Multi-Provider LLM Support
"""

import logging
from typing import List, Dict, Optional, AsyncGenerator, Any
from datetime import datetime

from app.config import settings
from app.services.llm import (
    get_llm_provider,
    LLMProviderFactory,
    LLMConfig,
    LLMResponse,
)
from app.core.streaming_processor import (
    StreamingProcessor,
    TokenCounter,
)

logger = logging.getLogger(__name__)


class AIService:
    """
    Unified AI service that wraps existing LLM providers with streaming optimization,
    token counting, and response normalization.
    """

    def __init__(self):
        """Initialize AI service with streaming processor."""
        self.streaming_processor = StreamingProcessor(
            chunk_size=settings.streaming_chunk_size,
            buffer_time=settings.streaming_buffer_time,
            max_buffer_size=settings.streaming_max_buffer_size,
        )
        self.token_counter = TokenCounter()

    async def stream_response(
        self,
        prompt: str,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        enable_token_counting: bool = True,
        enable_buffering: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from selected AI provider with optimization.

        Args:
            prompt: User's input prompt
            provider_name: LLM provider name (uses default if None)
            model: Model name (uses provider default if None)
            config: LLM configuration (temperature, max_tokens, etc.)
            context: Optional context to include
            conversation_history: Previous conversation messages
            enable_token_counting: Track token usage
            enable_buffering: Use buffering optimization

        Yields:
            Dict with streaming chunks and metadata
        """
        # Get provider
        provider = get_llm_provider(provider_name)

        # Build config
        if config is None:
            config = LLMConfig(model=model, temperature=0.7, max_tokens=2048)
        elif model:
            config.model = model

        logger.info(
            f"Streaming response from {provider.provider_name} "
            f"(model: {config.model or 'default'})"
        )

        try:
            # Get raw stream from provider
            raw_stream = provider.stream(
                prompt=prompt,
                config=config,
                context=context,
                conversation_history=conversation_history,
            )

            # Apply token counting if enabled
            if enable_token_counting:
                stream = self.token_counter.count_tokens_in_stream(raw_stream)
            else:
                stream = raw_stream

            # Apply buffering if enabled
            if enable_buffering:
                stream = self.streaming_processor.process_stream(stream)

            # Stream with timeout protection
            stream = self.streaming_processor.stream_with_timeout(
                stream, timeout=settings.streaming_timeout
            )

            # Yield formatted chunks
            start_time = datetime.utcnow()
            chunk_index = 0
            full_content = ""

            async for chunk in stream:
                full_content += chunk
                chunk_index += 1

                yield {
                    "type": "chunk",
                    "content": chunk,
                    "index": chunk_index,
                    "full_content": full_content,
                    "provider": provider.provider_name,
                    "model": config.model or provider.default_model,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Final completion message with stats
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            stats = self.token_counter.get_stats() if enable_token_counting else {}

            yield {
                "type": "complete",
                "full_content": full_content,
                "total_chunks": chunk_index,
                "provider": provider.provider_name,
                "model": config.model or provider.default_model,
                "elapsed_seconds": elapsed,
                "stats": stats,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Reset token counter for next request
            if enable_token_counting:
                self.token_counter.reset()

        except Exception as e:
            logger.error(f"Error streaming response: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "provider": provider.provider_name,
                "timestamp": datetime.utcnow().isoformat(),
            }
            raise

    async def generate_response(
        self,
        prompt: str,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMResponse:
        """
        Generate non-streaming response from AI provider.

        Args:
            prompt: User's input prompt
            provider_name: LLM provider name (uses default if None)
            model: Model name (uses provider default if None)
            config: LLM configuration
            context: Optional context to include
            conversation_history: Previous conversation messages

        Returns:
            LLMResponse with generated text and metadata
        """
        provider = get_llm_provider(provider_name)

        if config is None:
            config = LLMConfig(model=model, temperature=0.7, max_tokens=2048)
        elif model:
            config.model = model

        logger.info(
            f"Generating response from {provider.provider_name} "
            f"(model: {config.model or 'default'})"
        )

        try:
            response = await provider.generate(
                prompt=prompt,
                config=config,
                context=context,
                conversation_history=conversation_history,
            )
            return response
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            raise

    async def stream_with_retry(
        self,
        prompt: str,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_retries: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response with automatic retry on failure.

        Args:
            prompt: User's input prompt
            provider_name: LLM provider name
            model: Model name
            config: LLM configuration
            context: Optional context
            conversation_history: Previous messages
            max_retries: Maximum retry attempts (uses config default if None)

        Yields:
            Dict with streaming chunks
        """
        max_retries = max_retries or settings.streaming_max_retries

        async def _stream_func():
            async for chunk in self.stream_response(
                prompt=prompt,
                provider_name=provider_name,
                model=model,
                config=config,
                context=context,
                conversation_history=conversation_history,
            ):
                yield chunk

        async for chunk in self.streaming_processor.stream_with_retry(
            _stream_func,
            max_retries=max_retries,
            retry_delay=settings.streaming_retry_delay,
            exponential_backoff=settings.streaming_enable_exponential_backoff,
        ):
            yield chunk

    def list_providers(self) -> List[Dict[str, Any]]:
        """
        List all available LLM providers with status.

        Returns:
            List of provider info dicts
        """
        providers = []
        for name in LLMProviderFactory.list_providers():
            try:
                provider = LLMProviderFactory.get_provider(name)
                providers.append(
                    {
                        "name": name,
                        "default_model": getattr(provider, "default_model", None),
                        "provider_name": provider.provider_name,
                    }
                )
            except Exception as e:
                logger.warning(f"Error getting provider {name}: {e}")
                providers.append({"name": name, "error": str(e)})
        return providers

    async def health_check(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Check health of AI provider(s).

        Args:
            provider_name: Specific provider to check (checks all if None)

        Returns:
            Health status dict
        """
        if provider_name:
            try:
                provider = get_llm_provider(provider_name)
                healthy = await provider.health_check()
                return {
                    "provider": provider_name,
                    "status": "healthy" if healthy else "unhealthy",
                }
            except Exception as e:
                return {"provider": provider_name, "status": "error", "error": str(e)}
        else:
            # Check all providers
            results = {}
            for name in LLMProviderFactory.list_providers():
                try:
                    provider = get_llm_provider(name)
                    healthy = await provider.health_check()
                    results[name] = {"status": "healthy" if healthy else "unhealthy"}
                except Exception as e:
                    results[name] = {"status": "error", "error": str(e)}
            return results


# Global AI service instance
ai_service = AIService()
