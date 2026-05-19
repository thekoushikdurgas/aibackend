"""
Tests for NVIDIA NIM Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.nvidia import NVIDIANIMService


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"status": "healthy"}
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def nvidia_nim_service():
    """Create NVIDIA NIM service instance"""
    return NVIDIANIMService(
        api_key="test_key", nim_base_url="https://nim.example.com/v1"
    )


@pytest.mark.asyncio
async def test_nvidia_nim_service_initialization():
    """Test NVIDIA NIM service initialization"""
    service = NVIDIANIMService(
        api_key="test_key", nim_base_url="https://nim.example.com/v1"
    )
    assert service.client.api_key == "test_key"
    assert service.client.nim_base_url == "https://nim.example.com/v1"


@pytest.mark.asyncio
async def test_nvidia_nim_health_check(nvidia_nim_service, mock_httpx_response):
    """Test NIM health check"""
    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_httpx_response
        )

        result = await nvidia_nim_service.health_check()

        assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_nvidia_nim_list_models(nvidia_nim_service):
    """Test listing deployed models"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "model1", "name": "Model 1"},
            {"id": "model2", "name": "Model 2"},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        models = await nvidia_nim_service.list_models()

        assert isinstance(models, list)
        assert len(models) == 2


@pytest.mark.asyncio
async def test_nvidia_nim_get_model_info(nvidia_nim_service):
    """Test getting model information"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "model1",
        "name": "Test Model",
        "status": "ready",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        info = await nvidia_nim_service.get_model_info("model1")

        assert info is not None
        assert info["id"] == "model1"


@pytest.mark.asyncio
async def test_nvidia_nim_infer(nvidia_nim_service):
    """Test NIM inference"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "test-id",
        "model": "model1",
        "choices": [{"message": {"content": "Response"}}],
        "usage": {"total_tokens": 10},
    }
    mock_response.headers = {"Nvcf-Reqid": "test-req-id"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        messages = [{"role": "user", "content": "Hello"}]
        result = await nvidia_nim_service.infer(model_id="model1", messages=messages)

        assert "choices" in result
        assert result["model"] == "model1"


@pytest.mark.asyncio
async def test_nvidia_nim_get_metrics(nvidia_nim_service):
    """Test getting deployment metrics"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "requests_per_second": 10,
        "average_latency": 0.5,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        metrics = await nvidia_nim_service.get_metrics()

        assert "requests_per_second" in metrics


@pytest.mark.asyncio
async def test_nvidia_nim_error_no_base_url():
    """Test error when NIM base URL not configured"""
    service = NVIDIANIMService(api_key="test_key")

    with pytest.raises(ValueError, match="NIM base URL not configured"):
        await service.health_check()
