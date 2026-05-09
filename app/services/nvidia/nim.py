"""
NVIDIA NIM Service
Self-hosted model deployment management and inference
"""

import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from .client import NVIDIAClient, BaseURLType

logger = logging.getLogger(__name__)


class NVIDIANIMService:
    """
    NVIDIA NIM (NVIDIA Inference Microservice) service.

    Supports:
    - Self-hosted model deployment management
    - Health checks
    - Model metadata retrieval
    - Deployment status monitoring
    - Custom inference endpoints
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        nim_base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        Initialize NVIDIA NIM service.

        Args:
            api_key: NVIDIA API key
            nim_base_url: Base URL for NIM deployment
            timeout: Request timeout in seconds
        """
        self.client = NVIDIAClient(
            api_key=api_key,
            nim_base_url=nim_base_url,
            timeout=timeout or settings.nvidia_nim_timeout,
        )

        if not self.client.api_key:
            logger.warning("NVIDIA API key not configured")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check NIM deployment health.

        Returns:
            Health status dictionary
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        if not self.client.nim_base_url:
            raise ValueError("NIM base URL not configured")

        try:
            response = await self.client.get("health", url_type=BaseURLType.NIM)

            data = response.json()

            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "details": data,
                "status_code": response.status_code,
            }

        except Exception as e:
            logger.error(f"NIM health check error: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List all deployed models in the NIM instance.

        Returns:
            List of model information dictionaries
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        if not self.client.nim_base_url:
            raise ValueError("NIM base URL not configured")

        try:
            response = await self.client.get("models", url_type=BaseURLType.NIM)

            data = response.json()

            # Handle different response formats
            if isinstance(data, dict):
                return data.get("data", data.get("models", []))
            elif isinstance(data, list):
                return data
            else:
                return []

        except Exception as e:
            logger.error(f"NIM list models error: {e}")
            raise

    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific deployed model.

        Args:
            model_id: Model identifier

        Returns:
            Model metadata dictionary or None if not found
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        if not self.client.nim_base_url:
            raise ValueError("NIM base URL not configured")

        try:
            response = await self.client.get(
                f"models/{model_id}", url_type=BaseURLType.NIM
            )

            return response.json()

        except Exception as e:
            logger.error(f"NIM get model info error: {e}")
            return None

    async def infer(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Run inference on a deployed NIM model.

        Args:
            model_id: Model identifier
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response

        Returns:
            Inference result
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        if not self.client.nim_base_url:
            raise ValueError("NIM base URL not configured")

        # Build request payload
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            if stream:
                # Handle streaming response
                async with self.client.stream(
                    "chat/completions", url_type=BaseURLType.NIM, json=payload
                ) as response:
                    response.raise_for_status()
                    # Return streaming context
                    return {"stream": response}
            else:
                response = await self.client.post(
                    "chat/completions", url_type=BaseURLType.NIM, json=payload
                )

                data = response.json()

                # Extract NVIDIA-specific headers
                nvidia_headers = self.client._extract_nvidia_headers(response)

                result = {**data, **nvidia_headers}

                return result

        except Exception as e:
            logger.error(f"NIM inference error: {e}")
            raise

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get deployment metrics.

        Returns:
            Metrics dictionary
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        if not self.client.nim_base_url:
            raise ValueError("NIM base URL not configured")

        try:
            response = await self.client.get("metrics", url_type=BaseURLType.NIM)

            return response.json()

        except Exception as e:
            logger.error(f"NIM get metrics error: {e}")
            raise

    async def is_available(self) -> bool:
        """
        Check if NIM deployment is available.

        Returns:
            True if available, False otherwise
        """
        if not self.client.nim_base_url:
            return False

        try:
            health = await self.health_check()
            return health.get("status") == "healthy"
        except Exception:
            return False
