"""
Image generation service for fal.ai models
Supports flux-pro, imagen4, and veo3 models
"""

import logging
from typing import Any, Dict

from .client import FalClient
from .queue_manager import QueueManager
from .models import ImageGenerationResponse, ImageResult

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """
    Service for generating images using fal.ai models.
    Supports multiple model variants with unified interface.
    """

    def __init__(self, client: FalClient, queue_mgr: QueueManager):
        """
        Initialize image generation service.

        Args:
            client: FalClient instance
            queue_mgr: QueueManager instance
        """
        self.client = client
        self.queue_mgr = queue_mgr

    async def generate_flux_pro(
        self, prompt: str, version: str = "v1.1-ultra", wait: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate image using flux-pro model.

        Args:
            prompt: Text prompt describing the image
            version: Model version ("v1.1-ultra" or "kontext")
            wait: If True, wait for completion and return result; if False, return job info
            **kwargs: Additional parameters (seed, num_images, etc.)

        Returns:
            Image generation result or job submission info
        """
        model_id = f"flux-pro/{version}" if version != "kontext" else "flux-pro/kontext"

        payload = {"prompt": prompt}
        if "seed" in kwargs:
            payload["seed"] = kwargs["seed"]
        if "num_images" in kwargs:
            payload["num_images"] = kwargs["num_images"]
        if "aspect_ratio" in kwargs:
            payload["aspect_ratio"] = kwargs["aspect_ratio"]
        if "guidance_scale" in kwargs:
            payload["guidance_scale"] = kwargs["guidance_scale"]
        if "num_inference_steps" in kwargs:
            payload["num_inference_steps"] = kwargs["num_inference_steps"]

        job_response = await self.client.submit_job(model_id, payload)

        if not wait:
            return job_response

        # Wait for completion
        result = await self.queue_mgr.wait_for_completion(
            status_url=job_response["status_url"],
            response_url=job_response["response_url"],
        )

        return {
            "job_id": job_response["request_id"],
            "result": result,
            "model": model_id,
        }

    async def generate_imagen4(
        self, prompt: str, variant: str = "preview", wait: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate image using imagen4 model.

        Args:
            prompt: Text prompt describing the image
            variant: Model variant ("preview", "preview/fast", "preview/ultra")
            wait: If True, wait for completion; if False, return job info
            **kwargs: Additional parameters

        Returns:
            Image generation result or job submission info
        """
        model_id = f"imagen4/{variant}" if variant != "preview" else "imagen4/preview"

        payload = {"prompt": prompt}
        if "seed" in kwargs:
            payload["seed"] = kwargs["seed"]
        if "num_images" in kwargs:
            payload["num_images"] = kwargs["num_images"]
        if "aspect_ratio" in kwargs:
            payload["aspect_ratio"] = kwargs["aspect_ratio"]

        job_response = await self.client.submit_job(model_id, payload)

        if not wait:
            return job_response

        result = await self.queue_mgr.wait_for_completion(
            status_url=job_response["status_url"],
            response_url=job_response["response_url"],
        )

        return {
            "job_id": job_response["request_id"],
            "result": result,
            "model": model_id,
        }

    async def generate_veo3(
        self, prompt: str, fast: bool = False, wait: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate image using veo3 model.

        Args:
            prompt: Text prompt describing the image
            fast: If True, use veo3/fast variant
            wait: If True, wait for completion; if False, return job info
            **kwargs: Additional parameters

        Returns:
            Image generation result or job submission info
        """
        model_id = "veo3/fast" if fast else "veo3"

        payload = {"prompt": prompt}
        if "seed" in kwargs:
            payload["seed"] = kwargs["seed"]
        if "aspect_ratio" in kwargs:
            payload["aspect_ratio"] = kwargs["aspect_ratio"]

        job_response = await self.client.submit_job(model_id, payload)

        if not wait:
            return job_response

        result = await self.queue_mgr.wait_for_completion(
            status_url=job_response["status_url"],
            response_url=job_response["response_url"],
        )

        return {
            "job_id": job_response["request_id"],
            "result": result,
            "model": model_id,
        }

    def _parse_image_response(self, result: Dict[str, Any]) -> ImageGenerationResponse:
        """
        Parse raw API response into ImageGenerationResponse.

        Args:
            result: Raw API response

        Returns:
            Parsed image generation response
        """
        images = []

        if "images" in result:
            for img in result["images"]:
                images.append(
                    ImageResult(
                        url=img.get("url", ""),
                        width=img.get("width"),
                        height=img.get("height"),
                        content_type=img.get("content_type"),
                    )
                )

        return ImageGenerationResponse(
            images=images,
            seed=result.get("seed"),
            has_nsfw_concepts=result.get("has_nsfw_concepts"),
            prompt=result.get("prompt"),
            timings=result.get("timings"),
        )
