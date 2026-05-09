"""
Ollama Model Management Service
Handle model pulling, listing, deletion, and information
"""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from .client import OllamaClient, OllamaMode

logger = logging.getLogger(__name__)


class OllamaModelService:
    """
    Service for managing Ollama models.

    Handles:
    - Pulling models from registry
    - Listing available models
    - Deleting models
    - Getting model information
    - Copying/renaming models
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
        Initialize Ollama model service.

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
            timeout=timeout or 600.0,  # Longer timeout for model operations
        )

    async def pull_model(
        self, model: str, stream_progress: bool = False
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Pull/download a model from Ollama registry.

        Args:
            model: Model name to pull (e.g., "llama3", "qwen2.5:0.5b")
            stream_progress: If True, yields progress updates

        Yields:
            Progress updates with status, digest, total, completed
        """
        payload = {"model": model}

        try:
            if stream_progress:
                async with self.client.stream("pull", json=payload) as stream:
                    async for line in stream.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                yield data

                                # Check if done
                                if data.get("status") == "success":
                                    break
                            except json.JSONDecodeError:
                                continue
            else:
                # Non-streaming: wait for completion
                response = await self.client.post("pull", json=payload, timeout=600.0)
                # For non-streaming, we still get NDJSON
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if data.get("status") == "success":
                                yield data
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            raise

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List all locally available (pulled) models.

        Returns:
            List of model dictionaries with name, size, digest, etc.
        """
        try:
            response = await self.client.get("tags")
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise

    async def delete_model(self, model: str) -> bool:
        """
        Delete a model from local storage.

        Args:
            model: Model name to delete

        Returns:
            True if successful
        """
        try:
            payload = {"name": model}
            response = await self.client.delete("delete", json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to delete model {model}: {e}")
            raise

    async def show_model(self, model: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a model.

        Args:
            model: Model name

        Returns:
            Model information dictionary or None if not found
        """
        try:
            payload = {"name": model}
            response = await self.client.post("show", json=payload)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get model info for {model}: {e}")
            return None

    async def copy_model(self, source: str, destination: str) -> bool:
        """
        Copy/rename a model.

        Args:
            source: Source model name
            destination: Destination model name

        Returns:
            True if successful
        """
        try:
            payload = {"source": source, "destination": destination}
            response = await self.client.post("copy", json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to copy model {source} to {destination}: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Ollama service is available"""
        return await self.client.health_check()
