"""
OpenRouter LLM Provider
Unified interface for 100+ models from multiple providers
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.config import settings
from app.services.openrouter.monitoring import get_monitor
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter provider using OpenAI-compatible Chat Completions API.
    Provides unified access to 100+ models from OpenAI, Anthropic, Google, Meta, Mistral, etc.
    """

    provider_name = "openrouter"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
    ):
        """
        Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key
            model: Default model to use (e.g., "openrouter/auto" for auto-routing)
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
            site_url: Site URL for tracking (optional)
            app_name: App name for tracking (optional)
        """
        self.api_key = api_key or settings.openrouter_api_key
        self.default_model = model or settings.openrouter_model
        self.timeout = timeout
        self.base_url = base_url or settings.openrouter_base_url
        self.site_url = site_url or settings.openrouter_site_url
        self.app_name = app_name or settings.openrouter_app_name

        # Cache for model list
        self._model_cache: Optional[List[Dict[str, Any]]] = None
        self._model_cache_time: float = 0
        self._model_cache_ttl: float = 3600  # 1 hour cache

        # Response cache (simple in-memory cache)
        self._response_cache: Dict[str, tuple[LLMResponse, float]] = {}
        self._cache_enabled: bool = True
        self._cache_ttl: float = 300  # 5 minutes default

        # Retry configuration
        self._max_retries: int = 3
        self._retry_delay: float = 1.0  # Initial delay in seconds
        self._retry_backoff: float = 2.0  # Exponential backoff multiplier

        # Monitoring
        self._monitor = get_monitor()

        if not self.api_key:
            logger.warning("OpenRouter API key not configured")

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with OpenRouter-specific tracking"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url or "https://durgasai.app",
            "X-Title": self.app_name or "DurgasAI",
        }
        return headers

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build messages array for OpenRouter chat completions API.
        Uses OpenAI-compatible format with system/user/assistant roles.
        """
        messages = []

        # Add system message if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        elif not conversation_history:
            # Only add default system prompt if no conversation history
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "You are DurgasAI, a helpful AI assistant specialized in "
                        "web page analysis, content extraction, and SEO optimization. "
                        "Provide clear, accurate, and helpful responses."
                    ),
                }
            )

        # Add context if provided
        if context:
            context_message = f"Context:\n{context}\n\n"
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] = context_message + messages[0]["content"]
            else:
                messages.insert(0, {"role": "system", "content": context_message})

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                # Ensure role is valid (system, user, assistant)
                if role not in ["system", "user", "assistant"]:
                    role = "user"

                content = msg.get("content", "")
                # Handle multimodal content (list of content items)
                if isinstance(content, list):
                    messages.append({"role": role, "content": content})
                else:
                    messages.append({"role": role, "content": content})

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        return messages

    def _get_cache_key(
        self,
        prompt: str,
        config: Optional[LLMConfig],
        context: Optional[str],
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> str:
        """Generate cache key for request"""
        cache_data = {
            "prompt": prompt,
            "model": config.model if config else None,
            "temperature": config.temperature if config else None,
            "max_tokens": config.max_tokens if config else None,
            "context": context,
            "conversation_history": conversation_history,
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        model_info: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Calculate cost based on model pricing"""
        if model_info:
            pricing = model_info.get("pricing", {})
            prompt_price = float(pricing.get("prompt", "0") or "0")
            completion_price = float(pricing.get("completion", "0") or "0")
        else:
            # Default pricing estimates (per 1M tokens)
            prompt_price = 0.0025
            completion_price = 0.01

        cost = (prompt_tokens / 1_000_000 * prompt_price) + (
            completion_tokens / 1_000_000 * completion_price
        )
        return cost

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMResponse:
        """Generate a response using OpenRouter API with enhanced error handling, caching, and monitoring"""
        if not self.api_key:
            raise Exception("OpenRouter API key not configured")

        start_time = time.time()
        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Check cache first (only for non-streaming, deterministic requests)
        if self._cache_enabled and config.temperature == 0.0:
            cache_key = self._get_cache_key(
                prompt, config, context, conversation_history
            )
            if cache_key in self._response_cache:
                cached_response, cache_time = self._response_cache[cache_key]
                if time.time() - cache_time < self._cache_ttl:
                    logger.debug(f"Cache hit for request: {cache_key[:16]}")
                    return cached_response
                else:
                    # Remove expired cache entry
                    del self._response_cache[cache_key]

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload (OpenAI-compatible format)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }

        # Add stop sequences if provided
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        # Add frequency_penalty and presence_penalty if provided
        if config.frequency_penalty is not None:
            payload["frequency_penalty"] = config.frequency_penalty
        if config.presence_penalty is not None:
            payload["presence_penalty"] = config.presence_penalty

        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()

        # Retry logic with fallback models and exponential backoff
        fallback_models = settings.openrouter_fallback_models or []
        models_to_try = [model] + fallback_models

        last_error = None
        last_status_code = None

        for attempt_model in models_to_try:
            for retry_attempt in range(self._max_retries):
                try:
                    payload["model"] = attempt_model

                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(url, json=payload, headers=headers)
                        response.raise_for_status()
                        data = response.json()

                        # Calculate latency
                        latency_ms = (time.time() - start_time) * 1000

                        # Extract text from OpenAI-compatible response
                        text = ""
                        choices = data.get("choices", [])
                        if choices:
                            message = choices[0].get("message", {})
                            text = message.get("content", "")

                        # Get usage metadata
                        usage = data.get("usage", {})
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        total_tokens = usage.get("total_tokens", 0)

                        # Get finish reason
                        finish_reason = None
                        if choices:
                            finish_reason = choices[0].get("finish_reason")

                        # Extract OpenRouter-specific metadata
                        actual_model = data.get("model", attempt_model)
                        provider = data.get("provider", "unknown")

                        # Get model info for cost calculation
                        model_info = await self.get_model_info(actual_model)
                        cost = self._calculate_cost(
                            actual_model, prompt_tokens, completion_tokens, model_info
                        )

                        # Create response
                        llm_response = LLMResponse(
                            text=text,
                            model=actual_model,
                            provider=f"{self.provider_name} ({provider})",
                            usage={
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens,
                                "total_tokens": total_tokens,
                                "cost": cost,
                            },
                            finish_reason=finish_reason,
                            raw_response=data,
                        )

                        # Cache response if deterministic
                        if self._cache_enabled and config.temperature == 0.0:
                            cache_key = self._get_cache_key(
                                prompt, config, context, conversation_history
                            )
                            self._response_cache[cache_key] = (
                                llm_response,
                                time.time(),
                            )
                            # Limit cache size
                            if len(self._response_cache) > 1000:
                                # Remove oldest entries
                                oldest_key = min(
                                    self._response_cache.keys(),
                                    key=lambda k: self._response_cache[k][1],
                                )
                                del self._response_cache[oldest_key]

                        # Record successful request
                        self._monitor.record_request(
                            model=actual_model,
                            provider=provider,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            latency_ms=latency_ms,
                            success=True,
                        )

                        return llm_response

                except httpx.HTTPStatusError as e:
                    last_error = e
                    last_status_code = e.response.status_code if e.response else None

                    # Don't retry on 4xx errors (except 429 rate limit)
                    if (
                        last_status_code
                        and 400 <= last_status_code < 500
                        and last_status_code != 429
                    ):
                        logger.warning(
                            f"OpenRouter API client error {last_status_code} with model {attempt_model}: {e}"
                        )
                        break  # Don't retry this model

                    # Rate limited - exponential backoff
                    if last_status_code == 429:
                        wait_time = self._retry_delay * (
                            self._retry_backoff**retry_attempt
                        )
                        logger.warning(
                            f"Rate limited, waiting {wait_time:.2f}s before retry {retry_attempt + 1}/{self._max_retries}"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    # Server error - retry with backoff
                    if last_status_code and last_status_code >= 500:
                        wait_time = self._retry_delay * (
                            self._retry_backoff**retry_attempt
                        )
                        logger.warning(
                            f"Server error {last_status_code}, retrying in {wait_time:.2f}s (attempt {retry_attempt + 1}/{self._max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    # Other errors - try next model
                    logger.warning(
                        f"OpenRouter API error with model {attempt_model}: {e}"
                    )
                    break

                except httpx.RequestError as e:
                    last_error = e
                    # Network/connection errors - retry with backoff
                    wait_time = self._retry_delay * (self._retry_backoff**retry_attempt)
                    logger.warning(
                        f"Network error, retrying in {wait_time:.2f}s (attempt {retry_attempt + 1}/{self._max_retries}): {e}"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                except Exception as e:
                    last_error = e
                    logger.error(
                        f"Unexpected error with model {attempt_model}: {e}",
                        exc_info=True,
                    )
                    break  # Don't retry on unexpected errors

        # All models failed - record failure
        latency_ms = (time.time() - start_time) * 1000
        error_type = (
            "http_error" if isinstance(last_error, httpx.HTTPError) else "unknown_error"
        )
        error_message = str(last_error) if last_error else "All models failed"

        self._monitor.record_request(
            model=model,
            provider="unknown",
            latency_ms=latency_ms,
            success=False,
            error_type=error_type,
            error_message=error_message,
        )

        # Raise appropriate error
        if last_error:
            if hasattr(last_error, "response") and last_error.response is not None:
                try:
                    error_data = last_error.response.json()
                    error_msg = error_data.get("error", {}).get(
                        "message", str(last_error)
                    )
                    raise Exception(f"OpenRouter API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"OpenRouter API error: {error_message}")
        else:
            raise Exception("OpenRouter API error: All models failed")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response using OpenRouter API with enhanced error handling"""
        if not self.api_key:
            raise Exception("OpenRouter API key not configured")

        start_time = time.time()
        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload with streaming enabled
        payload = {
            "model": model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True,
        }

        # Add stop sequences if provided
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        # Add frequency_penalty and presence_penalty if provided
        if config.frequency_penalty is not None:
            payload["frequency_penalty"] = config.frequency_penalty
        if config.presence_penalty is not None:
            payload["presence_penalty"] = config.presence_penalty

        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()

        # Track streaming metrics
        total_content = ""
        prompt_tokens = 0
        completion_tokens = 0

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", url, json=payload, headers=headers
                ) as response:
                    response.raise_for_status()

                    buffer = ""
                    async for chunk in response.aiter_text():
                        buffer += chunk

                        # Process Server-Sent Events (SSE) format
                        # Each chunk may contain multiple lines
                        lines = buffer.split("\n")
                        buffer = lines[-1]  # Keep incomplete line in buffer

                        for line in lines[:-1]:
                            line = line.strip()
                            if not line:
                                continue

                            # Skip non-data lines
                            if not line.startswith("data: "):
                                continue

                            # Extract JSON data
                            data_str = line[6:]  # Remove "data: " prefix

                            # Check for [DONE] marker
                            if data_str == "[DONE]":
                                # Record successful streaming request
                                latency_ms = (time.time() - start_time) * 1000
                                self._monitor.record_request(
                                    model=model,
                                    provider="unknown",
                                    prompt_tokens=prompt_tokens,
                                    completion_tokens=completion_tokens,
                                    latency_ms=latency_ms,
                                    success=True,
                                )
                                return

                            try:
                                data = json.loads(data_str)

                                # Extract usage if available
                                usage = data.get("usage")
                                if usage:
                                    prompt_tokens = usage.get(
                                        "prompt_tokens", prompt_tokens
                                    )
                                    completion_tokens = usage.get(
                                        "completion_tokens", completion_tokens
                                    )

                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        total_content += content
                                        yield content

                                    # Check for finish reason
                                    finish_reason = choices[0].get("finish_reason")
                                    if finish_reason:
                                        # Stream ended
                                        latency_ms = (time.time() - start_time) * 1000
                                        self._monitor.record_request(
                                            model=model,
                                            provider="unknown",
                                            prompt_tokens=prompt_tokens,
                                            completion_tokens=completion_tokens,
                                            latency_ms=latency_ms,
                                            success=True,
                                        )
                                        return

                            except json.JSONDecodeError:
                                logger.warning(
                                    f"Failed to parse SSE data: {data_str[:100]}"
                                )
                                continue

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter streaming HTTP error: {e}")
            latency_ms = (time.time() - start_time) * 1000
            self._monitor.record_request(
                model=model,
                provider="unknown",
                latency_ms=latency_ms,
                success=False,
                error_type="http_error",
                error_message=str(e),
            )
            # Fallback to non-streaming
            try:
                response = await self.generate(
                    prompt, config, context, conversation_history
                )
                yield response.text
            except Exception as fallback_error:
                logger.error(f"Fallback generation also failed: {fallback_error}")
                raise Exception(
                    f"OpenRouter streaming failed and fallback failed: {str(e)}"
                )

        except httpx.RequestError as e:
            logger.error(f"OpenRouter streaming network error: {e}")
            latency_ms = (time.time() - start_time) * 1000
            self._monitor.record_request(
                model=model,
                provider="unknown",
                latency_ms=latency_ms,
                success=False,
                error_type="network_error",
                error_message=str(e),
            )
            # Fallback to non-streaming
            try:
                response = await self.generate(
                    prompt, config, context, conversation_history
                )
                yield response.text
            except Exception as fallback_error:
                logger.error(f"Fallback generation also failed: {fallback_error}")
                raise Exception(
                    f"OpenRouter streaming network error and fallback failed: {str(e)}"
                )

        except Exception as e:
            logger.error(f"OpenRouter streaming unexpected error: {e}", exc_info=True)
            latency_ms = (time.time() - start_time) * 1000
            self._monitor.record_request(
                model=model,
                provider="unknown",
                latency_ms=latency_ms,
                success=False,
                error_type="unknown_error",
                error_message=str(e),
            )
            raise

    async def health_check(self) -> bool:
        """Check if OpenRouter API is available"""
        if not self.api_key:
            return False

        try:
            # Try a simple chat completion request with minimal tokens
            url = f"{self.base_url}/chat/completions"
            headers = self._build_headers()
            payload = {
                "model": "openai/gpt-3.5-turbo",  # Use a reliable model for health check
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpenRouter health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available OpenRouter models"""
        # Use cached model list if available
        current_time = time.time()
        if (
            self._model_cache
            and (current_time - self._model_cache_time) < self._model_cache_ttl
        ):
            return [
                model.get("id", "") for model in self._model_cache if model.get("id")
            ]

        if not self.api_key:
            # Return a default list if API key not configured
            return [
                "openrouter/auto",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "anthropic/claude-3.5-sonnet",
                "google/gemini-2.0-flash-001",
                "meta-llama/llama-3.3-70b-instruct",
                "mistralai/mistral-large",
                "deepseek/deepseek-chat",
            ]

        try:
            url = f"{self.base_url}/models"
            headers = self._build_headers()

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Cache the model list
                self._model_cache = data.get("data", [])
                self._model_cache_time = current_time

                # Extract model IDs
                model_ids = [
                    model.get("id", "")
                    for model in self._model_cache
                    if model.get("id")
                ]
                return model_ids

        except Exception as e:
            logger.warning(f"Failed to fetch OpenRouter models: {e}")
            # Return default list on error
            return [
                "openrouter/auto",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "anthropic/claude-3.5-sonnet",
                "google/gemini-2.0-flash-001",
            ]

    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific model.

        Args:
            model_id: Model identifier (e.g., "openai/gpt-4o")

        Returns:
            Model information dictionary or None if not found
        """
        # Refresh model list if cache is stale
        await self.list_models()

        if not self._model_cache:
            return None

        # Find model in cache
        for model in self._model_cache:
            if model.get("id") == model_id:
                return model

        return None
