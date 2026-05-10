"""
NVIDIA Image Generation Service
Supports SDXL-Turbo and other image generation models via NVIDIA GenAI API
"""

import logging
from typing import Dict, Optional, Any

from .client import NVIDIAClient, BaseURLType

logger = logging.getLogger(__name__)


class NVIDIAImageService:
    """Service for generating images using NVIDIA's GenAI API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "stabilityai/sdxl-turbo",
        timeout: float = 120.0,
        genai_base_url: Optional[str] = None,
    ):
        """
        Initialize NVIDIA image generation service.

        Args:
            api_key: NVIDIA API key
            model: Model to use (defaults to stabilityai/sdxl-turbo)
            timeout: Request timeout in seconds
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
        prompt: str,
        model: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        sampler: str = "K_EULER_ANCESTRAL",
        steps: int = 2,
        seed: Optional[int] = None,
        cfg_scale: float = 1.0,
        width: int = 1024,
        height: int = 1024,
        return_base64: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image
            model: Model to use (overrides default)
            negative_prompt: Negative prompt to avoid certain elements
            sampler: Sampler to use (e.g., "K_EULER_ANCESTRAL")
            steps: Number of inference steps
            seed: Random seed for reproducibility
            cfg_scale: Classifier-free guidance scale
            width: Image width in pixels
            height: Image height in pixels
            return_base64: Whether to return base64-encoded image

        Returns:
            Dictionary with image data and metadata
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        model = model or self.model
        endpoint = f"genai/{model}"

        # Build text prompts
        text_prompts = [{"text": prompt, "weight": 1.0}]
        if negative_prompt:
            text_prompts.append({"text": negative_prompt, "weight": -1.0})

        # Build request payload
        payload: Dict[str, Any] = {
            "text_prompts": text_prompts,
            "sampler": sampler,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "width": width,
            "height": height,
        }

        if seed is not None:
            payload["seed"] = seed

        try:
            response = await self.client.post(
                endpoint, url_type=BaseURLType.GENAI, json=payload
            )

            data = response.json()

            # Extract image from artifacts
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
            logger.error(f"NVIDIA image generation error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if NVIDIA image generation API is available"""
        return await self.client.health_check(BaseURLType.GENAI)
