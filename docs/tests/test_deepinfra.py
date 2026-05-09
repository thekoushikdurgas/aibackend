"""
Comprehensive tests for Deep Infra provider and services
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64

from app.services.llm.deepinfra import DeepInfraProvider
from app.services.image.deepinfra_image import DeepInfraImageGenerator
from app.services.llm.base import LLMConfig


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response for chat completions"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "google/gemma-7b-it",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "Test response"},
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_completion_response():
    """Mock httpx response for text completions"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "id": "cmpl-test",
        "object": "text_completion",
        "created": 1234567890,
        "model": "google/gemma-7b-it",
        "choices": [{
            "index": 0,
            "text": "Generated text completion",
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 10,
            "total_tokens": 15
        }
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_embedding_response():
    """Mock httpx response for embeddings"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "object": "list",
        "data": [{
            "object": "embedding",
            "index": 0,
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
        }],
        "model": "thenlper/gte-large",
        "usage": {
            "prompt_tokens": 5,
            "total_tokens": 5
        }
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_image_response():
    """Mock httpx response for image generation"""
    response = MagicMock()
    response.status_code = 200
    response.content = b"fake_image_bytes"
    response.headers = {"content-type": "image/png"}
    response.raise_for_status = MagicMock()
    return response


class TestDeepInfraProvider:
    """Tests for DeepInfraProvider"""
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self):
        """Test provider initialization"""
        provider = DeepInfraProvider(api_key="test_key")
        assert provider.provider_name == "deepinfra"
        assert provider.api_key == "test_key"
        assert provider.base_url == "https://api.deepinfra.com/v1/openai"
        assert provider.inference_base_url == "https://api.deepinfra.com/v1"
    
    @pytest.mark.asyncio
    async def test_generate_chat_completion(self, mock_httpx_response):
        """Test chat completion generation"""
        provider = DeepInfraProvider(api_key="test_key")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response
            )
            
            response = await provider.generate(
                prompt="Test prompt",
                config=LLMConfig(model="google/gemma-7b-it")
            )
            
            assert response.text == "Test response"
            assert response.model == "google/gemma-7b-it"
            assert response.provider == "deepinfra"
            assert response.usage["total_tokens"] == 30
    
    @pytest.mark.asyncio
    async def test_complete_text_completion(self, mock_completion_response):
        """Test text completion endpoint"""
        provider = DeepInfraProvider(api_key="test_key")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_completion_response
            )
            
            response = await provider.complete(
                prompt="Write a limerick",
                config=LLMConfig(model="google/gemma-7b-it")
            )
            
            assert "Generated text completion" in response.text
            assert response.model == "google/gemma-7b-it"
            assert response.usage["total_tokens"] == 15
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_single(self, mock_embedding_response):
        """Test single text embedding generation"""
        provider = DeepInfraProvider(api_key="test_key")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_embedding_response
            )
            
            result = await provider.generate_embeddings(
                text="Test text",
                model="thenlper/gte-large"
            )
            
            assert len(result["embeddings"]) == 1
            assert len(result["embeddings"][0]) == 5
            assert result["model"] == "thenlper/gte-large"
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, mock_embedding_response):
        """Test batch embedding generation"""
        provider = DeepInfraProvider(api_key="test_key")
        
        # Mock response with multiple embeddings
        mock_embedding_response.json.return_value = {
            "object": "list",
            "data": [
                {"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3]},
                {"object": "embedding", "index": 1, "embedding": [0.4, 0.5, 0.6]}
            ],
            "model": "thenlper/gte-large",
            "usage": {"prompt_tokens": 10, "total_tokens": 10}
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_embedding_response
            )
            
            result = await provider.generate_embeddings(
                text=["Text 1", "Text 2"],
                model="thenlper/gte-large"
            )
            
            assert len(result["embeddings"]) == 2
    
    @pytest.mark.asyncio
    async def test_direct_inference_text(self):
        """Test direct inference for text models"""
        provider = DeepInfraProvider(api_key="test_key")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"generated_text": "Inference result"}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await provider.inference(
                model_path="bigcode/starcoder",
                input_data={"input": "def hello():"}
            )
            
            assert "data" in result
            assert result["model"] == "bigcode/starcoder"
    
    @pytest.mark.asyncio
    async def test_direct_inference_image(self, mock_image_response):
        """Test direct inference for image models"""
        provider = DeepInfraProvider(api_key="test_key")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_image_response
            )
            
            result = await provider.inference(
                model_path="black-forest-labs/FLUX-1-dev",
                input_data={"prompt": "A beautiful sunset"}
            )
            
            assert "image" in result
            assert result["content_type"] == "image/png"
    
    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test model listing"""
        provider = DeepInfraProvider(api_key="test_key")
        models = await provider.list_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "google/gemma-7b-it" in models
    
    @pytest.mark.asyncio
    async def test_get_completion_models(self):
        """Test completion models list"""
        provider = DeepInfraProvider(api_key="test_key")
        models = provider.get_completion_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
    
    @pytest.mark.asyncio
    async def test_get_embedding_models(self):
        """Test embedding models list"""
        provider = DeepInfraProvider(api_key="test_key")
        models = provider.get_embedding_models()
        
        assert isinstance(models, list)
        assert "thenlper/gte-large" in models
    
    @pytest.mark.asyncio
    async def test_get_inference_models(self):
        """Test inference models list"""
        provider = DeepInfraProvider(api_key="test_key")
        models = provider.get_inference_models()
        
        assert "text" in models
        assert "image" in models
        assert "black-forest-labs/FLUX-1-dev" in models["image"]
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_httpx_response):
        """Test successful health check"""
        provider = DeepInfraProvider(api_key="test_key")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_httpx_response
            )
            
            is_healthy = await provider.health_check()
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self):
        """Test health check without API key"""
        provider = DeepInfraProvider(api_key=None)
        is_healthy = await provider.health_check()
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling"""
        provider = DeepInfraProvider(api_key="test_key")
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {"message": "Invalid API key"}
        }
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(Exception) as exc_info:
                await provider.generate(
                    prompt="Test",
                    config=LLMConfig()
                )
            
            assert "API key" in str(exc_info.value) or "error" in str(exc_info.value).lower()


class TestDeepInfraImageGenerator:
    """Tests for DeepInfraImageGenerator"""
    
    @pytest.mark.asyncio
    async def test_image_generator_initialization(self):
        """Test image generator initialization"""
        generator = DeepInfraImageGenerator(api_key="test_key")
        assert generator.api_key == "test_key"
        assert generator.default_model == "black-forest-labs/FLUX-1-schnell"
        assert generator.inference_base_url == "https://api.deepinfra.com/v1"
    
    @pytest.mark.asyncio
    async def test_generate_image(self, mock_image_response):
        """Test image generation"""
        generator = DeepInfraImageGenerator(api_key="test_key")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_image_response
            )
            
            result = await generator.generate_image(
                prompt="A beautiful sunset",
                return_base64=True
            )
            
            assert "image" in result
            assert result["model"] == "black-forest-labs/FLUX-1-schnell"
            assert result["format"] == "base64"
    
    @pytest.mark.asyncio
    async def test_generate_image_bytes(self, mock_image_response):
        """Test image generation returning bytes"""
        generator = DeepInfraImageGenerator(api_key="test_key")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_image_response
            )
            
            image_bytes = await generator.generate_image_bytes(
                prompt="A beautiful sunset"
            )
            
            assert isinstance(image_bytes, bytes)
            assert image_bytes == b"fake_image_bytes"
    
    @pytest.mark.asyncio
    async def test_generate_image_base64(self, mock_image_response):
        """Test image generation returning base64"""
        generator = DeepInfraImageGenerator(api_key="test_key")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_image_response
            )
            
            base64_str = await generator.generate_image_base64(
                prompt="A beautiful sunset"
            )
            
            assert isinstance(base64_str, str)
            # Verify it's valid base64
            decoded = base64.b64decode(base64_str)
            assert decoded == b"fake_image_bytes"
    
    @pytest.mark.asyncio
    async def test_get_available_models(self):
        """Test getting available image models"""
        generator = DeepInfraImageGenerator(api_key="test_key")
        models = generator.get_available_models()
        
        assert isinstance(models, dict)
        assert "black-forest-labs/FLUX-1-dev" in models
        assert "black-forest-labs/FLUX-1-schnell" in models
        assert "stabilityai/sdxl-turbo" in models
        
        # Check model metadata
        flux_dev = models["black-forest-labs/FLUX-1-dev"]
        assert "description" in flux_dev
        assert "recommended_steps" in flux_dev
    
    @pytest.mark.asyncio
    async def test_generate_with_parameters(self, mock_image_response):
        """Test image generation with all parameters"""
        generator = DeepInfraImageGenerator(api_key="test_key")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_image_response
            )
            
            result = await generator.generate_image(
                prompt="A beautiful sunset",
                model="black-forest-labs/FLUX-1-dev",
                negative_prompt="blurry, low quality",
                num_inference_steps=50,
                guidance_scale=3.5,
                seed=42,
                return_base64=True
            )
            
            assert result["model"] == "black-forest-labs/FLUX-1-dev"
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in image generation"""
        generator = DeepInfraImageGenerator(api_key="test_key")
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Invalid prompt"}
        }
        mock_response.raise_for_status.side_effect = Exception("400 Bad Request")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(Exception):
                await generator.generate_image(prompt="")
