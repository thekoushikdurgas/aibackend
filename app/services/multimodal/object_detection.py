"""
Object Detection Service using HuggingFace Inference API
Supports DETR and other object detection models
"""

import base64
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.llm.hf_client import HuggingFaceClient

logger = logging.getLogger(__name__)


class ObjectDetectionService:
    """Service for detecting objects in images"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize object detection service.

        Args:
            api_key: HuggingFace API key
            model: Model to use (defaults to config)
        """
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.hf_object_detection_model
        self.client = HuggingFaceClient(api_key=self.api_key)

    async def detect(
        self,
        image_data: bytes,
        filename: str = "image.jpg",
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect objects in an image.

        Args:
            image_data: Binary image data
            filename: Name of the file (for content type detection)
            model: Model to use (overrides default)

        Returns:
            List of detected objects with scores and bounding boxes
        """
        model = model or self.model

        # Determine content type from filename
        content_type = "image/jpeg"
        if filename.lower().endswith((".png",)):
            content_type = "image/png"
        elif filename.lower().endswith((".gif",)):
            content_type = "image/gif"
        elif filename.lower().endswith((".webp",)):
            content_type = "image/webp"

        try:
            response = await self.client.inference_api_file(
                model=model,
                file_data=image_data,
                filename=filename,
                content_type=content_type,
            )

            # Response is typically a list of detections
            if isinstance(response, list):
                return response
            elif isinstance(response, dict):
                # Some models return dict with detections
                if "detections" in response:
                    return response["detections"]
                elif "results" in response:
                    return response["results"]
                # Return as single-item list
                return [response]
            else:
                logger.warning(f"Unexpected response format: {type(response)}")
                return []

        except Exception as e:
            logger.error(f"Object detection error: {e}")
            raise

    async def detect_from_url(
        self, image_url: str, model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect objects in an image from URL.

        Args:
            image_url: URL of the image
            model: Model to use (overrides default)

        Returns:
            List of detected objects
        """
        model = model or self.model

        try:
            # Download image
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content

            # Extract filename from URL
            parsed = urlparse(image_url)
            filename = parsed.path.split("/")[-1] or "image.jpg"

            return await self.detect(image_data, filename, model)

        except Exception as e:
            logger.error(f"Error detecting from URL: {e}")
            raise

    async def detect_from_base64(
        self,
        base64_image: str,
        filename: str = "image.jpg",
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect objects in an image from base64 string.

        Args:
            base64_image: Base64-encoded image (with or without data URL prefix)
            filename: Name of the file
            model: Model to use (overrides default)

        Returns:
            List of detected objects
        """
        # Remove data URL prefix if present
        if base64_image.startswith("data:image/"):
            base64_image = base64_image.split(",", 1)[1]

        try:
            image_data = base64.b64decode(base64_image)
            return await self.detect(image_data, filename, model)
        except Exception as e:
            logger.error(f"Error decoding base64 image: {e}")
            raise

    def format_detections(
        self, detections: List[Dict[str, Any]], min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Format detection results with filtering.

        Args:
            detections: Raw detection results
            min_score: Minimum confidence score to include

        Returns:
            Formatted detection list
        """
        formatted = []
        for det in detections:
            score = det.get("score", 0.0)
            if score >= min_score:
                formatted.append(
                    {
                        "label": det.get("label", "unknown"),
                        "score": round(score, 4),
                        "box": det.get("box", {}),
                    }
                )

        # Sort by score descending
        formatted.sort(key=lambda x: x["score"], reverse=True)
        return formatted
