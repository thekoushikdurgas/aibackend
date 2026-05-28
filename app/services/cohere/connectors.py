"""
Cohere Connectors Service
"""

from typing import Optional, Dict, Any
from .client import CohereClient


class CohereConnectors:
    def __init__(self):
        self.client = CohereClient()

    async def create_connector(
        self, name: str, url: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a custom connector"""
        payload = {"name": name, "url": url}
        if description:
            payload["description"] = description
        return await self.client.post("/connectors", payload)

    async def list_connectors(self) -> Dict[str, Any]:
        """List all connectors"""
        return await self.client.get("/connectors")

    async def get_connector(self, connector_id: str) -> Dict[str, Any]:
        """Get connector details"""
        return await self.client.get(f"/connectors/{connector_id}")

    async def update_connector(
        self, connector_id: str, name: Optional[str] = None, url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update connector"""
        payload = {}
        if name:
            payload["name"] = name
        if url:
            payload["url"] = url
        return await self.client.patch(f"/connectors/{connector_id}", payload)

    async def delete_connector(self, connector_id: str) -> Dict[str, Any]:
        """Delete connector"""
        return await self.client.delete(f"/connectors/{connector_id}")
