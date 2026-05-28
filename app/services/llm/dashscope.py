"""Alibaba DashScope (OpenAI-compatible mode) provider."""

from __future__ import annotations

from typing import Optional

from app.config import settings
from .openai_compat import OpenAICompatibleProvider


class DashScopeProvider(OpenAICompatibleProvider):
    provider_name = "dashscope"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        super().__init__(
            provider_name="dashscope",
            api_key=api_key or settings.dashscope_api_key,
            default_model=model or settings.dashscope_model,
            base_url=base_url or settings.dashscope_base_url,
            timeout=timeout,
            use_max_completion_tokens=False,
        )
