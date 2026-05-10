"""
Deep Infra LLM Provider
Cost-effective API with good model selection
Supports chat completions, text completions, embeddings, and direct inference
"""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import httpx

from app.config import settings
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class DeepInfraProvider(BaseLLMProvider):
    """
    Deep Infra provider using OpenAI-compatible API.
    Cost-effective inference with multiple model options.
    Supports chat completions, text completions, embeddings, and direct model inference.
    """

    provider_name = "deepinfra"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
        inference_base_url: Optional[str] = None,
    ):
        """Initialize Deep Infra provider"""
        self.api_key = api_key or getattr(settings, "deepinfra_api_key", None)
        self.default_model = model or getattr(
            settings, "deepinfra_model", "google/gemma-7b-it"
        )
        self.timeout = timeout
        self.base_url = base_url or getattr(
            settings, "deepinfra_base_url", "https://api.deepinfra.com/v1/openai"
        )
        self.inference_base_url = inference_base_url or getattr(
            settings, "deepinfra_inference_base_url", "https://api.deepinfra.com/v1"
        )
        self.default_embedding_model = getattr(
            settings, "deepinfra_embedding_model", "thenlper/gte-large"
        )

        if not self.api_key:
            logger.warning("Deep Infra API key not configured")

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Generate a response using Deep Infra API"""
        if not self.api_key:
            raise Exception("Deep Infra API key not configured")

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
            logger.error(f"Deep Infra API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Deep Infra API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Deep Infra API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response using Deep Infra API"""
        if not self.api_key:
            raise Exception("Deep Infra API key not configured")

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
            logger.error(f"Deep Infra streaming error: {e}")
            response = await self.generate(
                prompt, config, context, conversation_history
            )
            yield response.text

    async def health_check(self) -> bool:
        """Check if Deep Infra API is available"""
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
            logger.warning(f"Deep Infra health check failed: {e}")
            return False

    async def complete(
        self, prompt: str, config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """
        Generate text completion using Deep Infra /completions endpoint.
        Simple prompt-to-text generation without conversation history.
        """
        if not self.api_key:
            raise Exception("Deep Infra API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        if config.top_p:
            payload["top_p"] = config.top_p

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        url = f"{self.base_url}/completions"
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
                    text = choices[0].get("text", "")

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
            logger.error(f"Deep Infra completions API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Deep Infra API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Deep Infra API error: {str(e)}")

    async def generate_embeddings(
        self, text: Union[str, List[str]], model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings using Deep Infra /embeddings endpoint.

        Args:
            text: Single text string or list of texts for batch processing
            model: Embedding model to use (default: thenlper/gte-large)

        Returns:
            Dictionary with embeddings, model, and usage information
        """
        if not self.api_key:
            raise Exception("Deep Infra API key not configured")

        model = model or self.default_embedding_model

        payload = {"model": model, "input": text}

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                embeddings = []
                if "data" in data:
                    for item in data["data"]:
                        embeddings.append(item.get("embedding", []))

                usage = data.get("usage", {})

                return {
                    "embeddings": embeddings,
                    "model": model,
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    "raw_response": data,
                }

        except httpx.HTTPError as e:
            logger.error(f"Deep Infra embeddings API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Deep Infra embeddings error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Deep Infra embeddings error: {str(e)}")

    async def inference(
        self,
        model_path: str,
        input_data: Dict[str, Any],
        inference_base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Direct model inference using Deep Infra model-specific endpoints.
        Supports text models and image generation models.

        Args:
            model_path: Model path in format "organization/model-name"
                       e.g., "black-forest-labs/FLUX-1-dev", "bigcode/starcoder"
            input_data: Input data for the model (varies by model type)
            inference_base_url: Optional custom inference base URL

        Returns:
            Raw response from the inference endpoint
        """
        if not self.api_key:
            raise Exception("Deep Infra API key not configured")

        base_url = inference_base_url or self.inference_base_url
        url = f"{base_url}/{model_path}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=input_data, headers=headers)
                response.raise_for_status()

                # Check if response is image (binary) or JSON
                content_type = response.headers.get("content-type", "")
                if "image" in content_type:
                    return {
                        "image": response.content,
                        "content_type": content_type,
                        "model": model_path,
                    }
                else:
                    return {"data": response.json(), "model": model_path}

        except httpx.HTTPError as e:
            logger.error(f"Deep Infra inference API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Deep Infra inference error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Deep Infra inference error: {str(e)}")

    async def list_models(self) -> List[str]:
        """List available Deep Infra models organized by category"""
        return self._get_chat_models()

    def _get_chat_models(self) -> List[str]:
        """Get list of chat models"""
        return [
            # Meta Llama Family
            "meta-llama/Llama-2-7b-chat-hf",
            "meta-llama/Llama-2-13b-chat-hf",
            "meta-llama/Llama-2-70b-chat-hf",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "meta-llama/Meta-Llama-3-70B-Instruct",
            "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "meta-llama/Meta-Llama-3.1-405B-Instruct",
            "meta-llama/Llama-3.2-1B-Instruct",
            "meta-llama/Llama-3.2-3B-Instruct",
            "meta-llama/Llama-3.2-11B-Vision-Instruct",
            "meta-llama/Llama-3.2-90B-Vision-Instruct",
            "meta-llama/Llama-3.3-70B-Instruct",
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
            "meta-llama/Llama-Guard-4-12B",
            # Google Gemma
            "google/gemma-7b-it",
            "google/gemma-3-4b-it",
            "google/gemma-3-12b-it",
            "google/gemma-3-27b-it",
            # DeepSeek
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "deepseek-ai/DeepSeek-R1-0528",
            "deepseek-ai/DeepSeek-R1-Turbo",
            "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
            "deepseek-ai/DeepSeek-Prover-V2-671B",
            # Mistral/Mixtral
            "mistralai/Mistral-7B-Instruct-v0.1",
            "mistralai/Mistral-7B-Instruct-v0.2",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            # Qwen
            "Qwen/Qwen3-14B",
            "Qwen/Qwen3-32B",
            "Qwen/Qwen3-30B-A3B",
            "Qwen/Qwen3-235B-A22B",
            # Code Models
            "codellama/CodeLlama-34b-Instruct-hf",
            "codellama/CodeLlama-70b-Instruct-hf",
            "bigcode/starcoder2-15b",
            "Phind/Phind-CodeLlama-34B-v2",
            # Other Models
            "01-ai/Yi-34B-Chat",
            "microsoft/phi-4",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "moonshotai/Kimi-K2-Instruct",
            "Austism/chronos-hermes-13b-v2",
            "cognitivecomputations/dolphin-2.6-mixtral-8x7b",
            "deepinfra/airoboros-70b",
            "DeepInfra/pygmalion-13b-4bit-128g",
            "Gryphe/MythoMax-L2-13b",
            "lizpreciatior/lzlv_70b_fp16_hf",
            # Vision Models
            "llava-hf/llava-1.5-7b-hf",
        ]

    def get_completion_models(self) -> List[str]:
        """Get list of models that support text completion endpoint"""
        return [
            "google/gemma-7b-it",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "meta-llama/Meta-Llama-3-70B-Instruct",
        ]

    def get_embedding_models(self) -> List[str]:
        """Get list of embedding models"""
        return [
            "thenlper/gte-large",
        ]

    def get_inference_models(self) -> Dict[str, List[str]]:
        """Get list of direct inference models by category"""
        return {
            "text": [
                "bigcode/starcoder",
                "EleutherAI/gpt-j-6B",
                "EleutherAI/gpt-neo-125M",
                "EleutherAI/gpt-neo-1.3B",
                "EleutherAI/pythia-2.8b",
                "EleutherAI/pythia-12b",
                "gpt2",
                "meta-llama/Meta-Llama-3-8B-Instruct",
                "meta-llama/Meta-Llama-3-70B-Instruct",
                "Salesforce/codegen-16B-mono",
            ],
            "image": [
                "black-forest-labs/FLUX-1-dev",
                "black-forest-labs/FLUX-1-schnell",
                "stabilityai/sdxl-turbo",
            ],
        }
