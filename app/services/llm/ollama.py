"""
Ollama LLM Provider
Enhanced with cloud mode support using new OllamaClient
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.config import settings
from .base import BaseLLMProvider, LLMConfig, LLMResponse
from app.services.ollama import OllamaClient, resolve_ollama_mode

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama provider for local and cloud LLM inference.
    Supports streaming and non-streaming generation.
    Enhanced with cloud mode support via OllamaClient.
    """

    provider_name = "ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        cloud_url: Optional[str] = None,
        api_key: Optional[str] = None,
        mode: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama API base URL (localhost mode)
            cloud_url: Ollama Cloud API URL
            api_key: API key for cloud mode
            mode: Deployment mode ("localhost" or "cloud")
            model: Default model to use
            timeout: Request timeout in seconds
        """
        # Use new OllamaClient for cloud support
        self.client = OllamaClient(
            base_url=base_url,
            cloud_url=cloud_url,
            api_key=api_key,
            mode=resolve_ollama_mode(mode) if mode else None,
            timeout=timeout,
        )

        # Keep backward compatibility
        self.base_url = self.client.get_base_url()
        self.default_model = model or str(
            getattr(settings, "ollama_model", None) or "llama3"
        )
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Generate a response using Ollama API"""
        config = config or LLMConfig(model=self.default_model)

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload
        payload: Dict[str, Any] = {
            "model": config.model or self.default_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
            },
        }

        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        try:
            chat_timeout = httpx.Timeout(
                connect=30.0,
                read=float(settings.ollama_completion_timeout_seconds),
                write=120.0,
                pool=30.0,
            )
            # Use new client for cloud/localhost support
            response = await self.client.post(
                "chat", json=payload, timeout=chat_timeout
            )
            data = response.json()

            return LLMResponse(
                text=data.get("message", {}).get("content", ""),
                model=config.model or self.default_model,
                provider=self.provider_name,
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0)
                    + data.get("eval_count", 0),
                },
                finish_reason=data.get("done_reason"),
                raw_response=data,
            )

        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise Exception(f"Ollama API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response using Ollama API"""
        config = config or LLMConfig(model=self.default_model)

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload
        payload: Dict[str, Any] = {
            "model": config.model or self.default_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
            },
        }

        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        try:
            stream_timeout = httpx.Timeout(
                connect=30.0,
                read=float(settings.ollama_completion_timeout_seconds),
                write=120.0,
                pool=30.0,
            )
            # Use new client for cloud/localhost support
            async with self.client.stream(
                "chat", json=payload, timeout=stream_timeout
            ) as stream:
                async for line in stream.aiter_lines():
                    if line:
                        import json

                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content

                            # Check if done
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise Exception(f"Ollama streaming error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Ollama is available"""
        return await self.client.health_check()

    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            response = await self.client.get("tags")
            data = response.json()

            models = []
            for model in data.get("models", []):
                models.append(model.get("name", ""))
            return models

        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama library"""
        try:
            payload = {"model": model_name}
            response = await self.client.post("pull", json=payload, timeout=600.0)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
