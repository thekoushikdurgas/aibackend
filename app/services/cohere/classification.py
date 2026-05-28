"""
Cohere Classification Service
"""

from typing import Any, Dict, List
from .client import CohereClient


class CohereClassifier:
    def __init__(self):
        self.client = CohereClient()
        self.default_model = "embed-english-v3.0"

    async def classify(
        self,
        inputs: List[str],
        examples: List[Dict[str, str]],
        model: str | None = None,
        truncate: str = "END",
    ) -> Dict[str, Any]:
        """Classify texts"""
        payload = {
            "inputs": inputs,
            "examples": examples,
            "model": model or self.default_model,
            "truncate": truncate,
        }
        return await self.client.post("/classify", payload)
