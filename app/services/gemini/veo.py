"""
Veo-3 Video Generation Service
"""

import logging
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class VeoService:
    """
    Service for video generation using Veo-3 API.
    Uses long-running operations for video generation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 600.0,
    ):
        """
        Initialize Veo service.

        Args:
            api_key: Gemini API key
            model: Veo model to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_veo_model
        self.timeout = timeout
        self.base_url = settings.gemini_base_url

        if not self.api_key:
            logger.warning("Gemini API key not configured")

    async def generate(
        self,
        prompt: str,
        aspect_ratio: Optional[str] = None,
        duration: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Start video generation (long-running operation).

        Args:
            prompt: Text prompt describing the video
            aspect_ratio: Video aspect ratio
            duration: Video duration

        Returns:
            Operation response with operation name
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = f"{self.base_url}/models/{self.model}:predictLongRunning"
        headers = {"x-goog-api-key": self.api_key}

        payload = {"instances": [{"prompt": prompt}]}

        if aspect_ratio:
            payload["instances"][0]["aspectRatio"] = aspect_ratio
        if duration:
            payload["instances"][0]["duration"] = duration

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Extract operation name
                operation_name = data.get("name", "")

                return {
                    "operation_name": operation_name,
                    "model": self.model,
                    "prompt": prompt,
                    "raw_response": data,
                }

        except httpx.HTTPError as e:
            logger.error(f"Veo generation error: {e}")
            raise Exception(f"Veo generation error: {str(e)}")

    async def get_status(self, operation_name: str) -> Dict[str, Any]:
        """
        Get status of a video generation operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Operation status
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = f"{self.base_url}/{operation_name}"
        headers = {"x-goog-api-key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Veo status check error: {e}")
            raise Exception(f"Veo status check error: {str(e)}")

    async def get_result(self, operation_name: str) -> Dict[str, Any]:
        """
        Get result of a completed video generation operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Video generation result with video data/URL
        """
        status = await self.get_status(operation_name)

        if not status.get("done", False):
            return {
                "status": "pending",
                "operation_name": operation_name,
                "message": "Operation not yet complete",
            }

        # Extract video data from response
        response = status.get("response", {})
        generate_video_response = response.get("generateVideoResponse", {})
        generated_samples = generate_video_response.get("generatedSamples", [])

        videos = []
        for sample in generated_samples:
            video = sample.get("video", {})
            if "uri" in video:
                videos.append(
                    {
                        "uri": video["uri"],
                        "mimeType": video.get("mimeType", "video/mp4"),
                    }
                )
            elif "bytesBase64Encoded" in video:
                videos.append(
                    {
                        "base64": video["bytesBase64Encoded"],
                        "mimeType": video.get("mimeType", "video/mp4"),
                    }
                )

        return {
            "status": "completed",
            "videos": videos,
            "operation_name": operation_name,
            "raw_response": status,
        }
