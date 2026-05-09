"""
Tests for NVIDIA Chat Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.nvidia import NVIDIAChatService
from app.services.llm import LLMConfig


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "id": "test-id",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Test response"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }
    response.headers = {
        "Nvcf-Reqid": "test-req-id",
        "Nvcf-Status": "fulfilled"
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def nvidia_chat_service():
    """Create NVIDIA chat service instance"""
    return NVIDIAChatService(api_key="test_key")


@pytest.mark.asyncio
async def test_nvidia_chat_service_initialization():
    """Test NVIDIA chat service initialization"""
    service = NVIDIAChatService(api_key="test_key")
    assert service.provider_name == "nvidia"
    assert service.client.api_key == "test_key"


@pytest.mark.asyncio
async def test_nvidia_chat_generate(nvidia_chat_service, mock_httpx_response):
    """Test chat completion generation"""
    with patch('app.services.nvidia.client.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_httpx_response)
        
        config = LLMConfig(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            temperature=0.7,
            max_tokens=100
        )
        
        response = await nvidia_chat_service.generate(
            prompt="Hello",
            config=config
        )
        
        assert response.text == "Test response"
        assert response.model == "nvidia/llama-3.3-nemotron-super-49b-v1"
        assert response.provider == "nvidia"
        assert response.usage["total_tokens"] == 30


@pytest.mark.asyncio
async def test_nvidia_chat_stream(nvidia_chat_service):
    """Test streaming chat completion"""
    # Mock streaming response
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_lines = AsyncMock(return_value=iter([
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"content":" World"}}]}',
        'data: [DONE]'
    ]))
    
    with patch('app.services.nvidia.client.httpx.AsyncClient') as mock_client:
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value.stream = AsyncMock(return_value=mock_stream)
        
        config = LLMConfig(model="nvidia/llama-3.3-nemotron-super-49b-v1")
        
        chunks = []
        async for chunk in nvidia_chat_service.stream(prompt="Hello", config=config):
            chunks.append(chunk)
        
        assert len(chunks) > 0


@pytest.mark.asyncio
async def test_nvidia_chat_list_models(nvidia_chat_service):
    """Test listing available models"""
    models = await nvidia_chat_service.list_models()
    assert isinstance(models, list)
    assert len(models) > 0
    assert "nvidia/llama-3.3-nemotron-super-49b-v1" in models


@pytest.mark.asyncio
async def test_nvidia_chat_get_model_info(nvidia_chat_service):
    """Test getting model information"""
    info = await nvidia_chat_service.get_model_info("nvidia/llama-3.3-nemotron-super-49b-v1")
    assert info is not None
    assert info["id"] == "nvidia/llama-3.3-nemotron-super-49b-v1"
    assert "category" in info


@pytest.mark.asyncio
async def test_nvidia_chat_health_check(nvidia_chat_service):
    """Test health check"""
    with patch.object(nvidia_chat_service.client, 'health_check', return_value=True):
        result = await nvidia_chat_service.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_nvidia_chat_with_conversation_history(nvidia_chat_service, mock_httpx_response):
    """Test chat with conversation history"""
    with patch('app.services.nvidia.client.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_httpx_response)
        
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        response = await nvidia_chat_service.generate(
            prompt="What did I say?",
            conversation_history=history
        )
        
        assert response.text == "Test response"


@pytest.mark.asyncio
async def test_nvidia_chat_error_handling(nvidia_chat_service):
    """Test error handling"""
    with patch('app.services.nvidia.client.httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(Exception):
            await nvidia_chat_service.generate(prompt="test")


@pytest.mark.asyncio
async def test_nvidia_chat_reasoning_model(nvidia_chat_service, mock_httpx_response):
    """Test reasoning model support"""
    with patch('app.services.nvidia.client.httpx.AsyncClient') as mock_client:
        mock_httpx_response.json.return_value["choices"][0]["message"]["reasoning_content"] = "Reasoning steps"
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_httpx_response)
        
        config = LLMConfig(model="deepseek-ai/deepseek-r1")
        response = await nvidia_chat_service.generate(prompt="Solve this", config=config)
        
        assert response.text == "Test response"

