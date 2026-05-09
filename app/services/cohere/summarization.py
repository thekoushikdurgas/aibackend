"""
Cohere Summarization Service
"""

from typing import Optional, Dict, Any
from .client import CohereClient


class CohereSummarizer:
    def __init__(self):
        self.client = CohereClient()
        self.default_model = "command"

    async def summarize(
        self,
        text: str,
        model: Optional[str] = None,
        length: Optional[str] = None,
        format: Optional[str] = None,
        extractiveness: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Summarize text"""
        payload = {"text": text, "model": model or self.default_model}
        if length:
            payload["length"] = length
        if format:
            payload["format"] = format
        if extractiveness:
            payload["extractiveness"] = extractiveness
        if temperature is not None:
            payload["temperature"] = temperature

        return await self.client.post("/summarize", payload)
