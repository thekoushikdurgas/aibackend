"""
Video generation service for fal.ai veo2 model
Supports text-to-video and image-to-video generation
"""

import logging
from typing import Any, Dict, Optional

from .client import FalClient
from .queue_manager import QueueManager
from .models import VideoGenerationResponse, VideoResult

logger = logging.getLogger(__name__)


class VideoGenerationService:
    """
    Service for generating videos using fal.ai veo2 model.
    Supports both text-to-video and image-to-video generation.
    """

    def __init__(self, client: FalClient, queue_mgr: QueueManager):
        """
        Initialize video generation service.

        Args:
            client: FalClient instance
            queue_mgr: QueueManager instance
        """
        self.client = client
        self.queue_mgr = queue_mgr

    async def generate_from_text(
        self,
        prompt: str,
        wait: bool = True,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        fps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate video from text prompt using veo2.

        Args:
            prompt: Text prompt describing the video
            wait: If True, wait for completion; if False, return job info
            duration: Optional video duration in seconds
            aspect_ratio: Optional aspect ratio
            fps: Optional frames per second

        Returns:
            Video generation result or job submission info
        """
        model_id = "veo2"

        payload = {"prompt": prompt}

        if duration:
            payload["duration"] = duration
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        if fps:
            payload["fps"] = fps

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

    async def generate_from_image(
        self,
        prompt: str,
        image_url: str,
        wait: bool = True,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        fps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate video from image + text prompt using veo2.

        Args:
            prompt: Text prompt describing the video
            image_url: URL of the input image
            wait: If True, wait for completion; if False, return job info
            duration: Optional video duration in seconds
            aspect_ratio: Optional aspect ratio
            fps: Optional frames per second

        Returns:
            Video generation result or job submission info
        """
        model_id = "veo2"

        payload = {"prompt": prompt, "image_url": image_url}

        if duration:
            payload["duration"] = duration
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        if fps:
            payload["fps"] = fps

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

    def _parse_video_response(self, result: Dict[str, Any]) -> VideoGenerationResponse:
        """
        Parse raw API response into VideoGenerationResponse.

        Args:
            result: Raw API response

        Returns:
            Parsed video generation response
        """
        video_data = result.get("video", {})

        video_result = VideoResult(
            url=video_data.get("url", ""),
            content_type=video_data.get("content_type"),
            file_name=video_data.get("file_name"),
            file_size=video_data.get("file_size"),
        )

        return VideoGenerationResponse(
            video=video_result, timings=result.get("timings")
        )
