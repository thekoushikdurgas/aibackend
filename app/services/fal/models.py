"""
Pydantic models for fal.ai API requests and responses
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    """Job status enumeration"""

    IN_QUEUE = "IN_QUEUE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PROCESSING = "PROCESSING"


# ===================
# Request Models
# ===================


class ImageGenerationRequest(BaseModel):
    """Request for image generation"""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text prompt describing the image",
    )
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    num_images: Optional[int] = Field(
        1, ge=1, le=4, description="Number of images to generate"
    )
    aspect_ratio: Optional[str] = Field(None, description="Image aspect ratio")
    guidance_scale: Optional[float] = Field(
        None, ge=0, le=20, description="Guidance scale"
    )
    num_inference_steps: Optional[int] = Field(
        None, ge=1, le=100, description="Number of inference steps"
    )


class AudioGenerationRequest(BaseModel):
    """Request for audio generation"""

    lyrics: str = Field(
        ..., min_length=1, max_length=50000, description="Lyrics for the song"
    )
    genres: str = Field(
        ..., min_length=1, max_length=500, description="Genre tags (space-separated)"
    )
    duration: Optional[int] = Field(
        None, ge=1, le=300, description="Duration in seconds"
    )
    tempo: Optional[str] = Field(None, description="Tempo (e.g., 'medium', 'fast')")


class VideoGenerationRequest(BaseModel):
    """Request for video generation"""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text prompt describing the video",
    )
    image_url: Optional[HttpUrl] = Field(
        None, description="Image URL for image-to-video generation"
    )
    duration: Optional[int] = Field(
        None, ge=1, le=60, description="Video duration in seconds"
    )
    aspect_ratio: Optional[str] = Field(None, description="Video aspect ratio")
    fps: Optional[int] = Field(None, ge=1, le=60, description="Frames per second")


# ===================
# Response Models
# ===================


class JobSubmissionResponse(BaseModel):
    """Response from job submission"""

    status: JobStatus
    request_id: str
    response_url: str
    status_url: str
    cancel_url: str
    logs: Optional[Any] = None
    metrics: Optional[Dict[str, Any]] = None
    queue_position: Optional[int] = None


class JobStatusResponse(BaseModel):
    """Response from status check"""

    status: JobStatus
    request_id: str
    response_url: str
    status_url: str
    cancel_url: str
    logs: Optional[Any] = None
    metrics: Optional[Dict[str, Any]] = None
    queue_position: Optional[int] = None


class ImageResult(BaseModel):
    """Single image result"""

    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    content_type: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    """Response from image generation"""

    images: List[ImageResult]
    seed: Optional[int] = None
    has_nsfw_concepts: Optional[List[bool]] = None
    prompt: Optional[str] = None
    timings: Optional[Dict[str, Any]] = None


class AudioResult(BaseModel):
    """Audio generation result"""

    url: str
    content_type: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None


class AudioGenerationResponse(BaseModel):
    """Response from audio generation"""

    audio: AudioResult
    timings: Optional[Dict[str, Any]] = None


class VideoResult(BaseModel):
    """Video generation result"""

    url: str
    content_type: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None


class VideoGenerationResponse(BaseModel):
    """Response from video generation"""

    video: VideoResult
    timings: Optional[Dict[str, Any]] = None


class WebhookPayload(BaseModel):
    """Webhook payload from fal.ai"""

    request_id: str
    status: JobStatus
    response_url: Optional[str] = None
    status_url: Optional[str] = None
    error: Optional[str] = None
