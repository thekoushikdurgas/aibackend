"""
Cohere Embeddings Service
"""

from typing import List, Dict, Any
from .client import CohereClient


class CohereEmbeddings:
    def __init__(self):
        self.client = CohereClient()
        self.default_model = "embed-english-v3.0"

    async def embed(
        self,
        texts: List[str],
        model: str = None,
        input_type: str = "search_document",
        truncate: str = "END",
    ) -> Dict[str, Any]:
        """Generate embeddings"""
        payload = {
            "texts": texts,
            "model": model or self.default_model,
            "input_type": input_type,
            "truncate": truncate,
        }
        return await self.client.post("/embed", payload)

    async def create_embed_job(
        self, dataset_id: str, model: str = None, input_type: str = "search_document"
    ) -> Dict[str, Any]:
        """Create async embedding job"""
        payload = {
            "model": model or self.default_model,
            "dataset_id": dataset_id,
            "input_type": input_type,
        }
        return await self.client.post("/embed-jobs", payload)

    async def list_embed_jobs(self) -> Dict[str, Any]:
        """List embed jobs"""
        return await self.client.get("/embed-jobs")

    async def get_embed_job(self, job_id: str) -> Dict[str, Any]:
        """Get embed job status"""
        return await self.client.get(f"/embed-jobs/{job_id}")

    async def cancel_embed_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel embed job"""
        return await self.client.post(f"/embed-jobs/{job_id}/cancel", {})
