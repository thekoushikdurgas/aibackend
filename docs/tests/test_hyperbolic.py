"""
Tests for Hyperbolic API integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.hyperbolic import (
    HyperbolicClient,
    HyperbolicTextService,
    HyperbolicVisionService,
    HyperbolicAudioService,
    HyperbolicImageService,
    TEXT_MODELS,
    VISION_MODELS,
    IMAGE_MODELS,
    AUDIO_MODELS
)
from app.services.llm.hyperbolic import HyperbolicProvider


@pytest.fixture
def mock_client():
    """Mock Hyperbolic client"""
    client = MagicMock(spec=HyperbolicClient)
    client.post = AsyncMock()
    client.post_stream = AsyncMock()
    client.health_check = AsyncMock(return_value=True)
    return client


@pytest.fixture
def hyperbolic_provider():
    """Create Hyperbolic provider instance"""
    with patch('app.services.llm.hyperbolic.HyperbolicClient'):
        provider = HyperbolicProvider(api_key="test-key")
        return provider


class TestHyperbolicClient:
    """Tests for HyperbolicClient"""
    
    @pytest.mark.asyncio
    async def test_post_request(self, mock_client):
        """Test POST request handling"""
        mock_client.post.return_value = {"id": "test", "choices": []}
        
        result = await mock_client.post("/chat/completions", {"test": "data"})
        
        assert result == {"id": "test", "choices": []}
        mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check"""
        with patch('app.services.hyperbolic.client.HyperbolicClient.post') as mock_post:
            mock_post.return_value = {"choices": [{"message": {"content": "test"}}]}
            
            client = HyperbolicClient(api_key="test-key")
            result = await client.health_check()
            
            assert result is True


class TestHyperbolicTextService:
    """Tests for HyperbolicTextService"""
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, mock_client):
        """Test chat completion"""
        mock_response = {
            "id": "chat-123",
            "choices": [{
                "message": {"content": "Hello, world!"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        mock_client.post.return_value = mock_response
        
        service = HyperbolicTextService(client=mock_client)
        result = await service.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="meta-llama/Meta-Llama-3.1-70B-Instruct"
        )
        
        assert result == mock_response
        mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stream_completion(self, mock_client):
        """Test streaming completion"""
        mock_response = MagicMock()
        mock_response.aiter_text = AsyncMock(return_value=iter([
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
            'data: [DONE]\n\n'
        ]))
        mock_client.post_stream.return_value = mock_response
        
        service = HyperbolicTextService(client=mock_client)
        chunks = []
        async for chunk in await service.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="meta-llama/Meta-Llama-3.1-70B-Instruct",
            stream=True
        ):
            chunks.append(chunk)
        
        assert len(chunks) > 0


class TestHyperbolicVisionService:
    """Tests for HyperbolicVisionService"""
    
    @pytest.mark.asyncio
    async def test_vision_completion(self, mock_client):
        """Test vision completion"""
        mock_response = {
            "id": "vision-123",
            "choices": [{
                "message": {"content": "This is an image of a cat."},
                "finish_reason": "stop"
            }]
        }
        mock_client.post.return_value = mock_response
        
        service = HyperbolicVisionService(client=mock_client)
        result = await service.vision_completion(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is this?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
                ]
            }],
            model="meta-llama/Llama-3.2-90B-Vision-Instruct"
        )
        
        assert result == mock_response
    
    def test_prepare_multimodal_message(self, mock_client):
        """Test multimodal message preparation"""
        service = HyperbolicVisionService(client=mock_client)
        message = service.prepare_multimodal_message(
            text="What is this?",
            image_urls=["https://example.com/image.jpg"]
        )
        
        assert message["role"] == "user"
        assert isinstance(message["content"], list)
        assert message["content"][0]["type"] == "text"
        assert message["content"][1]["type"] == "image_url"


class TestHyperbolicAudioService:
    """Tests for HyperbolicAudioService"""
    
    @pytest.mark.asyncio
    async def test_generate_audio(self, mock_client):
        """Test audio generation"""
        mock_audio_data = b"fake audio data"
        
        with patch('app.services.hyperbolic.audio.httpx.AsyncClient') as mock_httpx:
            mock_response = MagicMock()
            mock_response.content = mock_audio_data
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__.return_value = mock_client_instance
            
            service = HyperbolicAudioService(client=mock_client)
            result = await service.generate_audio(text="Hello, world!", speed=1.0)
            
            assert result == mock_audio_data


