"""
Cohere Reranking Service
"""

from typing import List, Optional, Dict, Any
from .client import CohereClient


class CohereReranker:
    def __init__(self):
        self.client = CohereClient()
        self.default_model = "rerank-english-v3.0"

    async def rerank(
        self,
        query: str,
        documents: List[str],
        model: str | None = None,
        top_n: Optional[int] = None,
        return_documents: bool = True,
    ) -> Dict[str, Any]:
        """Rerank documents by relevance"""
        payload = {
            "query": query,
            "documents": documents,
            "model": model or self.default_model,
            "return_documents": return_documents,
        }
        if top_n:
            payload["top_n"] = top_n

        return await self.client.post("/rerank", payload)
