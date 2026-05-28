"""
NVIDIA Video Generation Service
Supports Stable Video Diffusion for generating videos from images via NVIDIA GenAI API
"""

import base64
import logging
from typing import Dict, Optional, Any

from .client import NVIDIAClient, BaseURLType

logger = logging.getLogger(__name__)


class NVIDIAVideoService:
    """Service for generating videos using NVIDIA's GenAI API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "stabilityai/stable-video-diffusion",
        timeout: float = 300.0,  # Longer timeout for video generation
        genai_base_url: Optional[str] = None,
    ):
        """
        Initialize NVIDIA video generation service.

        Args:
            api_key: NVIDIA API key
            model: Model to use (defaults to stabilityai/stable-video-diffusion)
            timeout: Request timeout in seconds (default 300 for video)
            genai_base_url: Optional custom GenAI base URL
        """
        self.client = NVIDIAClient(
            api_key=api_key, genai_base_url=genai_base_url, timeout=timeout
        )
        self.model = model

        if not self.client.api_key:
            logger.warning("NVIDIA API key not configured")

    async def generate(
        self,
        image: str,
        model: Optional[str] = None,
        cfg_scale: float = 2.5,
        seed: Optional[int] = None,
        motion_bucket_id: Optional[int] = None,
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a video from an image.

        Args:
            image: Base64-encoded image or data URI (e.g., "data:image/png;base64,...")
            model: Model to use (overrides default)
            cfg_scale: Classifier-free guidance scale
            seed: Random seed for reproducibility
            motion_bucket_id: Motion bucket ID for controlling motion (1-255)
            return_base64: Whether to return base64-encoded video

        Returns:
            Dictionary with video data and metadata
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        model = model or self.model
        endpoint = f"genai/{model}"

        # Ensure image is in data URI format
        if not image.startswith("data:"):
            image = f"data:image/png;base64,{image}"

        # Build request payload
        payload: Dict[str, Any] = {"image": image, "cfg_scale": cfg_scale}

        if seed is not None:
            payload["seed"] = seed

        if motion_bucket_id is not None:
            payload["motion_bucket_id"] = motion_bucket_id

        try:
            response = await self.client.post(
                endpoint, url_type=BaseURLType.GENAI, json=payload
            )

            data = response.json()

            # Extract video from artifacts
            result: dict[str, Any] = {"model": model, "artifacts": []}

            artifacts = data.get("artifacts", [])
            for artifact in artifacts:
                artifact_data = {
                    "finish_reason": artifact.get("finishReason"),
                    "seed": artifact.get("seed"),
                }

                if return_base64 and artifact.get("base64"):
                    artifact_data["base64"] = artifact.get("base64")
                    artifact_data["format"] = "base64"
                else:
                    artifact_data["base64"] = artifact.get("base64")
                    artifact_data["format"] = "base64"

                result["artifacts"].append(artifact_data)

            # Add NVIDIA-specific headers
            nvidia_headers = self.client._extract_nvidia_headers(response)
            result.update(nvidia_headers)

            return result

        except Exception as e:
            logger.error(f"NVIDIA video generation error: {e}")
            raise

    async def generate_from_image_file(
        self, image_path: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a video from an image file.

        Args:
            image_path: Path to the image file
            **kwargs: Additional arguments passed to generate()

        Returns:
            Dictionary with video data and metadata
        """
        # Read and encode image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            image_data_uri = f"data:image/png;base64,{image_base64}"

        return await self.generate(image=image_data_uri, **kwargs)

    async def health_check(self) -> bool:
        """Check if NVIDIA video generation API is available"""
        return await self.client.health_check(BaseURLType.GENAI)
