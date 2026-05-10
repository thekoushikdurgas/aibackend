"""
Hugging Face LLM Provider
Modern implementation using OpenAI-compatible Chat Completions API
"""

import json
import logging
from typing import AsyncIterator, Dict, List, Optional, Any

import httpx

from app.config import settings
from .base import BaseLLMProvider, LLMConfig, LLMResponse
from .hf_client import HuggingFaceClient, HFInferenceProvider

logger = logging.getLogger(__name__)


class HuggingFaceProvider(BaseLLMProvider):
    """
    Hugging Face provider using the modern Chat Completions API.
    Supports multiple inference providers via HF Router.
    """

    provider_name = "huggingface"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Hugging Face provider.

        Args:
            api_key: Hugging Face API key
            model: Default model to use
            provider: Inference provider (hf, cerebras, groq, etc.)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.huggingface_api_key
        self.default_model = model or settings.huggingface_model
        self.provider = provider or settings.huggingface_inference_provider
        self.timeout = timeout

        # Initialize client
        self.client = HuggingFaceClient(api_key=self.api_key, timeout=self.timeout)

        if not self.api_key:
            logger.warning("HuggingFace API key not configured")

    def _convert_provider(self, provider: Optional[str] = None) -> HFInferenceProvider:
        """Convert provider string to enum"""
        provider = provider or self.provider
        try:
            return HFInferenceProvider(provider.lower())
        except ValueError:
            logger.warning(f"Unknown provider {provider}, using 'hf'")
            return HFInferenceProvider.HF

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build message list for chat API.

        Args:
            prompt: Current user prompt
            context: Optional context to include
            conversation_history: Previous conversation messages
            system_prompt: Optional system prompt

        Returns:
            List of message dictionaries
        """
        messages = []

        # Build system message
        system_content = system_prompt or (
            "You are DurgasAI, a helpful AI assistant specialized in "
            "web page analysis, content extraction, and SEO optimization."
        )

        if context:
            system_content += f"\n\nContext:\n{context}"

        messages.append({"role": "system", "content": system_content})

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant", "system"]:
                    messages.append({"role": role, "content": content})

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
        """
        Generate a response using HuggingFace Chat Completions API.

        Args:
            prompt: The user's input prompt
            config: Generation configuration
            context: Optional context to include
            conversation_history: Previous messages in the conversation

        Returns:
            LLMResponse with the generated text
        """
        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Get provider
        provider = self._convert_provider()

        try:
            # Call chat completions API
            response = await self.client.chat_completions(
                messages=messages,
                model=model,
                provider=provider,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                stream=False,
            )

            # Parse response
            if isinstance(response, dict):
                # Extract text from response
                choices = response.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    text = message.get("content", "")
                else:
                    text = ""

                # Extract usage information
                usage = response.get("usage", {})
                usage_dict = None
                if usage:
                    usage_dict = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }

                # Extract finish reason
                finish_reason = None
                if choices:
                    finish_reason = choices[0].get("finish_reason")

                return LLMResponse(
                    text=text.strip(),
                    model=model,
                    provider=self.provider_name,
                    usage=usage_dict,
                    finish_reason=finish_reason,
                    raw_response=response,
                )
            else:
                raise Exception("Unexpected response format")

        except Exception as e:
            logger.error(f"HuggingFace API error: {e}")
            raise Exception(f"HuggingFace API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a response using HuggingFace Chat Completions API.

        Args:
            prompt: The user's input prompt
            config: Generation configuration
            context: Optional context to include
            conversation_history: Previous messages in the conversation

        Yields:
            Text chunks as they are generated
        """
        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Get provider
        provider = self._convert_provider()

        try:
            # Call streaming chat completions API
            response = await self.client.chat_completions(
                messages=messages,
                model=model,
                provider=provider,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                stream=True,
            )

            # Handle streaming response
            if isinstance(response, httpx.Response):
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str.strip() == "[DONE]":
                                break

                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            logger.warning(f"Error parsing stream chunk: {e}")
                            continue
            else:
                # Fallback to non-streaming
                response_obj = await self.generate(
                    prompt, config, context, conversation_history
                )
                yield response_obj.text

        except Exception as e:
            logger.error(f"HuggingFace streaming error: {e}")
            # Fallback to non-streaming
            response_obj = await self.generate(
                prompt, config, context, conversation_history
            )
            yield response_obj.text

    async def health_check(self) -> bool:
        """Check if HuggingFace API is available"""
        if not self.api_key:
            return False

        try:
            # Try a simple whoami check
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://huggingface.co/api/whoami-v2",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"HuggingFace health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """
        List recommended models for text generation.
        Returns models organized by provider.
        Based on Postman collection endpoints.
        """
        models = {
            "hf": [
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
                "mistralai/Mistral-7B-Instruct-v0.2",
                "meta-llama/Llama-3.2-3B-Instruct",
                "Qwen/Qwen2.5-72B-Instruct",
            ],
            "cerebras": [
                "meta-llama/Llama-4-Scout-17B-16E-Instruct",
                "meta-llama/Llama-3.3-70B-Instruct",
                "gpt-oss-120b",
            ],
            "groq": [
                "moonshotai/kimi-k2-instruct",
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
            ],
            "fireworks": [
                "deepseek-r1",
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "qwen3-30b-a3b",
                "qwen3-235b-a22b",
            ],
            "together": [
                "deepseek-ai/DeepSeek-R1",
                "moonshotai/Kimi-K2-Instruct",
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
            ],
            "nebius": [
                "google/gemma-3-27b-it",
                "Qwen/Qwen3-Embedding-8B",
            ],
            "novita": [
                "deepseek/deepseek-prover-v2-671b",
                "meta-llama/llama-4-scout-17b-16e-instruct",
                "meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
                "moonshotai/kimi-k2-instruct",
            ],
            "sambanova": [
                "DeepSeek-R1-Distill-Llama-70B",
            ],
            "scaleway": [
                "gpt-oss-120b",
            ],
        }

        # Return models for current provider or all if not specified
        if self.provider and self.provider in models:
            return models[self.provider]
        else:
            # Return all models flattened
            return [
                model
                for provider_models in models.values()
                for model in provider_models
            ]
