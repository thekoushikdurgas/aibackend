"""
OpenAI-compatible Chat Completions provider base (shared by many vendors).
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """HTTP client for POST {base_url}/chat/completions (OpenAI schema)."""

    provider_name: str = "openai_compat"
    use_max_completion_tokens: bool = True

    def __init__(
        self,
        *,
        provider_name: str,
        api_key: Optional[str],
        default_model: str,
        base_url: str,
        timeout: float = 120.0,
        extra_headers: Optional[Dict[str, str]] = None,
        auth_header: str = "Bearer",
        use_max_completion_tokens: Optional[bool] = None,
    ):
        self.provider_name = provider_name
        self.auth_header = auth_header
        self.api_key = api_key
        self.default_model = default_model
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout
        self.extra_headers = extra_headers or {}
        if use_max_completion_tokens is not None:
            self.use_max_completion_tokens = use_max_completion_tokens

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            if self.auth_header.lower() == "api-key":
                headers["api-key"] = self.api_key
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        return headers

    def _payload(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        config: LLMConfig,
        *,
        stream: bool,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": stream,
        }
        if self.use_max_completion_tokens:
            payload["max_completion_tokens"] = config.max_tokens
        else:
            payload["max_tokens"] = config.max_tokens
        if config.frequency_penalty is not None:
            payload["frequency_penalty"] = config.frequency_penalty
        if config.presence_penalty is not None:
            payload["presence_penalty"] = config.presence_penalty
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences
        return payload

    def _parse_response(self, data: Dict[str, Any], model: str) -> LLMResponse:
        text = ""
        choices = data.get("choices", [])
        finish_reason = None
        if choices:
            message = choices[0].get("message", {})
            text = message.get("content", "") or ""
            finish_reason = choices[0].get("finish_reason")
        usage = data.get("usage", {}) or {}
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

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        if not self.api_key and self.provider_name not in ("docker_model_runner",):
            raise Exception(f"{self.provider_name}: API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )
        payload = self._payload(messages, model, config, stream=False)
        url = f"{self.base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=self._headers())
                response.raise_for_status()
                return self._parse_response(response.json(), model)
        except httpx.HTTPError as e:
            logger.error("%s API error: %s", self.provider_name, e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    err = e.response.json()
                    msg = err.get("error", {})
                    if isinstance(msg, dict):
                        msg = msg.get("message", str(e))
                    raise Exception(f"{self.provider_name} API error: {msg}") from e
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"{self.provider_name} API error: {e}") from e

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        if not self.api_key and self.provider_name not in ("docker_model_runner",):
            raise Exception(f"{self.provider_name}: API key not configured")

        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )
        payload = self._payload(messages, model, config, stream=True)
        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", url, json=payload, headers=self._headers()
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content

    async def health_check(self) -> bool:
        if not self.api_key and self.provider_name not in ("docker_model_runner",):
            return False
        try:
            url = f"{self.base_url}/models"
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url, headers=self._headers())
                if r.status_code == 200:
                    return True
            # Some hosts have no /models — try minimal completion
            return bool(self.base_url)
        except Exception:
            return bool(self.base_url and self.api_key)

    async def list_models(self) -> List[str]:
        try:
            url = f"{self.base_url}/models"
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url, headers=self._headers())
                if r.status_code != 200:
                    return [self.default_model] if self.default_model else []
                data = r.json()
                items = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(items, list):
                    ids = []
                    for m in items:
                        if isinstance(m, dict) and m.get("id"):
                            ids.append(str(m["id"]))
                        elif isinstance(m, str):
                            ids.append(m)
                    return ids[:50] if ids else [self.default_model]
        except Exception as e:
            logger.debug("%s list_models: %s", self.provider_name, e)
        return [self.default_model] if self.default_model else []
