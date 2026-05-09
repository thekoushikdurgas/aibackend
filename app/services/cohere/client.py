"""
Base Cohere API client
"""

import httpx
import logging
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


class CohereClient:
    """Base client for all Cohere API interactions"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.cohere_api_key
        self.base_url = settings.cohere_base_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=120.0,
        )

    async def post(self, endpoint: str, data: Dict[str, Any]):
        """POST request"""
        response = await self.client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        """GET request"""
        response = await self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    async def patch(self, endpoint: str, data: Dict[str, Any]):
        """PATCH request"""
        response = await self.client.patch(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    async def delete(self, endpoint: str):
        """DELETE request"""
        response = await self.client.delete(endpoint)
        response.raise_for_status()
        return response.json() if response.content else {}

    async def close(self):
        """Close client"""
        await self.client.aclose()