class TestHyperbolicImageService:
    """Tests for HyperbolicImageService"""
    
    @pytest.mark.asyncio
    async def test_generate_image(self, mock_client):
        """Test image generation"""
        mock_response = {
            "image": "base64_encoded_image_data",
            "model": "FLUX.1-dev"
        }
        mock_client.post.return_value = mock_response
        
        service = HyperbolicImageService(client=mock_client)
        result = await service.generate_image(
            prompt="A beautiful sunset",
            model_name="FLUX.1-dev",
            steps=30,
            cfg_scale=5.0,
            height=1024,
            width=1024
        )
        
        assert result == mock_response
        mock_client.post.assert_called_once()


class TestHyperbolicProvider:
    """Tests for HyperbolicProvider"""
    
    @pytest.mark.asyncio
    async def test_generate(self, hyperbolic_provider):
        """Test text generation"""
        with patch.object(hyperbolic_provider.client, 'post') as mock_post:
            mock_post.return_value = {
                "choices": [{
                    "message": {"content": "Hello, world!"},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15
                }
            }
            
            from app.services.llm.base import LLMConfig
            config = LLMConfig(model="meta-llama/Meta-Llama-3.1-70B-Instruct")
            
            response = await hyperbolic_provider.generate(
                prompt="Hello",
                config=config
            )
            
            assert response.text == "Hello, world!"
            assert response.model == "meta-llama/Meta-Llama-3.1-70B-Instruct"
            assert response.provider == "hyperbolic"
    
    @pytest.mark.asyncio
    async def test_stream(self, hyperbolic_provider):
        """Test streaming generation"""
        mock_response = MagicMock()
        mock_response.aiter_text = AsyncMock(return_value=iter([
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            'data: [DONE]\n\n'
        ]))
        
        with patch.object(hyperbolic_provider.client, 'post_stream', return_value=mock_response):
            chunks = []
            async for chunk in hyperbolic_provider.stream("Hello"):
                chunks.append(chunk)
            
            assert len(chunks) > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, hyperbolic_provider):
        """Test health check"""
        with patch.object(hyperbolic_provider.client, 'health_check', return_value=True):
            result = await hyperbolic_provider.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_list_models(self, hyperbolic_provider):
        """Test model listing"""
        models = await hyperbolic_provider.list_models()
        assert len(models) > 0
        assert isinstance(models, list)


class TestModelRegistry:
    """Tests for model registry"""
    
    def test_text_models_list(self):
        """Test text models list"""
        assert len(TEXT_MODELS) == 12
        assert "meta-llama/Meta-Llama-3.1-70B-Instruct" in TEXT_MODELS
        assert "deepseek-ai/DeepSeek-V3" in TEXT_MODELS
    
    def test_vision_models_list(self):
        """Test vision models list"""
        assert len(VISION_MODELS) == 4
        assert "meta-llama/Llama-3.2-90B-Vision-Instruct" in VISION_MODELS
    
    def test_image_models_list(self):
        """Test image models list"""
        assert len(IMAGE_MODELS) == 6
        assert "FLUX.1-dev" in IMAGE_MODELS
        assert "SD1.5" in IMAGE_MODELS
    
    def test_audio_models_list(self):
        """Test audio models list"""
        assert len(AUDIO_MODELS) == 1
        assert "Melo TTS" in AUDIO_MODELS


class TestIntegration:
    """Integration tests (require API key)"""
    
    @pytest.mark.skip(reason="Requires API key")
    @pytest.mark.asyncio
    async def test_real_chat_completion(self):
        """Test real chat completion (requires API key)"""
        from app.config import settings
        
        if not settings.hyperbolic_api_key:
            pytest.skip("No API key configured")
        
        service = HyperbolicTextService()
        result = await service.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="meta-llama/Meta-Llama-3.1-70B-Instruct",
            max_tokens=10
        )
        
        assert "choices" in result
        assert len(result["choices"]) > 0

