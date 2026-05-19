"""
Service tests for DurgasAI Backend
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.base import LLMConfig
from app.services.llm.factory import LLMProviderFactory
from app.services.llm.ai21 import AI21Provider
from app.services.memory.conversation import ConversationMemory
from app.utils.html_parser import HTMLParser
from app.utils.helpers import (
    generate_id,
    sanitize_text,
    truncate_text,
    extract_keywords,
)


class TestLLMProviderFactory:
    """Tests for LLM Provider Factory"""

    def test_list_providers(self):
        """Test listing available providers"""
        providers = LLMProviderFactory.list_providers()
        assert "ollama" in providers
        assert "huggingface" in providers
        assert "gemini" in providers
        assert "ai21" in providers

    def test_get_provider(self):
        """Test getting a provider"""
        provider = LLMProviderFactory.get_provider("ollama")
        assert provider is not None
        assert provider.provider_name == "ollama"

    def test_get_provider_invalid(self):
        """Test getting invalid provider raises error"""
        with pytest.raises(ValueError):
            LLMProviderFactory.get_provider("invalid_provider")

    def test_clear_cache(self):
        """Test clearing provider cache"""
        # Get a provider to populate cache
        LLMProviderFactory.get_provider("ollama")
        LLMProviderFactory.clear_cache()
        assert len(LLMProviderFactory._instances) == 0


class TestLLMConfig:
    """Tests for LLMConfig"""

    def test_default_config(self):
        """Test default configuration values"""
        config = LLMConfig()
        assert config.model == "llama3"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048

    def test_custom_config(self):
        """Test custom configuration"""
        config = LLMConfig(model="mistral", temperature=0.5, max_tokens=1024)
        assert config.model == "mistral"
        assert config.temperature == 0.5


class TestConversationMemory:
    """Tests for Conversation Memory"""

    @pytest.fixture
    def memory(self):
        """Fresh memory instance"""
        return ConversationMemory()

    def test_create_conversation(self, memory):
        """Test creating a new conversation"""
        conv = memory.create_conversation("test_123")
        assert conv.id == "test_123"
        assert len(conv.messages) == 0

    def test_add_message(self, memory):
        """Test adding messages to conversation"""
        conv = memory.add_message("test_123", "user", "Hello")
        assert len(conv.messages) == 1
        assert conv.messages[0].role == "user"
        assert conv.messages[0].content == "Hello"

    def test_get_history(self, memory):
        """Test getting conversation history"""
        memory.add_message("test_123", "user", "Hello")
        memory.add_message("test_123", "assistant", "Hi there!")

        history = memory.get_history("test_123")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_delete_conversation(self, memory):
        """Test deleting conversation"""
        memory.create_conversation("to_delete")
        deleted = memory.delete_conversation("to_delete")
        assert deleted is True
        assert memory.get_conversation("to_delete") is None

    def test_max_messages_limit(self, memory):
        """Test that old messages are trimmed"""
        memory.max_messages = 5
        for i in range(10):
            memory.add_message("test_limit", "user", f"Message {i}")

        conv = memory.get_conversation("test_limit")
        assert len(conv.messages) == 5


class TestHTMLParser:
    """Tests for HTML Parser"""

    @pytest.fixture
    def parser(self):
        """Parser with test HTML"""
        html = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
            </head>
            <body>
                <header><nav>Nav</nav></header>
                <main>
                    <h1>Main Title</h1>
                    <h2>Subtitle</h2>
                    <p>Paragraph content here.</p>
                    <img src="test.jpg" alt="Test image">
                    <img src="noalt.jpg">
                    <a href="/link1">Link 1</a>
                </main>
                <footer>Footer</footer>
            </body>
        </html>
        """
        return HTMLParser(html)

    def test_get_title(self, parser):
        """Test extracting title"""
        assert parser.get_title() == "Test Page"

    def test_get_meta_description(self, parser):
        """Test extracting meta description"""
        assert parser.get_meta_description() == "Test description"

    def test_get_headings(self, parser):
        """Test extracting headings"""
        headings = parser.get_headings()
        assert len(headings["h1"]) == 1
        assert headings["h1"][0] == "Main Title"
        assert len(headings["h2"]) == 1

    def test_get_images(self, parser):
        """Test extracting images"""
        images = parser.get_images()
        assert len(images) == 2
        assert images[0]["has_alt"] is True
        assert images[1]["has_alt"] is False

    def test_get_semantic_elements(self, parser):
        """Test detecting semantic elements"""
        semantic = parser.get_semantic_elements()
        assert semantic["has_header"] is True
        assert semantic["has_nav"] is True
        assert semantic["has_main"] is True
        assert semantic["has_footer"] is True

    def test_analyze_images_seo(self, parser):
        """Test image SEO analysis"""
        analysis = parser.analyze_images_seo()
        assert analysis["total_images"] == 2
        assert analysis["images_with_alt"] == 1
        assert analysis["images_without_alt"] == 1
        assert analysis["alt_coverage_percent"] == 50.0


