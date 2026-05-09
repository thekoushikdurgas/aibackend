"""
Integration tests for NVIDIA API routes
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_nvidia_services():
    """Mock NVIDIA services"""
    with patch('app.services.nvidia.chat.NVIDIAChatService') as mock_chat, \
         patch('app.services.nvidia.embeddings.NVIDIAEmbeddingService') as mock_emb, \
         patch('app.services.nvidia.vision.NVIDIAVisionService') as mock_vision, \
         patch('app.services.nvidia.nim.NVIDIANIMService') as mock_nim:
        
        # Setup mock chat service
        mock_chat_instance = MagicMock()
        mock_chat_instance.generate = AsyncMock(return_value=MagicMock(
            text="Test response",
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            provider="nvidia",
            usage={"total_tokens": 30},
            finish_reason="stop"
        ))
        mock_chat_instance.list_models = AsyncMock(return_value=["nvidia/llama-3.3-nemotron-super-49b-v1"])
        mock_chat_instance.get_model_info = AsyncMock(return_value={
            "id": "nvidia/llama-3.3-nemotron-super-49b-v1",
            "category": "chat"
        })
        mock_chat.return_value = mock_chat_instance
        
        # Setup mock embedding service
        mock_emb_instance = MagicMock()
        mock_emb_instance.embed = AsyncMock(return_value={
            "embeddings": [{"embedding": [0.1] * 768, "index": 0}],
            "model": "nvidia/nv-embedqa-e5-v5",
            "usage": {"total_tokens": 5}
        })
        mock_emb_instance.list_models = AsyncMock(return_value=["nvidia/nv-embedqa-e5-v5"])
        mock_emb.return_value = mock_emb_instance
        
        # Setup mock vision service
        mock_vision_instance = MagicMock()
        mock_vision_instance.analyze = AsyncMock(return_value={
            "text": "This is a cat",
            "model": "meta/llama-3.2-90b-vision-instruct",
            "usage": {"total_tokens": 60}
        })
        mock_vision_instance.list_models = AsyncMock(return_value=["meta/llama-3.2-90b-vision-instruct"])
        mock_vision.return_value = mock_vision_instance
        
        # Setup mock NIM service
        mock_nim_instance = MagicMock()
        mock_nim_instance.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_nim_instance.list_models = AsyncMock(return_value=[{"id": "model1"}])
        mock_nim.return_value = mock_nim_instance
        
        yield {
            "chat": mock_chat_instance,
            "embeddings": mock_emb_instance,
            "vision": mock_vision_instance,
            "nim": mock_nim_instance
        }


@pytest.mark.asyncio
async def test_nvidia_chat_completions_endpoint(mock_nvidia_services):
    """Test NVIDIA chat completions endpoint"""
    response = client.post(
        "/api/v1/nvidia/chat/completions",
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "nvidia/llama-3.3-nemotron-super-49b-v1"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert data["model"] == "nvidia/llama-3.3-nemotron-super-49b-v1"


@pytest.mark.asyncio
async def test_nvidia_chat_list_models_endpoint(mock_nvidia_services):
    """Test NVIDIA list models endpoint"""
    response = client.get("/api/v1/nvidia/chat/models")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0


@pytest.mark.asyncio
async def test_nvidia_embeddings_endpoint(mock_nvidia_services):
    """Test NVIDIA embeddings endpoint"""
    response = client.post(
        "/api/v1/nvidia/embeddings",
        json={
            "input": "Hello world",
            "model": "nvidia/nv-embedqa-e5-v5"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "model" in data


@pytest.mark.asyncio
async def test_nvidia_vision_analyze_endpoint(mock_nvidia_services):
    """Test NVIDIA vision analyze endpoint"""
    response = client.post(
        "/api/v1/nvidia/vision/analyze",
        json={
            "prompt": "What is in this image?",
            "image_url": "https://example.com/image.jpg"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "model" in data


@pytest.mark.asyncio
async def test_nvidia_nim_health_endpoint(mock_nvidia_services):
    """Test NVIDIA NIM health endpoint"""
    response = client.get("/api/v1/nvidia/nim/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_nvidia_integrated_chat_route(mock_nvidia_services):
    """Test NVIDIA through integrated chat route"""
    with patch('app.services.llm.factory.LLMProviderFactory.get_provider') as mock_get_provider:
        mock_get_provider.return_value = mock_nvidia_services["chat"]
        
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Hello",
                "provider": "nvidia",
                "model": "nvidia/llama-3.3-nemotron-super-49b-v1"
            }
        )
        
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_nvidia_integrated_embeddings_route(mock_nvidia_services):
    """Test NVIDIA through integrated embeddings route"""
    response = client.post(
        "/api/v1/embeddings/nvidia",
        json={
            "input": "Hello world",
            "model": "nvidia/nv-embedqa-e5-v5"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_nvidia_integrated_vision_route(mock_nvidia_services):
    """Test NVIDIA through integrated vision route"""
    response = client.post(
        "/api/v1/vision/nvidia",
        json={
            "prompt": "What is this?",
            "image_url": "https://example.com/image.jpg"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "text" in data

