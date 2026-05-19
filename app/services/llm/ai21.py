"""
AI21 Labs LLM Provider
"""

import json
import logging
from typing import AsyncIterator, Dict, List, Optional, Any

import httpx

from app.config import settings
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class AI21Provider(BaseLLMProvider):
    """
    AI21 Labs provider using the Studio API.
    Supports both streaming and non-streaming generation via OpenAI-compatible chat completions.
    """

    provider_name = "ai21"

    # API endpoint
    API_BASE = "https://api.ai21.com/studio/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
    ):
        """
        Initialize AI21 provider.

        Args:
            api_key: AI21 API key
            model: Default model to use
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.api_key = api_key or settings.ai21_api_key
        self.default_model = model or settings.ai21_model
        self.timeout = timeout
        self.API_BASE = base_url or settings.ai21_base_url

        if not self.api_key:
            logger.warning("AI21 API key not configured")

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build messages array for AI21 chat completions API.
        AI21 uses OpenAI-compatible format with system/user/assistant roles.
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
        """Generate a response using AI21 Labs API"""
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload (OpenAI-compatible format)
        payload: dict[str, Any] = {
            "messages": messages,
            "model": model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }

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
                    raw_response=data,
                )

        except httpx.HTTPError as e:
            logger.error(f"AI21 API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response using AI21 Labs API"""
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload with streaming enabled
        payload: dict[str, Any] = {
            "messages": messages,
            "model": model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True,
        }

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
                ) as http_resp:
                    http_resp.raise_for_status()

                    buffer = ""
                    async for chunk in http_resp.aiter_text():
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
            logger.error(f"AI21 streaming error: {e}")
            # Fallback to non-streaming
            llm_resp = await self.generate(
                prompt, config, context, conversation_history
            )
            yield llm_resp.text

    async def health_check(self) -> bool:
        """Check if AI21 API is available"""
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
                "messages": [{"role": "user", "content": "test"}],
                "model": self.default_model,
                "max_tokens": 1,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"AI21 health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available AI21 models"""
        return ["jamba-large-1.7", "jamba-mini-1.7"]
