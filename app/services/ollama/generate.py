"""
Ollama Generation Service
Core generation logic for text completion and chat
"""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from app.config import settings
from app.services.llm.base import BaseLLMProvider, LLMConfig, LLMResponse
from .client import OllamaClient, OllamaMode
from .models import get_model, validate_model

logger = logging.getLogger(__name__)


class OllamaGenerateService(BaseLLMProvider):
    """
    Ollama generation service for text completion and chat.

    Supports:
    - Non-streaming and streaming generation
    - Raw mode generation
    - Chat completions with messages
    - OpenAI-compatible response format
    """

    provider_name = "ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        cloud_url: Optional[str] = None,
        api_key: Optional[str] = None,
        mode: Optional[OllamaMode] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        Initialize Ollama generation service.

        Args:
            base_url: Base URL for localhost mode
            cloud_url: Base URL for cloud mode
            api_key: API key for cloud mode
            mode: Deployment mode (localhost or cloud)
            model: Default model to use
            timeout: Request timeout in seconds
        """
        self.client = OllamaClient(
            base_url=base_url,
            cloud_url=cloud_url,
            api_key=api_key,
            mode=mode,
            timeout=timeout or 120.0,
        )
        self.default_model = model or str(
            getattr(settings, "ollama_model", None) or "llama3"
        )

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMResponse:
        """
        Generate a response using Ollama API.

        Args:
            prompt: User prompt
            config: LLM configuration
            context: Additional context
            conversation_history: Previous conversation messages

        Returns:
            LLMResponse with generated text and metadata
        """
        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Validate model if in registry
        if validate_model(model):
            model_info = get_model(model)
            if model_info:
                # Check if model is compatible with current mode
                if model_info.cloud_only and self.client.mode != OllamaMode.CLOUD:
                    raise ValueError(f"Model {model} is only available in cloud mode")
                if (
                    model_info.localhost_only
                    and self.client.mode != OllamaMode.LOCALHOST
                ):
                    raise ValueError(
                        f"Model {model} is only available in localhost mode"
                    )

        # Build messages for chat endpoint
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Use chat endpoint if we have messages, otherwise use generate
        use_chat = len(messages) > 1 or conversation_history

        if use_chat:
            return await self._generate_chat(messages, model, config)
        else:
            return await self._generate_completion(prompt, model, config)

    async def _generate_chat(
        self, messages: List[Dict[str, str]], model: str, config: LLMConfig
    ) -> LLMResponse:
        """Generate using chat endpoint"""
        payload: Dict[str, Any] = {
            "model": model,
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
            response = await self.client.post("chat", json=payload)
            data = response.json()

            return LLMResponse(
                text=data.get("message", {}).get("content", ""),
                model=model,
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
            logger.error(f"Ollama chat generation error: {e}")
            raise

    async def _generate_completion(
        self, prompt: str, model: str, config: LLMConfig
    ) -> LLMResponse:
        """Generate using generate endpoint (raw mode)"""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "raw": False,
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
            response = await self.client.post("generate", json=payload)
            data = response.json()

            return LLMResponse(
                text=data.get("response", ""),
                model=model,
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
            logger.error(f"Ollama completion generation error: {e}")
            raise

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a response using Ollama API.

        Args:
            prompt: User prompt
            config: LLM configuration
            context: Additional context
            conversation_history: Previous conversation messages

        Yields:
            Text chunks as they are generated
        """
        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Use chat endpoint if we have messages, otherwise use generate
        use_chat = len(messages) > 1 or conversation_history

        if use_chat:
            async for chunk in self._stream_chat(messages, model, config):
                yield chunk
        else:
            async for chunk in self._stream_completion(prompt, model, config):
                yield chunk

    async def _stream_chat(
        self, messages: List[Dict[str, str]], model: str, config: LLMConfig
    ) -> AsyncIterator[str]:
        """Stream using chat endpoint"""
        payload: Dict[str, Any] = {
            "model": model,
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
            async with self.client.stream("chat", json=payload) as stream:
                async for line in stream.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content

                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Ollama chat streaming error: {e}")
            raise

    async def _stream_completion(
        self, prompt: str, model: str, config: LLMConfig
    ) -> AsyncIterator[str]:
        """Stream using generate endpoint"""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "raw": False,
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
            async with self.client.stream("generate", json=payload) as stream:
                async for line in stream.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("response", "")
                            if content:
                                yield content

                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Ollama completion streaming error: {e}")
            raise

    async def generate_raw(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate using raw mode (no prompt formatting).

        Args:
            prompt: Raw prompt text
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Raw response dictionary
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "raw": True,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            response = await self.client.post("generate", json=payload)
            return response.json()
        except Exception as e:
            logger.error(f"Ollama raw generation error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Ollama service is available"""
        return await self.client.health_check()

    async def list_models(self) -> List[str]:
        """List model names from the Ollama API (BaseLLMProvider contract)."""
        try:
            response = await self.client.get("tags")
            data = response.json()
            names: List[str] = []
            for m in data.get("models", []) or []:
                if isinstance(m, dict):
                    n = m.get("name", "")
                    if n:
                        names.append(str(n))
            return names
        except Exception as e:
            logger.error(f"Ollama list_models error: {e}")
            raise

    def _normalize_chat_messages(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for m in messages:
            out.append(
                {
                    "role": str(m.get("role", "user")),
                    "content": str(m.get("content", "")),
                }
            )
        return out

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Chat completion using the Ollama chat API (OpenAI-style message list)."""
        if not messages:
            raise ValueError("messages is required")
        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model
        normalized = self._normalize_chat_messages(messages)
        return await self._generate_chat(normalized, model, config)

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion using the Ollama chat API."""
        if not messages:
            raise ValueError("messages is required")
        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model
        normalized = self._normalize_chat_messages(messages)
        async for chunk in self._stream_chat(normalized, model, config):
            yield chunk
