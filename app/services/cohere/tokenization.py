"""
Cohere Tokenization Service
"""

from typing import Any, Dict, List, Optional
from .client import CohereClient


class CohereTokenizer:
    def __init__(self):
        self.client = CohereClient()
        self.default_model = "command"

    async def tokenize(self, text: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Tokenize text"""
        payload = {"text": text, "model": model or self.default_model}
        return await self.client.post("/tokenize", payload)

    async def detokenize(
        self, tokens: List[int], model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Detokenize tokens"""
        payload = {"tokens": tokens, "model": model or self.default_model}
        return await self.client.post("/detokenize", payload)