class TestAI21Provider:
    """Tests for AI21 Provider"""

    @pytest.fixture
    def provider(self):
        """AI21 provider instance with mocked API key"""
        with patch("app.services.llm.ai21.settings") as mock_settings:
            mock_settings.ai21_api_key = "test_api_key"
            mock_settings.ai21_model = "jamba-large-1.7"
            mock_settings.ai21_base_url = "https://api.ai21.com/studio/v1"
            return AI21Provider()

    def test_provider_name(self, provider):
        """Test provider name"""
        assert provider.provider_name == "ai21"

    def test_default_model(self, provider):
        """Test default model"""
        assert provider.default_model == "jamba-large-1.7"

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation"""
        mock_response = {
            "id": "chatcmpl-test",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Test response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.raise_for_status = AsyncMock()
            mock_post.json = MagicMock(return_value=mock_response)

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.post = AsyncMock(return_value=mock_post)
            mock_client.return_value = mock_client_instance

            response = await provider.generate("Test prompt")

            assert response.text == "Test response"
            assert response.model == "jamba-large-1.7"
            assert response.provider == "ai21"
            assert response.usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_generate_no_api_key(self):
        """Test generation without API key raises error"""
        with patch("app.services.llm.ai21.settings") as mock_settings:
            mock_settings.ai21_api_key = None
            provider = AI21Provider()

            with pytest.raises(Exception, match="AI21 API key not configured"):
                await provider.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_stream_success(self, provider):
        """Test successful streaming"""
        mock_chunks = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":" World"}}]}\n\n',
            "data: [DONE]\n\n",
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_stream = AsyncMock()
            mock_stream.raise_for_status = AsyncMock()
            mock_stream.aiter_text = AsyncMock(return_value=iter(mock_chunks))

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.stream = AsyncMock(return_value=mock_stream)
            mock_client.return_value = mock_client_instance

            chunks = []
            async for chunk in provider.stream("Test prompt"):
                chunks.append(chunk)

            assert "Hello" in chunks
            assert " World" in chunks

    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        """Test successful health check"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.post = mock_post
            mock_client.return_value = mock_client_instance

            result = await provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self):
        """Test health check without API key"""
        with patch("app.services.llm.ai21.settings") as mock_settings:
            mock_settings.ai21_api_key = None
            provider = AI21Provider()

            result = await provider.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_list_models(self, provider):
        """Test listing available models"""
        models = await provider.list_models()
        assert "jamba-large-1.7" in models
        assert "jamba-mini-1.7" in models

    def test_build_messages(self, provider):
        """Test message building"""
        messages = provider._build_messages(
            prompt="Hello",
            context="Context here",
            conversation_history=[
                {"role": "user", "content": "Previous message"},
                {"role": "assistant", "content": "Previous response"},
            ],
        )

        assert len(messages) >= 3  # System + history + current
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Hello"


class TestHelpers:
    """Tests for helper functions"""

    def test_generate_id(self):
        """Test ID generation"""
        id1 = generate_id("test")
        id2 = generate_id("test")
        assert id1.startswith("test_")
        assert id1 != id2  # Should be unique

    def test_sanitize_text(self):
        """Test text sanitization"""
        dirty = "<script>alert('xss')</script><p>Clean text</p>"
        clean = sanitize_text(dirty)
        assert "<script>" not in clean
        assert "Clean text" in clean

    def test_truncate_text(self):
        """Test text truncation"""
        long_text = "This is a very long text that should be truncated"
        truncated = truncate_text(long_text, max_length=20)
        assert len(truncated) <= 23  # 20 + "..."
        assert truncated.endswith("...")

    def test_truncate_text_short(self):
        """Test truncation of short text"""
        short_text = "Short"
        result = truncate_text(short_text, max_length=100)
        assert result == "Short"

    def test_extract_keywords(self):
        """Test keyword extraction"""
        text = "Python programming is great. Python is used for machine learning."
        keywords = extract_keywords(text, max_keywords=5)
        assert "python" in keywords
        assert "programming" in keywords


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
