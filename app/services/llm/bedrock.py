"""Amazon Bedrock Converse API provider."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from app.config import settings
from .base import BaseLLMProvider, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class BedrockProvider(BaseLLMProvider):
    provider_name = "bedrock"

    def __init__(
        self,
        region: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.region = region or settings.bedrock_region
        self.default_model = model or settings.bedrock_model

    def _client(self):
        import boto3

        return boto3.client("bedrock-runtime", region_name=self.region)

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        config = config or LLMConfig(model=self.default_model)
        model = config.model or self.default_model
        messages = self._build_messages(
            prompt, context, conversation_history, config.system_prompt
        )
        bedrock_messages = []
        system_blocks = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_blocks.append({"text": content})
            else:
                bedrock_messages.append(
                    {
                        "role": "user" if role == "user" else "assistant",
                        "content": [{"text": content}],
                    }
                )

        body: Dict[str, Any] = {
            "messages": bedrock_messages,
            "inferenceConfig": {
                "maxTokens": config.max_tokens,
                "temperature": config.temperature,
                "topP": config.top_p,
            },
        }
        if system_blocks:
            body["system"] = system_blocks

        import asyncio

        def _invoke() -> Dict[str, Any]:
            client = self._client()
            resp = client.converse(modelId=model, **body)
            return resp

        raw = await asyncio.to_thread(_invoke)
        text = ""
        output = raw.get("output", {})
        msg = output.get("message", {})
        for block in msg.get("content", []):
            if "text" in block:
                text += block["text"]

        usage = raw.get("usage", {})
        return LLMResponse(
            text=text,
            model=model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": usage.get("inputTokens", 0),
                "completion_tokens": usage.get("outputTokens", 0),
                "total_tokens": usage.get("totalTokens", 0),
            },
            raw_response=raw,
        )

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        result = await self.generate(prompt, config, context, conversation_history)
        yield result.text

    async def health_check(self) -> bool:
        try:
            import boto3

            boto3.client("bedrock", region_name=self.region).list_foundation_models(
                maxResults=1
            )
            return True
        except Exception as e:
            logger.debug("Bedrock health_check: %s", e)
            return False

    async def list_models(self) -> List[str]:
        try:
            import asyncio

            def _list() -> List[str]:
                br = __import__("boto3").client("bedrock", region_name=self.region)
                resp = br.list_foundation_models(byOutputModality="TEXT")
                return [m["modelId"] for m in resp.get("modelSummaries", [])][:30]

            return await asyncio.to_thread(_list)
        except Exception:
            return [self.default_model]
