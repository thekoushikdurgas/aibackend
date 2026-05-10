"""
NVIDIA Chat Completions Service
Enhanced chat service with support for all NVIDIA models, reasoning, and function calling
"""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from app.config import settings
from app.services.llm.base import BaseLLMProvider, LLMConfig, LLMResponse
from .client import NVIDIAClient, BaseURLType
from .models import get_model, get_chat_models, validate_model

logger = logging.getLogger(__name__)


class NVIDIAChatService(BaseLLMProvider):
    """
    NVIDIA AI chat completions service.

    Supports:
    - All 50+ chat models from NVIDIA API
    - Streaming and non-streaming generation
    - Reasoning models (DeepSeek-R1, etc.)
    - Function calling
    - Extended context windows
    """

    provider_name = "nvidia"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        base_url: Optional[str] = None,
        genai_base_url: Optional[str] = None,
    ):
        """
        Initialize NVIDIA chat service.

        Args:
            api_key: NVIDIA API key
            model: Default model to use
            timeout: Request timeout in seconds
            base_url: Optional custom base URL for integrate API
            genai_base_url: Optional custom base URL for GenAI API
        """
        self.client = NVIDIAClient(
            api_key=api_key,
            base_url=base_url,
            genai_base_url=genai_base_url,
            timeout=timeout or settings.nvidia_chat_timeout,
        )
        self.default_model = model or settings.nvidia_chat_model

        if not self.client.api_key:
            logger.warning("NVIDIA API key not configured")

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMResponse:
        """
        Generate a chat completion using NVIDIA AI API.

        Args:
            prompt: User prompt
            config: LLM configuration
            context: Additional context
            conversation_history: Previous conversation messages

        Returns:
            LLMResponse with generated text and metadata
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Validate model
        if not validate_model(model):
            logger.warning(f"Model {model} not in registry, proceeding anyway")

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload (OpenAI-compatible format)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }

        # Add optional parameters
        if config.top_k:
            payload["top_k"] = config.top_k

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        # Add function calling if tools are provided
        if hasattr(config, "tools") and config.tools:
            payload["tools"] = config.tools
            if hasattr(config, "tool_choice") and config.tool_choice:
                payload["tool_choice"] = config.tool_choice

        # Determine base URL type from model
        model_metadata = get_model(model)
        url_type = (
            BaseURLType.GENAI
            if (model_metadata and model_metadata.base_url_type == "genai")
            else BaseURLType.INTEGRATE
        )

        try:
            response = await self.client.post(
                "chat/completions", url_type=url_type, model_id=model, json=payload
            )

            data = response.json()

            # Extract text from OpenAI-compatible response
            text = ""

            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                text = message.get("content", "")
                message.get("reasoning_content", "")
                message.get("tool_calls", [])

            # Get usage metadata
            usage_data = data.get("usage", {})

            # Build raw response with NVIDIA-specific headers
            raw_response = data.copy()
            nvidia_headers = self.client._extract_nvidia_headers(response)
            raw_response.update(nvidia_headers)

            return LLMResponse(
                text=text,
                model=model,
                provider=self.provider_name,
                usage={
                    "prompt_tokens": usage_data.get("prompt_tokens", 0),
                    "completion_tokens": usage_data.get("completion_tokens", 0),
                    "total_tokens": usage_data.get("total_tokens", 0),
                },
                finish_reason=choices[0].get("finish_reason") if choices else None,
                raw_response=raw_response,
            )

        except Exception as e:
            logger.error(f"NVIDIA chat generation error: {e}")
            raise

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion using NVIDIA AI API.

        Args:
            prompt: User prompt
            config: LLM configuration
            context: Additional context
            conversation_history: Previous conversation messages

        Yields:
            Text chunks as they are generated
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Validate model
        if not validate_model(model):
            logger.warning(f"Model {model} not in registry, proceeding anyway")

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
        }

        if config.top_k:
            payload["top_k"] = config.top_k

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        # Determine base URL type from model
        model_metadata = get_model(model)
        url_type = (
            BaseURLType.GENAI
            if (model_metadata and model_metadata.base_url_type == "genai")
            else BaseURLType.INTEGRATE
        )

        try:
            async with self.client.stream(
                "chat/completions", url_type=url_type, model_id=model, json=payload
            ) as http_resp:
                http_resp.raise_for_status()

                async for line in http_resp.aiter_lines():
                    if not line.strip():
                        continue

                    # Handle SSE format: "data: {...}"
                    if line.startswith("data: "):
                        line = line[6:]  # Remove "data: " prefix

                    if line.strip() == "[DONE]":
                        break

                    # Try to parse JSON
                    try:
                        data = json.loads(line)

                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        # Continue to next line
                        continue

        except Exception as e:
            logger.error(f"NVIDIA streaming error: {e}")
            # Fallback to non-streaming
            llm_resp = await self.generate(
                prompt, config, context, conversation_history
            )
            yield llm_resp.text

    async def health_check(self) -> bool:
        """Check if NVIDIA chat API is available"""
        return await self.client.health_check(BaseURLType.INTEGRATE)

    async def list_models(self) -> List[str]:
        """List all available chat models"""
        return get_chat_models()

    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.

        Args:
            model_id: Model identifier

        Returns:
            Model metadata dictionary or None if not found
        """
        model = get_model(model_id)
        if not model:
            return None

        return {
            "id": model.id,
            "category": model.category.value,
            "provider": model.provider.value,
            "capabilities": list(model.capabilities),
            "context_length": model.context_length,
            "vision": model.vision,
            "reasoning": model.reasoning,
            "code": model.code,
            "description": model.description,
        }
