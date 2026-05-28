"""
Cohere LLM Provider
Enterprise-grade LLM with RAG connectors
"""

import json
import logging
from typing import AsyncIterator, List, Optional, Dict, Any

import httpx

from app.config import settings
from app.utils.helpers import is_usable_api_key
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class CohereProvider(BaseLLMProvider):
    """
    Cohere provider with RAG connectors support.
    Supports web search and custom connectors for enhanced responses.
    """

    provider_name = "cohere"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Cohere provider.

        Args:
            api_key: Cohere API key
            model: Default model to use
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.api_key = api_key or settings.cohere_api_key
        self.default_model = model or settings.cohere_model
        self.timeout = timeout
        self.base_url = base_url or settings.cohere_base_url

        if not self.api_key:
            logger.warning("Cohere API key not configured")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=self.timeout,
        )

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Generate chat completion with optional RAG connectors.

        Args:
            prompt: User message
            config: Generation configuration
            context: Optional context to include
            conversation_history: Previous conversation messages

        Returns:
            LLMResponse with generated text and metadata
        """
        if config is None:
            config = LLMConfig()

        # Build chat history in Cohere format
        history = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                # Convert to Cohere format: USER or CHATBOT
                if role in ["user", "USER"]:
                    cohere_role = "USER"
                elif role in ["assistant", "CHATBOT"]:
                    cohere_role = "CHATBOT"
                else:
                    cohere_role = "USER"

                content = msg.get("content", "")
                if content:
                    history.append({"role": cohere_role, "message": content})

        # Build request payload
        payload: dict[str, Any] = {
            "model": config.model or self.default_model,
            "message": prompt,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        if history:
            payload["chat_history"] = history

        # Handle context and connectors
        if context:
            # If context provided, add it to preamble
            payload["preamble"] = (
                f"Context: {context}\n\nUse the above context to answer."
            )
        else:
            # Enable web search by default for RAG
            payload["connectors"] = [{"id": "web-search"}]

        try:
            response = await self.client.post("/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract usage information
            meta = data.get("meta", {})
            billed_units = meta.get("billed_units", {})
            tokens = meta.get("tokens", {})

            # Build usage dict
            usage = {
                "prompt_tokens": billed_units.get(
                    "input_tokens", tokens.get("input_tokens", 0)
                ),
                "completion_tokens": billed_units.get(
                    "output_tokens", tokens.get("output_tokens", 0)
                ),
                "total_tokens": tokens.get("input_tokens", 0)
                + tokens.get("output_tokens", 0),
            }

            return LLMResponse(
                text=data.get("text", ""),
                provider="cohere",
                model=config.model or self.default_model,
                usage=usage,
                finish_reason=data.get("finish_reason"),
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Cohere API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Cohere generation error: {e}")
            raise

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat completion.

        Args:
            prompt: User message
            config: Generation configuration
            context: Optional context to include
            conversation_history: Previous conversation messages

        Yields:
            Text chunks as they are generated
        """
        if config is None:
            config = LLMConfig()

        # Build chat history in Cohere format
        history = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                if role in ["user", "USER"]:
                    cohere_role = "USER"
                elif role in ["assistant", "CHATBOT"]:
                    cohere_role = "CHATBOT"
                else:
                    cohere_role = "USER"

                content = msg.get("content", "")
                if content:
                    history.append({"role": cohere_role, "message": content})

        # Build request payload
        payload: dict[str, Any] = {
            "model": config.model or self.default_model,
            "message": prompt,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": True,
        }

        if history:
            payload["chat_history"] = history

        if context:
            payload["preamble"] = f"Context: {context}"
        else:
            payload["connectors"] = [{"id": "web-search"}]

        try:
            async with self.client.stream("POST", "/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        # Cohere streaming format: parse JSON lines
                        try:
                            if line.startswith("data: "):
                                line = line[6:]  # Remove "data: " prefix
                            if line.strip() == "[DONE]":
                                break
                            data = json.loads(line)
                            if "text" in data:
                                yield data["text"]
                        except json.JSONDecodeError:
                            # If not JSON, yield as-is
                            if line.strip():
                                yield line
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Cohere streaming error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Cohere streaming error: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if Cohere API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        if not is_usable_api_key(self.api_key):
            return False

        try:
            response = await self.client.get("/models")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Cohere health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """
        List available Cohere models.

        Returns:
            List of model names
        """
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            return [model.get("name", "") for model in models if model.get("name")]
        except Exception as e:
            logger.error(f"Error listing Cohere models: {e}")
            return []

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
