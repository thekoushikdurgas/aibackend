"""IBM watsonx.ai — OpenAI-compatible inference where available."""

from __future__ import annotations

from typing import Optional

from app.config import settings
from .openai_compat import OpenAICompatibleProvider


class WatsonxProvider(OpenAICompatibleProvider):
    provider_name = "watsonx"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        base = base_url or settings.watsonx_base_url
        if settings.watsonx_project_id:
            base = f"{base.rstrip('/')}/ml/v1/text/chat"
        super().__init__(
            provider_name="watsonx",
            api_key=api_key or settings.watsonx_api_key,
            default_model=model or settings.watsonx_model,
            base_url=base,
            timeout=timeout,
            use_max_completion_tokens=False,
        )
