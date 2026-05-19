"""
Comprehensive tests for OpenRouter Provider
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.openrouter import OpenRouterProvider
from app.services.llm.base import LLMConfig
from app.services.openrouter import OpenRouterModelRegistry, OpenRouterEmbeddingService


@pytest.fixture
def mock_openrouter_provider():
    """Create a mock OpenRouter provider with API key"""
    return OpenRouterProvider(api_key="test-api-key", model="openai/gpt-4o-mini")


@pytest.fixture
def mock_openrouter_provider_no_key():
    """Create a mock OpenRouter provider without API key"""
    return OpenRouterProvider(api_key=None)


class TestOpenRouterProvider:
    """Test OpenRouter provider functionality"""

    @pytest.mark.asyncio
    async def test_provider_initialization(self):
        """Test provider initialization"""
        provider = OpenRouterProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.provider_name == "openrouter"
        assert provider.base_url == "https://openrouter.ai/api/v1"

    @pytest.mark.asyncio
    async def test_provider_initialization_no_key(self):
        """Test provider initialization without API key"""
        provider = OpenRouterProvider(api_key=None)
        assert provider.api_key is None

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_openrouter_provider):
        """Test successful generation"""
        mock_response = {
            "choices": [
                {"message": {"content": "Test response"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "openai/gpt-4o-mini",
            "provider": "OpenAI",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            config = LLMConfig(model="openai/gpt-4o-mini")
            response = await mock_openrouter_provider.generate(
                prompt="Test prompt", config=config
            )

            assert response.text == "Test response"
            assert response.model == "openai/gpt-4o-mini"
            assert response.provider == "openrouter (OpenAI)"
            assert response.usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_generate_no_api_key(self, mock_openrouter_provider_no_key):
        """Test generation fails without API key"""
        with pytest.raises(Exception, match="API key not configured"):
            await mock_openrouter_provider_no_key.generate("test")

    @pytest.mark.asyncio
    async def test_stream(self, mock_openrouter_provider):
        """Test streaming generation"""
        mock_chunks = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
            'data: {"choices":[{"delta":{"content":" World"}}]}\n',
            "data: [DONE]\n",
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_stream = AsyncMock()
            mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream.__aexit__ = AsyncMock(return_value=None)
            mock_stream.raise_for_status = MagicMock()
            mock_stream.aiter_text = AsyncMock(return_value=iter(mock_chunks))

            mock_client.return_value.__aenter__.return_value.stream = AsyncMock(
                return_value=mock_stream
            )

            config = LLMConfig(model="openai/gpt-4o-mini")
            chunks = []
            async for chunk in mock_openrouter_provider.stream("test", config):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0] == "Hello"
            assert chunks[1] == " World"

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_openrouter_provider):
        """Test successful health check"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            is_healthy = await mock_openrouter_provider.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_openrouter_provider):
        """Test failed health check"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection error")
            )

            is_healthy = await mock_openrouter_provider.health_check()
            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_list_models(self, mock_openrouter_provider):
        """Test listing models"""
        mock_models = {
            "data": [
                {"id": "openai/gpt-4o"},
                {"id": "anthropic/claude-3.5-sonnet"},
                {"id": "google/gemini-2.0-flash-001"},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_models
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            models = await mock_openrouter_provider.list_models()
            assert len(models) == 3
            assert "openai/gpt-4o" in models
            assert "anthropic/claude-3.5-sonnet" in models

    @pytest.mark.asyncio
    async def test_list_models_no_key(self, mock_openrouter_provider_no_key):
        """Test listing models without API key returns defaults"""
        models = await mock_openrouter_provider_no_key.list_models()
        assert len(models) > 0
        assert "openrouter/auto" in models


class TestOpenRouterModelRegistry:
    """Test OpenRouter model registry"""

    @pytest.mark.asyncio
    async def test_fetch_models(self):
        """Test fetching models"""
        registry = OpenRouterModelRegistry(api_key="test-key")

        mock_models = {
            "data": [
                {
                    "id": "openai/gpt-4o",
                    "name": "GPT-4o",
                    "context_length": 128000,
                    "pricing": {"prompt": "0.0025", "completion": "0.01"},
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_models
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            models = await registry.fetch_models()
            assert len(models) == 1
            assert models[0]["id"] == "openai/gpt-4o"

    @pytest.mark.asyncio
    async def test_auto_route(self):
        """Test auto-routing"""
        registry = OpenRouterModelRegistry(api_key="test-key")

        # Mock models
        registry._models = [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "context_length": 128000,
                "pricing": {"prompt": "0.0025", "completion": "0.01"},
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "context_length": 128000,
                "pricing": {"prompt": "0.00015", "completion": "0.0006"},
            },
        ]

        result = await registry.auto_route(query="Simple question", prefer_speed=True)

        assert "selected_model" in result
        assert "reasoning" in result
        assert "alternatives" in result


class TestOpenRouterEmbeddings:
    """Test OpenRouter embeddings service"""

    @pytest.mark.asyncio
    async def test_embed_text(self):
        """Test embedding single text"""
        service = OpenRouterEmbeddingService(api_key="test-key")

        mock_response = {
            "data": [{"embedding": [0.1, 0.2, 0.3] * 512}]  # 1536 dimensions
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            embedding = await service.embed_text("test text")
            assert len(embedding) == 1536
            assert embedding[0] == 0.1

    @pytest.mark.asyncio
    async def test_embed_texts(self):
        """Test embedding multiple texts"""
        service = OpenRouterEmbeddingService(api_key="test-key")

        mock_response = {
            "data": [{"embedding": [0.1] * 1536}, {"embedding": [0.2] * 1536}]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            embeddings = await service.embed_texts(["text1", "text2"])
            assert len(embeddings) == 2
            assert len(embeddings[0]) == 1536

    def test_list_models(self):
        """Test listing embedding models"""
        service = OpenRouterEmbeddingService()
        models = service.list_models()
        assert len(models) > 0
        assert "openai/text-embedding-3-small" in models

    @pytest.mark.asyncio
    async def test_get_embedding_dimension(self):
        """Test getting embedding dimensions"""
        service = OpenRouterEmbeddingService()
        dim = await service.get_embedding_dimension("openai/text-embedding-3-small")
        assert dim == 1536

        dim = await service.get_embedding_dimension("google/gemini-embedding-001")
        assert dim == 768

    def test_get_model_metadata(self):
        """Test getting model metadata"""
        service = OpenRouterEmbeddingService()
        metadata = service.get_model_metadata("openai/text-embedding-3-small")
        assert "dimensions" in metadata
        assert "pricing" in metadata

    def test_calculate_cost(self):
        """Test cost calculation"""
        service = OpenRouterEmbeddingService()
        cost = service.calculate_cost("openai/text-embedding-3-small", 1000)
        assert cost >= 0


class TestOpenRouterModelRegistryAdvanced:
    """Advanced tests for OpenRouter model registry"""

    @pytest.mark.asyncio
    async def test_get_models_by_provider(self):
        """Test getting models by provider"""
        registry = OpenRouterModelRegistry(api_key="test-key")

        # Mock models
        registry._models = [
            {"id": "openai/gpt-4o", "name": "GPT-4o"},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
            {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash"},
        ]

        gpt_models = registry.get_models_by_provider("gpt")
        assert len(gpt_models) > 0
        assert any("gpt" in m["id"] for m in gpt_models)

    @pytest.mark.asyncio
    async def test_get_providers(self):
        """Test getting provider list"""
        registry = OpenRouterModelRegistry()
        providers = registry.get_providers()
        assert len(providers) > 0
        assert "gpt" in providers
        assert "claude" in providers

    @pytest.mark.asyncio
    async def test_categorize_by_provider(self):
        """Test categorizing models by provider"""
        registry = OpenRouterModelRegistry(api_key="test-key")
        registry._models = [
            {"id": "openai/gpt-4o", "name": "GPT-4o"},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
        ]

        categories = registry.categorize_by_provider()
        assert "gpt" in categories
        assert "claude" in categories


class TestOpenRouterMonitoring:
    """Tests for OpenRouter monitoring"""

    def test_monitor_record_request(self):
        """Test recording requests"""
        from app.services.openrouter.monitoring import OpenRouterMonitor

        monitor = OpenRouterMonitor()
        monitor.record_request(
            model="openai/gpt-4o",
            provider="OpenAI",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=500.0,
            success=True,
        )

        assert monitor.stats.total_requests == 1
        assert monitor.stats.successful_requests == 1
        assert monitor.stats.total_tokens == 150

    def test_monitor_error_tracking(self):
        """Test error tracking"""
        from app.services.openrouter.monitoring import OpenRouterMonitor

        monitor = OpenRouterMonitor()
        monitor.record_request(
            model="openai/gpt-4o",
            provider="OpenAI",
            latency_ms=100.0,
            success=False,
            error_type="http_error",
            error_message="Rate limited",
        )

        assert monitor.stats.failed_requests == 1
        assert "http_error" in monitor.stats.error_counts
        assert monitor.stats.error_counts["http_error"] == 1

    def test_monitor_health_check(self):
        """Test health check"""
        from app.services.openrouter.monitoring import OpenRouterMonitor

        monitor = OpenRouterMonitor()

        # Record some successful requests
        for _ in range(10):
            monitor.record_request(
                model="openai/gpt-4o", provider="OpenAI", latency_ms=500.0, success=True
            )

        health = monitor.check_health()
        assert health["status"] == "healthy"
        assert health["success_rate"] == 1.0

    def test_monitor_get_stats_window(self):
        """Test getting stats for time window"""
        from app.services.openrouter.monitoring import OpenRouterMonitor

        monitor = OpenRouterMonitor()

        # Record request
        monitor.record_request(
            model="openai/gpt-4o", provider="OpenAI", latency_ms=500.0, success=True
        )

        stats = monitor.get_stats(window_minutes=1)
        assert stats.total_requests == 1

        stats = monitor.get_stats(window_minutes=0)  # Very small window
        assert stats.total_requests == 0  # Should be empty


class TestOpenRouterProviderAdvanced:
    """Advanced tests for OpenRouter provider"""

    @pytest.mark.asyncio
    async def test_generate_with_cost_tracking(self, mock_openrouter_provider):
        """Test generation with cost tracking"""
        mock_response = {
            "choices": [
                {"message": {"content": "Test response"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "openai/gpt-4o",
            "provider": "OpenAI",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            # Mock get_model_info
            with patch.object(
                mock_openrouter_provider, "get_model_info", new_callable=AsyncMock
            ) as mock_info:
                mock_info.return_value = {
                    "pricing": {"prompt": "0.0025", "completion": "0.01"}
                }

                config = LLMConfig(model="openai/gpt-4o")
                response = await mock_openrouter_provider.generate(
                    prompt="Test prompt", config=config
                )

                assert response.text == "Test response"
                assert "cost" in response.usage
                assert response.usage["cost"] > 0

    @pytest.mark.asyncio
    async def test_generate_with_retry(self, mock_openrouter_provider):
        """Test generation with retry logic"""
        import httpx

        # First call fails with 500, second succeeds
        mock_error = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=MagicMock(status_code=500)
        )
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {
            "choices": [{"message": {"content": "Success"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            "model": "openai/gpt-4o",
        }
        mock_success.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=[mock_error, mock_success])
            mock_client.return_value.__aenter__.return_value.post = mock_post

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with patch.object(
                    mock_openrouter_provider, "get_model_info", new_callable=AsyncMock
                ):
                    config = LLMConfig(model="openai/gpt-4o")
                    response = await mock_openrouter_provider.generate(
                        prompt="Test", config=config
                    )

                    assert response.text == "Success"
                    assert mock_post.call_count == 2  # Retried once

    @pytest.mark.asyncio
    async def test_generate_with_cache(self, mock_openrouter_provider):
        """Test generation with caching"""
        mock_response = {
            "choices": [{"message": {"content": "Cached response"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            "model": "openai/gpt-4o",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            with patch.object(
                mock_openrouter_provider, "get_model_info", new_callable=AsyncMock
            ):
                # First call - should make API request
                config = LLMConfig(model="openai/gpt-4o", temperature=0.0)
                response1 = await mock_openrouter_provider.generate(
                    prompt="Test", config=config
                )

                # Second call with same params - should use cache
                response2 = await mock_openrouter_provider.generate(
                    prompt="Test", config=config
                )

                assert response1.text == response2.text
                # Should only call API once (cached on second call)
                # Note: This is a simplified test - actual cache key includes more params
