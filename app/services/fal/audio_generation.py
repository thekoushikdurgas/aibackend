"""
Audio generation service for fal.ai yue model
"""

import logging
from typing import Any, Dict, Optional

from .client import FalClient
from .queue_manager import QueueManager
from .models import AudioGenerationResponse, AudioResult

logger = logging.getLogger(__name__)


class AudioGenerationService:
    """
    Service for generating audio/music using fal.ai yue model.
    """

    def __init__(self, client: FalClient, queue_mgr: QueueManager):
        """
        Initialize audio generation service.

        Args:
            client: FalClient instance
            queue_mgr: QueueManager instance
        """
        self.client = client
        self.queue_mgr = queue_mgr

    async def generate_music(
        self,
        lyrics: str,
        genres: str,
        wait: bool = True,
        duration: Optional[int] = None,
        tempo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate music/audio from lyrics using yue model.

        Args:
            lyrics: Song lyrics with verse/chorus markers
            genres: Space-separated genre tags
            wait: If True, wait for completion; if False, return job info
            duration: Optional duration in seconds
            tempo: Optional tempo specification

        Returns:
            Audio generation result or job submission info
        """
        model_id = "yue"

        payload = {"lyrics": lyrics, "genres": genres}

        if duration:
            payload["duration"] = duration
        if tempo:
            payload["tempo"] = tempo

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

    def _parse_audio_response(self, result: Dict[str, Any]) -> AudioGenerationResponse:
        """
        Parse raw API response into AudioGenerationResponse.

        Args:
            result: Raw API response

        Returns:
            Parsed audio generation response
        """
        audio_data = result.get("audio", {})

        audio_result = AudioResult(
            url=audio_data.get("url", ""),
            content_type=audio_data.get("content_type"),
            file_name=audio_data.get("file_name"),
            file_size=audio_data.get("file_size"),
        )

        return AudioGenerationResponse(
            audio=audio_result, timings=result.get("timings")
        )
