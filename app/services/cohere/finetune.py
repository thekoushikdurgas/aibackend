"""
Cohere Fine-tuning Service
"""

from typing import Dict, Any
from .client import CohereClient


class CohereFineTune:
    def __init__(self):
        self.client = CohereClient()

    async def create_finetuned_model(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Create fine-tuning job"""
        return await self.client.post("/finetuning/finetuned-models", settings)

    async def list_finetuned_models(self) -> Dict[str, Any]:
        """List fine-tuned models"""
        return await self.client.get("/finetuning/finetuned-models")

    async def get_finetuned_model(self, model_id: str) -> Dict[str, Any]:
        """Get fine-tuned model details"""
        return await self.client.get(f"/finetuning/finetuned-models/{model_id}")

    async def update_finetuned_model(
        self, model_id: str, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update fine-tuned model"""
        return await self.client.patch(
            f"/finetuning/finetuned-models/{model_id}", settings
        )

    async def delete_finetuned_model(self, model_id: str) -> Dict[str, Any]:
        """Delete fine-tuned model"""
        return await self.client.delete(f"/finetuning/finetuned-models/{model_id}")

    async def get_finetuned_model_events(self, model_id: str) -> Dict[str, Any]:
        """Get training events"""
        return await self.client.get(f"/finetuning/finetuned-models/{model_id}/events")

    async def get_finetuned_model_metrics(self, model_id: str) -> Dict[str, Any]:
        """Get training metrics"""
        return await self.client.get(f"/finetuning/finetuned-models/{model_id}/metrics")
