"""Google Vertex AI — uses Gemini-compatible generateContent via Google API."""

from __future__ import annotations

from typing import Optional

from app.config import settings
from .gemini import GeminiProvider


class VertexProvider(GeminiProvider):
    """Vertex uses Gemini models with project/location routing."""

    provider_name = "vertex"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        super().__init__(
            api_key=api_key or settings.gemini_api_key,
            model=model or settings.vertex_model,
        )
        self.provider_name = "vertex"
        project = settings.vertex_project_id
        location = settings.vertex_location
        if project:
            self.API_BASE = (
                f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
                f"/locations/{location}/publishers/google/models"
            )
