"""
Tests for Object Detection service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.multimodal.object_detection import ObjectDetectionService


@pytest.fixture
def mock_hf_client():
    """Mock HuggingFace client"""
    client = AsyncMock()
    client.inference_api_file = AsyncMock(
        return_value=[
            {
                "score": 0.99,
                "label": "sports ball",
                "box": {"xmin": 95, "ymin": 444, "xmax": 172, "ymax": 515},
            },
            {
                "score": 0.85,
                "label": "person",
                "box": {"xmin": 109, "ymin": 14, "xmax": 497, "ymax": 528},
            },
        ]
    )
    return client


@pytest.fixture
def detection_service(mock_hf_client):
    """Object detection service fixture"""
    with patch(
        "app.services.multimodal.object_detection.HuggingFaceClient",
        return_value=mock_hf_client,
    ):
        service = ObjectDetectionService()
        service.client = mock_hf_client
        return service


@pytest.mark.asyncio
async def test_detect_from_bytes(detection_service, mock_hf_client):
    """Test object detection from image bytes"""
    image_data = b"fake image data"
    filename = "test.jpg"

    result = await detection_service.detect(image_data, filename)

    assert len(result) == 2
    assert result[0]["label"] == "sports ball"
    assert result[0]["score"] == 0.99
    mock_hf_client.inference_api_file.assert_called_once()


@pytest.mark.asyncio
async def test_detect_from_url(detection_service, mock_hf_client):
    """Test object detection from image URL"""

    image_url = "https://example.com/image.jpg"

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await detection_service.detect_from_url(image_url)

        assert len(result) == 2
        mock_hf_client.inference_api_file.assert_called_once()


@pytest.mark.asyncio
async def test_detect_from_base64(detection_service, mock_hf_client):
    """Test object detection from base64 image"""
    import base64

    image_data = b"fake image data"
    base64_image = base64.b64encode(image_data).decode("utf-8")

    result = await detection_service.detect_from_base64(base64_image)

    assert len(result) == 2
    mock_hf_client.inference_api_file.assert_called_once()


@pytest.mark.asyncio
async def test_detect_from_base64_with_data_url(detection_service, mock_hf_client):
    """Test object detection from base64 with data URL prefix"""
    import base64

    image_data = b"fake image data"
    base64_image = base64.b64encode(image_data).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{base64_image}"

    result = await detection_service.detect_from_base64(data_url)

    assert len(result) == 2
    mock_hf_client.inference_api_file.assert_called_once()


def test_format_detections(detection_service):
    """Test detection formatting and filtering"""
    detections = [
        {
            "score": 0.99,
            "label": "ball",
            "box": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 100},
        },
        {
            "score": 0.85,
            "label": "person",
            "box": {"xmin": 0, "ymin": 0, "xmax": 200, "ymax": 200},
        },
        {
            "score": 0.3,
            "label": "noise",
            "box": {"xmin": 0, "ymin": 0, "xmax": 50, "ymax": 50},
        },
    ]

    formatted = detection_service.format_detections(detections, min_score=0.5)

    assert len(formatted) == 2  # Only scores >= 0.5
    assert formatted[0]["score"] == 0.99  # Sorted by score descending
    assert formatted[1]["score"] == 0.85


def test_format_detections_empty(detection_service):
    """Test formatting with empty detections"""
    formatted = detection_service.format_detections([], min_score=0.5)
    assert formatted == []


@pytest.mark.asyncio
async def test_detect_custom_model(detection_service, mock_hf_client):
    """Test detection with custom model"""
    image_data = b"fake image data"
    custom_model = "custom/detection-model"

    await detection_service.detect(image_data, "test.jpg", model=custom_model)

    call_args = mock_hf_client.inference_api_file.call_args
    assert call_args[1]["model"] == custom_model
