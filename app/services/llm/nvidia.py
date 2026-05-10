"""
NVIDIA AI LLM Provider
Supports OpenAI-compatible API for NVIDIA's chat completion models
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.config import settings
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class NVIDIAProvider(BaseLLMProvider):
    """
    NVIDIA AI provider using OpenAI-compatible API.
    Supports streaming and non-streaming generation with various NVIDIA models.
    """

    provider_name = "nvidia"

    # API endpoint
    API_BASE = "https://integrate.api.nvidia.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
    ):
        """
        Initialize NVIDIA provider.

        Args:
            api_key: NVIDIA API key
            model: Default model to use
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.api_key = api_key or settings.nvidia_api_key
        self.default_model = model or settings.nvidia_model
        self.timeout = timeout
        self.API_BASE = base_url or settings.nvidia_base_url

        if not self.api_key:
            logger.warning("NVIDIA API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Generate a response using NVIDIA AI API"""
        if not self.api_key:
            raise Exception("NVIDIA API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

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

        # Add top_k if supported
        if config.top_k:
            payload["top_k"] = config.top_k

        # Add stop sequences
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        url = f"{self.API_BASE}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                # Extract text from OpenAI-compatible response
                text = ""
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    text = message.get("content", "")
                    # Some models return reasoning_content
                    message.get("reasoning_content", "")

                # Get usage metadata
                usage_data = data.get("usage", {})

                # Build raw response with NVIDIA-specific headers if available
                raw_response = data.copy()
                if hasattr(response, "headers"):
                    nvcf_reqid = response.headers.get("Nvcf-Reqid")
                    nvcf_status = response.headers.get("Nvcf-Status")
                    if nvcf_reqid:
                        raw_response["nvcf_reqid"] = nvcf_reqid
                    if nvcf_status:
                        raw_response["nvcf_status"] = nvcf_status

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

        except httpx.HTTPError as e:
            logger.error(f"NVIDIA API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                except (ValueError, AttributeError, KeyError):
                    error_msg = str(e)
            else:
                error_msg = str(e)
            raise Exception(f"NVIDIA API error: {error_msg}")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response using NVIDIA AI API"""
        if not self.api_key:
            raise Exception("NVIDIA API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

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

        url = f"{self.API_BASE}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", url, json=payload, headers=self._get_headers()
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        # Handle SSE format: "data: {...}"
                        if line.startswith("data: "):
                            line = line[6:]  # Remove "data: " prefix

                        if line.strip() == "[DONE]":
                            break

                        # Try to parse JSON
                        try:
                            import json

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

        except httpx.HTTPError as e:
            logger.error(f"NVIDIA streaming error: {e}")
            # Fallback to non-streaming
            response = await self.generate(
                prompt, config, context, conversation_history
            )
            yield response.text

    async def health_check(self) -> bool:
        """Check if NVIDIA API is available"""
        if not self.api_key:
            return False

        try:
            # Try a simple request with minimal tokens
            test_config = LLMConfig(
                model=self.default_model, max_tokens=1, temperature=0
            )
            test_response = await self.generate(prompt="test", config=test_config)
            return bool(test_response.text)
        except Exception as e:
            logger.warning(f"NVIDIA health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available NVIDIA models"""
        return [
            # NVIDIA Models
            "nvidia/nemotron-4-340b-instruct",
            "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            "nvidia/llama-3.3-nemotron-super-49b-v1",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nv-mistralai/mistral-nemo-12b-instruct",
            # Meta Models
            "meta/llama2-70b",
            "meta/llama3-8b",
            "meta/llama3-8b-instruct",
            "meta/llama3-70b",
            "meta/llama3-70b-instruct",
            "meta/llama-3.1-405b-instruct",
            "meta/llama-3.2-1b-instruct",
            "meta/llama-3.2-3b-instruct",
            "meta/llama-3.2-11b-vision-instruct",
            "meta/llama-3.2-90b-vision-instruct",
            "meta/llama-3.3-70b-instruct",
            "meta/llama-4-scout-17b-16e-instruct",
            "meta/llama-4-maverick-17b-128e-instruct",
            "meta/codellama-70b",
            # Google Models
            "google/gemma-2b",
            "google/gemma-7b",
            "google/gemma-2-9b-it",
            "google/gemma-3-27b-it",
            "google/codegemma-7b",
            # Microsoft Models
            "microsoft/phi-3-mini-128k-instruct",
            "microsoft/phi-3.5-moe-instruct",
            "microsoft/phi-4-multimodal-instruct",
            # Mistral Models
            "mistralai/mistral-7b-instruct-v0.2",
            "mistralai/mistral-large",
            "mistralai/mixtral-8x22b-instruct-v0.1",
            # DeepSeek Models
            "deepseek-ai/deepseek-r1",
            # OpenAI Models
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            # Qwen Models
            "qwen/qwen3-235b-a22b",
            # Snowflake Models
            "snowflake/arctic",
            # Moonshot Models
            "moonshotai/kimi-k2-instruct",
        ]
