"""
Cerebras AI LLM Provider
Ultra-fast inference using wafer-scale processors
"""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.config import settings
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class CerebrasProvider(BaseLLMProvider):
    """
    Cerebras AI provider using the OpenAI-compatible API.
    Supports both streaming and non-streaming generation.
    Provides ultra-fast inference with detailed timing metrics.
    """

    provider_name = "cerebras"

    # API endpoint
    API_BASE = "https://api.cerebras.ai/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Cerebras provider.

        Args:
            api_key: Cerebras API key
            model: Default model to use
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.api_key = api_key or settings.cerebras_api_key
        self.default_model = model or settings.cerebras_model
        self.timeout = timeout
        self.API_BASE = base_url or settings.cerebras_base_url

        if not self.api_key:
            logger.warning("Cerebras API key not configured")

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build messages array for Cerebras chat completions API.
        Cerebras uses OpenAI-compatible format with system/user/assistant roles.
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

        # Add context if provided (as a system message or prepended to first user message)
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
                messages.append({"role": role, "content": msg.get("content", "")})

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        return messages

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Generate a response using Cerebras AI API"""
        if not self.api_key:
            raise Exception("Cerebras API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload (OpenAI-compatible format)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": config.temperature,
            "max_completion_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }

        # Add optional parameters if provided
        if (
            hasattr(config, "frequency_penalty")
            and config.frequency_penalty is not None
        ):
            payload["frequency_penalty"] = config.frequency_penalty
        if hasattr(config, "presence_penalty") and config.presence_penalty is not None:
            payload["presence_penalty"] = config.presence_penalty

        # Add stop sequences if provided
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        url = f"{self.API_BASE}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Extract text from OpenAI-compatible response
                text = ""
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    text = message.get("content", "")

                # Get usage metadata
                usage = data.get("usage", {})

                # Get finish reason
                finish_reason = None
                if choices:
                    finish_reason = choices[0].get("finish_reason")

                # Extract time_info if available (Cerebras-specific)
                raw_response = data.copy()
                time_info = data.get("time_info")
                extra_metadata = {}
                if time_info:
                    extra_metadata["cerebras_timing"] = time_info
                    logger.debug(f"Cerebras timing: {time_info}")

                # Store enhanced response with time_info
                enhanced_response = (
                    {"data": raw_response, "time_info": time_info}
                    if time_info
                    else raw_response
                )

                return LLMResponse(
                    text=text,
                    model=model,
                    provider=self.provider_name,
                    usage={
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    finish_reason=finish_reason,
                    raw_response=enhanced_response,
                )

        except httpx.HTTPError as e:
            logger.error(f"Cerebras API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Cerebras API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Cerebras API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response using Cerebras AI API"""
        if not self.api_key:
            raise Exception("Cerebras API key not configured")

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
            "max_completion_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True,
        }

        # Add optional parameters if provided
        if (
            hasattr(config, "frequency_penalty")
            and config.frequency_penalty is not None
        ):
            payload["frequency_penalty"] = config.frequency_penalty
        if hasattr(config, "presence_penalty") and config.presence_penalty is not None:
            payload["presence_penalty"] = config.presence_penalty

        # Add stop sequences if provided
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        url = f"{self.API_BASE}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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
                        # Each chunk is a line starting with "data: "
                        lines = buffer.split("\n")
                        buffer = lines[-1]  # Keep incomplete line in buffer

                        for line in lines[:-1]:
                            line = line.strip()
                            if not line or not line.startswith("data: "):
                                continue

                            # Extract JSON data
                            data_str = line[6:]  # Remove "data: " prefix

                            # Check for [DONE] marker
                            if data_str == "[DONE]":
                                return

                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse SSE data: {data_str}")
                                continue

        except httpx.HTTPError as e:
            logger.error(f"Cerebras streaming error: {e}")
            # Fallback to non-streaming
            response = await self.generate(
                prompt, config, context, conversation_history
            )
            yield response.text

    async def complete(
        self, prompt: str, config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """
        Generate completion using Cerebras Completions API (non-chat).
        Uses /completions endpoint instead of /chat/completions.

        Args:
            prompt: Text prompt to complete
            config: Optional generation configuration

        Returns:
            LLMResponse with completed text
        """
        if not self.api_key:
            raise Exception("Cerebras API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build request payload for completions endpoint
        payload = {
            "prompt": prompt,
            "model": model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
        }

        # Add optional parameters if provided
        if config.frequency_penalty is not None:
            payload["frequency_penalty"] = config.frequency_penalty
        if config.presence_penalty is not None:
            payload["presence_penalty"] = config.presence_penalty

        # Add stop sequences if provided
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        url = f"{self.API_BASE}/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Extract text from completions response
                text = ""
                choices = data.get("choices", [])
                if choices:
                    text = choices[0].get("text", "")

                # Get usage metadata
                usage = data.get("usage", {})

                # Get finish reason
                finish_reason = None
                if choices:
                    finish_reason = choices[0].get("finish_reason")

                # Extract time_info if available (Cerebras-specific)
                raw_response = data.copy()
                time_info = data.get("time_info")
                extra_metadata = {}
                if time_info:
                    extra_metadata["cerebras_timing"] = time_info
                    logger.debug(f"Cerebras timing: {time_info}")

                # Store enhanced response with time_info
                enhanced_response = (
                    {"data": raw_response, "time_info": time_info}
                    if time_info
                    else raw_response
                )

                return LLMResponse(
                    text=text,
                    model=model,
                    provider=self.provider_name,
                    usage={
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    finish_reason=finish_reason,
                    raw_response=enhanced_response,
                )

        except httpx.HTTPError as e:
            logger.error(f"Cerebras completions API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Cerebras API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Cerebras API error: {str(e)}")

    async def get_model_details(self, model_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific Cerebras model.

        Args:
            model_id: The model identifier (e.g., "llama3.1-8b")

        Returns:
            Dictionary with model details: id, object, created, owned_by
        """
        if not self.api_key:
            raise Exception("Cerebras API key not configured")

        try:
            url = f"{self.API_BASE}/models/{model_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get Cerebras model details: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Cerebras API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Failed to get model details: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Cerebras API is available"""
        if not self.api_key:
            return False

        try:
            # Try a simple chat completion request with minimal tokens
            url = f"{self.API_BASE}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.default_model,
                "messages": [{"role": "user", "content": "test"}],
                "max_completion_tokens": 1,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Cerebras health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """
        List available Cerebras model IDs (BaseLLMProvider contract).
        """
        return await self._list_model_ids()

    async def list_models_with_metadata(self) -> List[Dict[str, Any]]:
        """Return full model metadata dicts from the Cerebras API."""
        if not self.api_key:
            return []

        try:
            url = f"{self.API_BASE}/models"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                if isinstance(data, dict) and "data" in data:
                    raw = data["data"]
                    if isinstance(raw, list):
                        return [x for x in raw if isinstance(x, dict)]
                return []
        except Exception as e:
            logger.warning(f"Failed to fetch Cerebras models (metadata): {e}")
            return []

    async def _list_model_ids(self) -> List[str]:
        """Internal: model id strings only."""
        if not self.api_key:
            return []

        try:
            url = f"{self.API_BASE}/models"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                if isinstance(data, dict) and "data" in data:
                    models: List[str] = []
                    for model_info in data["data"]:
                        if isinstance(model_info, dict) and "id" in model_info:
                            models.append(str(model_info["id"]))
                    return models if models else self._get_default_models()
                return self._get_default_models()
        except Exception as e:
            logger.warning(f"Failed to fetch Cerebras models: {e}")
            return self._get_default_models()

    def _get_default_models(self) -> List[str]:
        """
        Return default list of Cerebras models.

        Active models:
        - llama3.1-8b
        - llama-3.3-70b
        - gpt-oss-120b
        - qwen-3-32b
        - qwen-3-235b-a22b-instruct-2507
        - zai-glm-4.6

        Deprecated models (not included):
        - deepseek-r1-distill-llama-70b
        - llama-4-scout-17b-16e-instruct
        - llama-4-maverick-17b-128e-instruct
        - qwen-3-235b-a22b-thinking-2507
        - qwen-3-coder-480b
        """
        return [
            "llama3.1-8b",
            "llama-3.3-70b",
            "gpt-oss-120b",
            "qwen-3-32b",
            "qwen-3-235b-a22b-instruct-2507",
            "zai-glm-4.6",
        ]
