"""
Google Gemini LLM Provider
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.config import settings
from app.utils.helpers import is_usable_api_key
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini provider using the Generative AI API.
    Supports both streaming and non-streaming generation.
    """

    provider_name = "gemini"

    # API endpoint
    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Gemini API key
            model: Default model to use
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.api_key = api_key or settings.gemini_api_key
        self.default_model = model or settings.gemini_model
        self.timeout = timeout
        self.API_BASE = base_url or settings.gemini_base_url + "/models"

        if not self.api_key:
            logger.warning("Gemini API key not configured")

    def _build_gemini_contents(
        self,
        prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Build contents array for Gemini API"""
        contents = []

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                # Gemini uses "user" and "model" roles
                gemini_role = "model" if role == "assistant" else "user"
                contents.append(
                    {"role": gemini_role, "parts": [{"text": msg.get("content", "")}]}
                )

        # Build current prompt with context
        current_prompt = prompt
        if context:
            current_prompt = f"Context:\n{context}\n\nUser Query:\n{prompt}"

        contents.append({"role": "user", "parts": [{"text": current_prompt}]})

        return contents

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Generate a response using Gemini API"""
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build contents
        contents = self._build_gemini_contents(prompt, context, conversation_history)

        # Build request payload
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.temperature,
                "topP": config.top_p,
                "topK": config.top_k,
                "maxOutputTokens": config.max_tokens,
            },
        }

        # Add system instruction if provided
        if config.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": config.system_prompt}]}
        else:
            payload["systemInstruction"] = {
                "parts": [
                    {
                        "text": (
                            "You are DurgasAI, a helpful AI assistant specialized in "
                            "web page analysis, content extraction, and SEO optimization. "
                            "Provide clear, accurate, and helpful responses."
                        )
                    }
                ]
            }

        if config.stop_sequences:
            payload["generationConfig"]["stopSequences"] = config.stop_sequences

        # Add tools (function calling) if provided
        if config.tools:
            payload["tools"] = config.tools

        # Add safety settings if provided
        if config.safety_settings:
            payload["safetySettings"] = config.safety_settings

        # Add response MIME type if provided
        if config.response_mime_type:
            payload["generationConfig"]["responseMimeType"] = config.response_mime_type

        url = f"{self.API_BASE}/{model}:generateContent?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract text from response
                text = ""
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")

                # Get usage metadata
                usage_metadata = data.get("usageMetadata", {})

                return LLMResponse(
                    text=text,
                    model=model,
                    provider=self.provider_name,
                    usage={
                        "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                        "completion_tokens": usage_metadata.get(
                            "candidatesTokenCount", 0
                        ),
                        "total_tokens": usage_metadata.get("totalTokenCount", 0),
                    },
                    finish_reason=(
                        candidates[0].get("finishReason") if candidates else None
                    ),
                    raw_response=data,
                )

        except httpx.HTTPError as e:
            logger.error(f"Gemini API error: {e}")
            raise Exception(f"Gemini API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response using Gemini API"""
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model

        # Build contents
        contents = self._build_gemini_contents(prompt, context, conversation_history)

        # Build request payload
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.temperature,
                "topP": config.top_p,
                "topK": config.top_k,
                "maxOutputTokens": config.max_tokens,
            },
        }

        if config.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": config.system_prompt}]}

        # Add tools (function calling) if provided
        if config.tools:
            payload["tools"] = config.tools

        # Add safety settings if provided
        if config.safety_settings:
            payload["safetySettings"] = config.safety_settings

        # Add response MIME type if provided
        if config.response_mime_type:
            payload["generationConfig"]["responseMimeType"] = config.response_mime_type

        url = f"{self.API_BASE}/{model}:streamGenerateContent?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload) as http_resp:
                    http_resp.raise_for_status()

                    buffer = ""
                    async for chunk in http_resp.aiter_text():
                        buffer += chunk

                        # Try to parse complete JSON objects
                        while True:
                            try:
                                # Find JSON object boundaries
                                import json

                                # Parse streaming response
                                if buffer.strip().startswith("["):
                                    buffer = buffer.strip()[1:]
                                if buffer.strip().startswith(","):
                                    buffer = buffer.strip()[1:]
                                if buffer.strip().startswith("{"):
                                    # Try to find complete object
                                    depth = 0
                                    end_idx = -1
                                    for i, char in enumerate(buffer):
                                        if char == "{":
                                            depth += 1
                                        elif char == "}":
                                            depth -= 1
                                            if depth == 0:
                                                end_idx = i + 1
                                                break

                                    if end_idx > 0:
                                        json_str = buffer[:end_idx]
                                        buffer = buffer[end_idx:]

                                        data = json.loads(json_str)
                                        candidates = data.get("candidates", [])
                                        if candidates:
                                            content = candidates[0].get("content", {})
                                            parts = content.get("parts", [])
                                            if parts:
                                                text = parts[0].get("text", "")
                                                if text:
                                                    yield text
                                    else:
                                        break
                                else:
                                    break
                            except (json.JSONDecodeError, IndexError):
                                break

        except httpx.HTTPError as e:
            logger.error(f"Gemini streaming error: {e}")
            # Fallback to non-streaming
            llm_resp = await self.generate(
                prompt, config, context, conversation_history
            )
            yield llm_resp.text

    async def health_check(self) -> bool:
        """Check if Gemini API is available"""
        if not is_usable_api_key(self.api_key):
            return False

        try:
            url = f"{self.API_BASE}?key={self.api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available Gemini models"""
        return [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-pro",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash-lite",
            "gemini-3-pro-preview",
            "gemma-3-27b-it",
            "gemma-3-12b-it",
            "gemma-3-4b-it",
            "gemma-3-1b-it",
            "gemma-3n-e4b-it",
            "learnlm-1.5-pro-experimental",
        ]
