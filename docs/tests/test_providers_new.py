"""
Tests for new LLM providers
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.fireworks import FireworksProvider
from app.services.llm.deepinfra import DeepInfraProvider
from app.services.llm.anyscale import AnyscaleProvider
from app.services.llm.lepton import LeptonProvider
from app.services.llm.octoai import OctoAIProvider
from app.services.llm.together import TogetherProvider
from app.services.llm.mistral import MistralProvider
from app.services.llm.perplexity import PerplexityProvider
from app.services.llm.base import LLMConfig


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "choices": [{"message": {"content": "Test response"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.mark.asyncio
async def test_fireworks_provider_initialization():
    """Test Fireworks provider initialization"""
    provider = FireworksProvider(api_key="test_key")
    assert provider.provider_name == "fireworks"
    assert provider.api_key == "test_key"
    assert provider.base_url == "https://api.fireworks.ai/inference/v1"


@pytest.mark.asyncio
async def test_deepinfra_provider_initialization():
    """Test Deep Infra provider initialization"""
    provider = DeepInfraProvider(api_key="test_key")
    assert provider.provider_name == "deepinfra"
    assert provider.api_key == "test_key"


@pytest.mark.asyncio
async def test_anyscale_provider_initialization():
    """Test Anyscale provider initialization"""
    provider = AnyscaleProvider(api_key="test_key")
    assert provider.provider_name == "anyscale"
    assert provider.api_key == "test_key"


@pytest.mark.asyncio
async def test_lepton_provider_base_url():
    """Test Lepton provider dynamic base URL"""
    provider = LeptonProvider(api_key="test_key", model="llama3-70b")
    base_url = provider._get_base_url("llama3-70b")
    assert "llama3-70b" in base_url or base_url == "https://llama3-70b.lepton.run"


@pytest.mark.asyncio
async def test_octoai_provider_initialization():
    """Test OctoAI provider initialization"""
    provider = OctoAIProvider(api_key="test_key")
    assert provider.provider_name == "octoai"
    assert provider.api_key == "test_key"


@pytest.mark.asyncio
async def test_together_provider_initialization():
    """Test Together AI provider initialization"""
    provider = TogetherProvider(api_key="test_key")
    assert provider.provider_name == "together"
    assert provider.api_key == "test_key"


@pytest.mark.asyncio
async def test_mistral_provider_initialization():
    """Test Mistral AI provider initialization"""
    provider = MistralProvider(api_key="test_key")
    assert provider.provider_name == "mistral"
    assert provider.api_key == "test_key"


@pytest.mark.asyncio
async def test_perplexity_provider_initialization():
    """Test Perplexity AI provider initialization"""
    provider = PerplexityProvider(api_key="test_key")
    assert provider.provider_name == "perplexity"
    assert provider.api_key == "test_key"


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_fireworks_generate(mock_client_class, mock_httpx_response):
    """Test Fireworks provider generate method"""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_httpx_response
    mock_client_class.return_value = mock_client

    provider = FireworksProvider(api_key="test_key")
    config = LLMConfig(model="test-model", max_tokens=100)

    response = await provider.generate("Test prompt", config=config)

    assert response.text == "Test response"
    assert response.provider == "fireworks"
    assert response.usage["total_tokens"] == 30


@pytest.mark.asyncio
async def test_provider_list_models():
    """Test that all providers can list models"""
    providers = [
        FireworksProvider(api_key="test"),
        DeepInfraProvider(api_key="test"),
        AnyscaleProvider(api_key="test"),
        LeptonProvider(api_key="test"),
        OctoAIProvider(api_key="test"),
        TogetherProvider(api_key="test"),
        MistralProvider(api_key="test"),
        PerplexityProvider(api_key="test"),
    ]

    for provider in providers:
        models = await provider.list_models()
        assert isinstance(models, list)
        assert len(models) > 0


@pytest.mark.asyncio
async def test_provider_health_check_no_key():
    """Test health check returns False when API key is missing"""
    provider = FireworksProvider(api_key=None)
    result = await provider.health_check()
    assert result is False
