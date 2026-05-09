"""
Ollama Lifecycle Service
Manage model runtime lifecycle (load, unload, list running)
"""

import logging
from typing import Any, Dict, List, Optional

from .client import OllamaClient, OllamaMode

logger = logging.getLogger(__name__)


class OllamaLifecycleService:
    """
    Service for managing Ollama model runtime lifecycle.

    Handles:
    - Listing running models (ps)
    - Loading models into memory
    - Unloading models from memory
    - Model status tracking
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        cloud_url: Optional[str] = None,
        api_key: Optional[str] = None,
        mode: Optional[OllamaMode] = None,
        timeout: Optional[float] = None,
    ):
        """
        Initialize Ollama lifecycle service.

        Args:
            base_url: Base URL for localhost mode
            cloud_url: Base URL for cloud mode
            api_key: API key for cloud mode
            mode: Deployment mode
            timeout: Request timeout in seconds
        """
        self.client = OllamaClient(
            base_url=base_url,
            cloud_url=cloud_url,
            api_key=api_key,
            mode=mode,
            timeout=timeout or 120.0,
        )

    async def list_running(self) -> List[Dict[str, Any]]:
        """
        List all models currently loaded in memory (ps command).

        Returns:
            List of running model dictionaries with name, size_vram, expires_at, etc.
        """
        try:
            response = await self.client.get("ps")
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list running models: {e}")
            raise

    async def load_model(
        self, model: str, keep_alive: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pre-load a model into memory.

        Args:
            model: Model name to load
            keep_alive: How long to keep model in memory (e.g., "5m", "1h", or None for default)

        Returns:
            Response dictionary with model info
        """
        try:
            payload = {"model": model}
            if keep_alive is not None:
                payload["keep_alive"] = keep_alive

            # Use generate endpoint with empty prompt to load model
            response = await self.client.post("generate", json=payload)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to load model {model}: {e}")
            raise

    async def unload_model(self, model: str) -> Dict[str, Any]:
        """
        Unload a model from memory.

        Args:
            model: Model name to unload

        Returns:
            Response dictionary
        """
        try:
            payload = {"model": model, "keep_alive": 0}  # 0 means unload immediately
            response = await self.client.post("generate", json=payload)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to unload model {model}: {e}")
            raise

    async def get_model_status(self, model: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific model (whether it's running).

        Args:
            model: Model name

        Returns:
            Model status dictionary or None if not running
        """
        try:
            running = await self.list_running()
            for running_model in running:
                if (
                    running_model.get("name") == model
                    or running_model.get("model") == model
                ):
                    return running_model
            return None
        except Exception as e:
            logger.error(f"Failed to get status for model {model}: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if Ollama service is available"""
        return await self.client.health_check()
