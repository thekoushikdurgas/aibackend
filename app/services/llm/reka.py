"""
Reka AI LLM Provider
"""

import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.services.reka.model_registry import RekaModelRegistry
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class RekaProvider(BaseLLMProvider):
    """
    Reka AI provider using Reka AI Chat API.
    Supports reka-core, reka-flash, reka-flash-3, and reka-edge models.
    """

    provider_name = "reka"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Reka provider.

        Args:
            api_key: Reka AI API key
            model: Default model to use
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.api_key = api_key or settings.reka_api_key
        self.default_model = model or settings.reka_model
        self.timeout = timeout
        self.base_url = base_url or settings.reka_base_url
        self.model_registry = RekaModelRegistry(api_key=api_key, base_url=base_url)

        if not self.api_key:
            logger.warning("Reka AI API key not configured")

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        return headers

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build messages array for Reka AI chat API.
        """
        messages = []

        # Add system message if provided
        if system_prompt:
            messages.append({"role": "user", "content": system_prompt})
        elif not conversation_history:
            # Only add default system prompt if no conversation history
            messages.append(
                {
                    "role": "user",
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
            if messages:
                messages[-1]["content"] = context_message + messages[-1]["content"]
            else:
                messages.append({"role": "user", "content": context_message})

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                # Reka uses "user" and "assistant" roles
                if role not in ["user", "assistant"]:
                    role = "user"

                content = msg.get("content", "")
                messages.append({"role": role, "content": content})

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        return messages

    def _extract_reasoning(self, content: str) -> Tuple[str, Optional[str]]:
        """
        Extract reasoning from reka-flash-3 responses.
        Returns (clean_content, reasoning) tuple.
        """
        # Check for reasoning tags
        reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", content, re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()
            # Remove reasoning tags from content
            clean_content = re.sub(
                r"<reasoning>.*?</reasoning>", "", content, flags=re.DOTALL
            ).strip()
            return clean_content, reasoning
        return content, None

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Generate a response using Reka AI API.
        """
        if not self.api_key:
            raise Exception("Reka AI API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload
        payload = {"messages": messages, "model": model, "stream": False}

        # Add optional parameters if supported
        if config.temperature is not None:
            payload["temperature"] = config.temperature
        if config.max_tokens is not None:
            payload["max_tokens"] = config.max_tokens
        if config.top_p is not None:
            payload["top_p"] = config.top_p
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        url = f"{self.base_url}/chat"
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Parse Reka AI response format
                # Response structure: {id, model, usage: {input_tokens, output_tokens}, responses: [{message: {role, content}}]}
                text = ""
                finish_reason = None

                if "responses" in data and data["responses"]:
                    response_obj = data["responses"][0]
                    if "message" in response_obj:
                        text = response_obj["message"].get("content", "")
                    elif "content" in response_obj:
                        text = response_obj["content"]

                    finish_reason = response_obj.get("finish_reason")

                # Extract reasoning if present (for reka-flash-3)
                clean_text, reasoning = self._extract_reasoning(text)

                # Get usage metadata
                usage_data = data.get("usage", {})
                usage = {
                    "input_tokens": usage_data.get("input_tokens", 0),
                    "output_tokens": usage_data.get("output_tokens", 0),
                    "total_tokens": usage_data.get("input_tokens", 0)
                    + usage_data.get("output_tokens", 0),
                }

                # Store reasoning in raw_response if present
                raw_response = data.copy()
                if reasoning:
                    raw_response["_reasoning"] = reasoning

                return LLMResponse(
                    text=clean_text,
                    model=data.get("model", model),
                    provider=self.provider_name,
                    usage=usage,
                    finish_reason=finish_reason,
                    raw_response=raw_response,
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Reka AI API error: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Reka AI API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Reka AI request error: {e}")
            raise

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a response from Reka AI.
        """
        if not self.api_key:
            raise Exception("Reka AI API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload
        payload = {"messages": messages, "model": model, "stream": True}

        # Add optional parameters
        if config.temperature is not None:
            payload["temperature"] = config.temperature
        if config.max_tokens is not None:
            payload["max_tokens"] = config.max_tokens

        url = f"{self.base_url}/chat"
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", url, json=payload, headers=headers
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            # Parse SSE format if applicable
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    import json

                                    chunk = json.loads(data_str)
                                    # Extract content from response
                                    if "responses" in chunk and chunk["responses"]:
                                        content = (
                                            chunk["responses"][0]
                                            .get("message", {})
                                            .get("content", "")
                                        )
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                            else:
                                yield line
        except Exception as e:
            logger.error(f"Reka AI stream error: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if the provider is available and healthy.
        """
        try:
            models = await self.model_registry.fetch_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"Reka AI health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """
        List available models for this provider.
        """
        try:
            models = await self.model_registry.fetch_models()
            return [model.get("id", "") for model in models if model.get("id")]
        except Exception as e:
            logger.error(f"Failed to list Reka AI models: {e}")
            # Return default models
            return ["reka-core", "reka-flash-3", "reka-flash", "reka-edge"]
