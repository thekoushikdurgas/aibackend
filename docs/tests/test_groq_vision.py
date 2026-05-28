"""
Tests for Groq Vision Service
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.multimodal.groq_vision import GroqVisionService


class TestGroqVisionService:
    """Test GroqVisionService functionality"""

    @pytest.fixture
    def vision_service(self):
        """Create GroqVisionService instance"""
        return GroqVisionService(api_key="test-key")

    def test_initialization(self, vision_service):
        """Test service initialization"""
        assert vision_service.api_key == "test-key"
        assert vision_service.default_model == "llama-3.2-11b-vision-preview"

    def test_prepare_image_bytes(self, vision_service):
        """Test preparing image from bytes"""
        image_bytes = b"fake_image_data"
        result = vision_service._prepare_image(image_bytes)
        assert result.startswith("data:image/jpeg;base64,")

    def test_prepare_image_bytesio(self, vision_service):
        """Test preparing image from BytesIO"""
        from io import BytesIO

        image_io = BytesIO(b"fake_image_data")
        result = vision_service._prepare_image(image_io)
        assert result.startswith("data:image/jpeg;base64,")

    def test_prepare_image_url(self, vision_service):
        """Test preparing image from URL"""
        url = "https://example.com/image.jpg"
        result = vision_service._prepare_image(url)
        assert result == url

    def test_prepare_image_data_url(self, vision_service):
        """Test preparing image from data URL"""
        data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        result = vision_service._prepare_image(data_url)
        assert result == data_url

    @pytest.mark.asyncio
    @patch.object(GroqVisionService, "groq_provider")
    async def test_analyze_image_success(self, mock_provider, vision_service):
        """Test successful image analysis"""
        from app.services.llm.base import LLMResponse

        mock_response = LLMResponse(
            text="This image shows a beautiful sunset over the ocean",
            model="llama-3.2-11b-vision-preview",
            provider="groq",
            usage={"prompt_tokens": 15, "completion_tokens": 12, "total_tokens": 27},
            finish_reason="stop",
            raw_response={},
        )

        mock_provider.generate_with_vision = AsyncMock(return_value=mock_response)

        result = await vision_service.analyze_image(
            image="https://example.com/sunset.jpg", prompt="Describe this image"
        )

        assert result["text"] == "This image shows a beautiful sunset over the ocean"
        assert result["model"] == "llama-3.2-11b-vision-preview"
        assert result["usage"]["total_tokens"] == 27

    @pytest.mark.asyncio
    @patch.object(GroqVisionService, "groq_provider")
    async def test_analyze_multiple_images(self, mock_provider, vision_service):
        """Test analyzing multiple images"""
        from app.services.llm.base import LLMResponse

        mock_response = LLMResponse(
            text="The first image shows a cat, and the second shows a dog",
            model="llama-3.2-11b-vision-preview",
            provider="groq",
            usage={"prompt_tokens": 20, "completion_tokens": 15, "total_tokens": 35},
            finish_reason="stop",
            raw_response={},
        )

        mock_provider.generate_with_vision = AsyncMock(return_value=mock_response)

        result = await vision_service.analyze_multiple_images(
            images=["https://example.com/cat.jpg", "https://example.com/dog.jpg"],
            prompt="What's in these images?",
        )

        assert "cat" in result["text"].lower()
        assert "dog" in result["text"].lower()
        assert result["image_count"] == 2

    @pytest.mark.asyncio
    @patch.object(GroqVisionService, "groq_provider")
    async def test_extract_image_info_description(self, mock_provider, vision_service):
        """Test extracting image description"""
        from app.services.llm.base import LLMResponse

        mock_response = LLMResponse(
            text="A detailed description of the image...",
            model="llama-3.2-11b-vision-preview",
            provider="groq",
            usage={"prompt_tokens": 25, "completion_tokens": 50, "total_tokens": 75},
            finish_reason="stop",
            raw_response={},
        )

        mock_provider.generate_with_vision = AsyncMock(return_value=mock_response)

        result = await vision_service.extract_image_info(
            image="https://example.com/image.jpg", extract_type="description"
        )

        assert result["extract_type"] == "description"
        assert "information" in result
        assert result["model"] == "llama-3.2-11b-vision-preview"

    @pytest.mark.asyncio
    @patch.object(GroqVisionService, "groq_provider")
    async def test_extract_image_info_objects(self, mock_provider, vision_service):
        """Test extracting objects from image"""
        from app.services.llm.base import LLMResponse

        mock_response = LLMResponse(
            text="Objects: car, tree, building, person",
            model="llama-3.2-11b-vision-preview",
            provider="groq",
            usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            finish_reason="stop",
            raw_response={},
        )

        mock_provider.generate_with_vision = AsyncMock(return_value=mock_response)

        result = await vision_service.extract_image_info(
            image="https://example.com/image.jpg", extract_type="objects"
        )

        assert result["extract_type"] == "objects"
        assert "car" in result["information"].lower()

    def test_list_models(self, vision_service):
        """Test listing available vision models"""
        models = vision_service.list_models()
        assert len(models) == 2
        assert "llama-3.2-11b-vision-preview" in models
        assert "llama-3.2-90b-vision-preview" in models

    @pytest.mark.asyncio
    async def test_analyze_image_no_api_key(self):
        """Test that missing API key raises error"""
        service = GroqVisionService(api_key=None)
        with pytest.raises(Exception, match="Groq API key not configured"):
            await service.analyze_image(
                image="https://example.com/image.jpg", prompt="Test"
            )
