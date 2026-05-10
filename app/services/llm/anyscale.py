"""
Anyscale LLM Provider
Ray-based inference platform
"""

import json
import logging
from typing import AsyncIterator, Dict, List, Optional, Any

import httpx

from app.config import settings
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class AnyscaleProvider(BaseLLMProvider):
    """
    Anyscale provider using OpenAI-compatible API.
    Enterprise-grade Ray-based inference platform.
    """

    provider_name = "anyscale"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
    ):
        """Initialize Anyscale provider"""
        self.api_key = api_key or getattr(settings, "anyscale_api_key", None)
        self.default_model = model or getattr(
            settings, "anyscale_model", "meta-llama/Llama-3-70b-chat-hf"
        )
        self.timeout = timeout
        self.base_url = base_url or getattr(
            settings, "anyscale_base_url", "https://api.endpoints.anyscale.com/v1"
        )

        if not self.api_key:
            logger.warning("Anyscale API key not configured")

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Generate a response using Anyscale API"""
        if not self.api_key:
            raise Exception("Anyscale API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        payload = {
            "messages": messages,
            "model": model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                text = ""
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    text = message.get("content", "")

                usage = data.get("usage", {})

                return LLMResponse(
                    text=text,
                    model=model,
                    provider=self.provider_name,
                    usage={
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    finish_reason=choices[0].get("finish_reason") if choices else None,
                    raw_response=data,
                )

        except httpx.HTTPError as e:
            logger.error(f"Anyscale API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Anyscale API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Anyscale API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response using Anyscale API"""
        if not self.api_key:
            raise Exception("Anyscale API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        payload = {
            "messages": messages,
            "model": model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True,
        }

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        url = f"{self.base_url}/chat/completions"
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
                        lines = buffer.split("\n")
                        buffer = lines[-1]

                        for line in lines[:-1]:
                            line = line.strip()
                            if not line or not line.startswith("data: "):
                                continue

                            data_str = line[6:]
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
                                continue

        except httpx.HTTPError as e:
            logger.error(f"Anyscale streaming error: {e}")
            response = await self.generate(
                prompt, config, context, conversation_history
            )
            yield response.text

    async def health_check(self) -> bool:
        """Check if Anyscale API is available"""
        if not self.api_key:
            return False

        try:
            url = f"{self.base_url}/chat/completions"
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
            logger.warning(f"Anyscale health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available Anyscale models"""
        return [
            "meta-llama/Llama-2-70b-chat-hf",
            "meta-llama/Llama-3-70b-chat-hf",
            "mistralai/Mixtral-8x7b-Instruct-v0.1",
        ]
