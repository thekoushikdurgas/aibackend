"""
Ollama Web Search Service
Perform web searches via Ollama Cloud API
"""

import logging
from typing import Dict, Optional

from .client import OllamaClient, OllamaMode

logger = logging.getLogger(__name__)


class OllamaWebSearchService:
    """
    Service for performing web searches via Ollama Cloud.

    Note: Web search is only available in cloud mode.
    """

    def __init__(
        self,
        cloud_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        Initialize Ollama web search service.

        Args:
            cloud_url: Base URL for cloud mode
            api_key: API key for cloud mode
            timeout: Request timeout in seconds
        """
        self.client = OllamaClient(
            cloud_url=cloud_url,
            api_key=api_key,
            mode=OllamaMode.CLOUD,
            timeout=timeout or 120.0,
        )

        if self.client.mode != OllamaMode.CLOUD:
            logger.warning("Web search requires cloud mode")

    async def search(self, query: str) -> Dict:
        """
        Perform a web search query.

        Args:
            query: Search query string

        Returns:
            Search results dictionary
        """
        if self.client.mode != OllamaMode.CLOUD:
            raise ValueError("Web search is only available in cloud mode")

        try:
            payload = {"query": query}
            response = await self.client.post("web_search", json=payload)
            return response.json()
        except Exception as e:
            logger.error(f"Web search error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Ollama cloud service is available"""
        return await self.client.health_check()
