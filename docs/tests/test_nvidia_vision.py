"""
Tests for NVIDIA Vision Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.nvidia import NVIDIAVisionService


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "id": "test-id",
        "object": "chat.completion",
        "model": "meta/llama-3.2-90b-vision-instruct",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a test image showing a cat."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 10,
            "total_tokens": 60
        }
    }
    response.headers = {
        "Nvcf-Reqid": "test-req-id",
        "Nvcf-Status": "fulfilled"
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def nvidia_vision_service():
    """Create NVIDIA vision service instance"""
    return NVIDIAVisionService(api_key="test_key")


@pytest.mark.asyncio
async def test_nvidia_vision_service_initialization():
    """Test NVIDIA vision service initialization"""
    service = NVIDIAVisionService(api_key="test_key")
    assert service.client.api_key == "test_key"


@pytest.mark.asyncio
async def test_nvidia_vision_analyze_with_image_url(nvidia_vision_service, mock_httpx_response):
    """Test image analysis with URL"""
    with patch('app.services.nvidia.client.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_httpx_response)
        
        result = await nvidia_vision_service.analyze(
            prompt="What is in this image?",
            image_url="https://example.com/image.jpg"
        )
        
        assert result["text"] == "This is a test image showing a cat."
        assert result["model"] == "meta/llama-3.2-90b-vision-instruct"


@pytest.mark.asyncio
async def test_nvidia_vision_analyze_with_base64(nvidia_vision_service, mock_httpx_response):
    """Test image analysis with base64 image"""
    with patch('app.services.nvidia.client.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_httpx_response)
        
        base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        result = await nvidia_vision_service.analyze(
            prompt="Describe this image",
            image=base64_image
        )
        
        assert "text" in result
        assert result["model"] == "meta/llama-3.2-90b-vision-instruct"


@pytest.mark.asyncio
async def test_nvidia_vision_analyze_multimodal(nvidia_vision_service, mock_httpx_response):
    """Test multimodal analysis with multiple images"""
    with patch('app.services.nvidia.client.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_httpx_response)
        
        images = ["base64_image_1", "base64_image_2"]
        result = await nvidia_vision_service.analyze_multimodal(
            prompt="Compare these images",
            images=images
        )
        
        assert "text" in result


@pytest.mark.asyncio
async def test_nvidia_vision_analyze_video_frames(nvidia_vision_service, mock_httpx_response):
    """Test video frame analysis"""
    with patch('app.services.nvidia.client.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_httpx_response)
        
        frames = ["frame1", "frame2", "frame3"]
        result = await nvidia_vision_service.analyze_video_frames(
            prompt="What happens in this video?",
            frames=frames
        )
        
        assert "text" in result


@pytest.mark.asyncio
async def test_nvidia_vision_error_no_image(nvidia_vision_service):
    """Test error when no image provided"""
    with pytest.raises(ValueError, match="Either image or image_url"):
        await nvidia_vision_service.analyze(prompt="Test")


@pytest.mark.asyncio
async def test_nvidia_vision_list_models(nvidia_vision_service):
    """Test listing vision models"""
    models = await nvidia_vision_service.list_models()
    assert isinstance(models, list)
    assert len(models) > 0
    assert "meta/llama-3.2-90b-vision-instruct" in models


@pytest.mark.asyncio
async def test_nvidia_vision_get_model_info(nvidia_vision_service):
    """Test getting vision model information"""
    info = await nvidia_vision_service.get_model_info("meta/llama-3.2-90b-vision-instruct")
    assert info is not None
    assert info["id"] == "meta/llama-3.2-90b-vision-instruct"
    assert info.get("vision") is True


@pytest.mark.asyncio
async def test_nvidia_vision_health_check(nvidia_vision_service):
    """Test health check"""
    with patch.object(nvidia_vision_service.client, 'health_check', return_value=True):
        result = await nvidia_vision_service.health_check()
        assert result is True

