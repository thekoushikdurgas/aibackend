"""
Hyperbolic Image Generation Service
Handles text-to-image generation
"""

import logging
from typing import Dict, Optional

from .client import HyperbolicClient
from .models import IMAGE_MODELS

logger = logging.getLogger(__name__)


class HyperbolicImageService:
    """Service for image generation using Hyperbolic API"""

    def __init__(self, client: Optional[HyperbolicClient] = None):
        """
        Initialize image service.

        Args:
            client: Optional HyperbolicClient instance
        """
        self.client = client or HyperbolicClient()

    async def generate_image(
        self,
        prompt: str,
        model_name: str,
        steps: int = 30,
        cfg_scale: float = 5.0,
        height: int = 1024,
        width: int = 1024,
        enable_refiner: bool = False,
        backend: str = "auto",
        **kwargs,
    ) -> Dict:
        """
        Generate image from text prompt.

        Args:
            prompt: Text prompt describing the image
            model_name: Image model identifier (FLUX.1-dev, SD1.5, SD2, etc.)
            steps: Number of generation steps (default: 30)
            cfg_scale: Guidance scale (default: 5.0)
            height: Image height in pixels (default: 1024)
            width: Image width in pixels (default: 1024)
            enable_refiner: Whether to enable refiner (default: False)
            backend: Backend selection ("auto" or specific backend)
            **kwargs: Additional model-specific parameters

        Returns:
            Response dict with image data (base64 or URL)
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        if model_name not in IMAGE_MODELS:
            logger.warning(
                f"Model {model_name} not in known image models, proceeding anyway"
            )

        # Validate dimensions
        if height < 64 or height > 2048:
            logger.warning(f"Height {height} outside typical range (64-2048)")
        if width < 64 or width > 2048:
            logger.warning(f"Width {width} outside typical range (64-2048)")

        payload = {
            "model_name": model_name,
            "prompt": prompt,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "enable_refiner": enable_refiner,
            "height": height,
            "width": width,
            "backend": backend,
            **kwargs,
        }

        return await self.client.post("/image/generation", payload)
