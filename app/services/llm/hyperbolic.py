"""
Hyperbolic LLM Provider
Open access AI cloud with OpenAI-compatible API
"""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from app.config import settings
from app.services.hyperbolic import HyperbolicClient, TEXT_MODELS, VISION_MODELS
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class HyperbolicProvider(BaseLLMProvider):
    """
    Hyperbolic provider using OpenAI-compatible Chat Completions API.
    Supports text and vision models.
    """

    provider_name = "hyperbolic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Hyperbolic provider.

        Args:
            api_key: Hyperbolic API key
            model: Default model to use
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.api_key = api_key or settings.hyperbolic_api_key
        self.default_model = model or settings.hyperbolic_default_text_model
        self.timeout = timeout or settings.hyperbolic_timeout
        self.base_url = base_url or settings.hyperbolic_base_url

        # Initialize client
        self.client = HyperbolicClient(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

        if not self.api_key:
            logger.warning("Hyperbolic API key not configured")

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build messages array for Hyperbolic chat completions API.
        Uses OpenAI-compatible format with system/user/assistant roles.
        Supports multimodal content (text and image_url).
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

        # Add context if provided
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

                content = msg.get("content", "")
                # Handle multimodal content (list of content items)
                if isinstance(content, list):
                    messages.append({"role": role, "content": content})
                else:
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
        """Generate a response using Hyperbolic API"""
        if not self.api_key:
            raise Exception("Hyperbolic API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload (OpenAI-compatible format)
        payload = {
            "messages": messages,
            "model": model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }

        # Add presence_penalty if provided
        if config.presence_penalty is not None:
            payload["presence_penalty"] = config.presence_penalty

        # Add stop sequences if provided
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        try:
            data = await self.client.post("/chat/completions", payload)

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

        except Exception as e:
            logger.error(f"Hyperbolic API error: {e}")
            raise Exception(f"Hyperbolic API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response using Hyperbolic API"""
        if not self.api_key:
            raise Exception("Hyperbolic API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build messages
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )

        # Build request payload with streaming enabled
        payload = {
            "messages": messages,
            "model": model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True,
        }

        # Add presence_penalty if provided
        if config.presence_penalty is not None:
            payload["presence_penalty"] = config.presence_penalty

        # Add stop sequences if provided
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        try:
            response = await self.client.post_stream("/chat/completions", payload)

            buffer = ""
            async for chunk in response.aiter_text():
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

        except Exception as e:
            logger.error(f"Hyperbolic streaming error: {e}")
            # Fallback to non-streaming
            response = await self.generate(
                prompt, config, context, conversation_history
            )
            yield response.text

    async def health_check(self) -> bool:
        """Check if Hyperbolic API is available"""
        if not self.api_key:
            return False

        try:
            return await self.client.health_check()
        except Exception as e:
            logger.warning(f"Hyperbolic health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available Hyperbolic models"""
        return TEXT_MODELS + VISION_MODELS

    def _prepare_image_content(self, image: Union[str, bytes]) -> Dict[str, str]:
        """
        Prepare image content for multimodal message format.

        Args:
            image: Image URL or base64-encoded image

        Returns:
            Dictionary with image_url format
        """
        if isinstance(image, bytes):
            # Convert bytes to base64 data URL
            import base64

            image_b64 = base64.b64encode(image).decode("utf-8")
            return {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
            }
        elif isinstance(image, str):
            if image.startswith("http://") or image.startswith("https://"):
                # URL
                return {"type": "image_url", "image_url": {"url": image}}
            elif image.startswith("data:image"):
                # Data URL
                return {"type": "image_url", "image_url": {"url": image}}
            else:
                # Assume base64
                return {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                }
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    async def generate_with_vision(
        self,
        prompt: str,
        images: List[Union[str, bytes]],
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Generate a response with vision capabilities (text + images).

        Args:
            prompt: Text prompt
            images: List of image URLs or base64-encoded images
            config: Generation configuration
            context: Optional context
            conversation_history: Previous conversation messages

        Returns:
            LLMResponse with generated text
        """
        if not self.api_key:
            raise Exception("Hyperbolic API key not configured")

        # Auto-select vision model if not specified
        config = config or LLMConfig()
        if not config.model:
            config.model = settings.hyperbolic_default_vision_model

        model = config.model or settings.hyperbolic_default_vision_model

        # Build multimodal message content
        content_items = [{"type": "text", "text": prompt}]
        for image in images:
            content_items.append(self._prepare_image_content(image))

        # Build messages with multimodal content
        messages = []

        # Add system message
        if config.system_prompt:
            messages.append({"role": "system", "content": config.system_prompt})
        elif not conversation_history:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "You are DurgasAI, a helpful AI assistant specialized in "
                        "web page analysis, content extraction, and SEO optimization. "
                        "You can analyze images and provide detailed visual descriptions. "
                        "Provide clear, accurate, and helpful responses."
                    ),
                }
            )

        # Add context
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
                if role not in ["system", "user", "assistant"]:
                    role = "user"
                messages.append({"role": role, "content": msg.get("content", "")})

        # Add current multimodal message
        messages.append({"role": "user", "content": content_items})

        # Build request payload
        payload = {
            "messages": messages,
            "model": model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }

        if config.presence_penalty is not None:
            payload["presence_penalty"] = config.presence_penalty

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        try:
            data = await self.client.post("/chat/completions", payload)

            # Extract text from response
            text = ""
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                text = message.get("content", "")

            usage = data.get("usage", {})
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

        except Exception as e:
            logger.error(f"Hyperbolic vision API error: {e}")
            raise Exception(f"Hyperbolic vision API error: {str(e)}")
