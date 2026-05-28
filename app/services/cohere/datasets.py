"""
Cohere Datasets Service
"""

from typing import Dict, Any
from .client import CohereClient


class CohereDatasets:
    def __init__(self):
        self.client = CohereClient()

    async def list_datasets(self) -> Dict[str, Any]:
        """List all datasets"""
        return await self.client.get("/datasets")

    async def get_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Get dataset details"""
        return await self.client.get(f"/datasets/{dataset_id}")

    async def get_dataset_usage(self) -> Dict[str, Any]:
        """Get dataset usage statistics"""
        return await self.client.get("/datasets/usage")

    async def delete_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Delete dataset"""
        return await self.client.delete(f"/datasets/{dataset_id}")
