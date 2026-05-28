"""
Tests for NVIDIA Embeddings Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.nvidia import NVIDIAEmbeddingService


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "data": [{"embedding": [0.1, 0.2, 0.3] * 256, "index": 0}],  # 768-dim embedding
        "model": "nvidia/nv-embedqa-e5-v5",
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
    }
    response.headers = {"Nvcf-Reqid": "test-req-id", "Nvcf-Status": "fulfilled"}
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def nvidia_embedding_service():
    """Create NVIDIA embedding service instance"""
    return NVIDIAEmbeddingService(api_key="test_key")


@pytest.mark.asyncio
async def test_nvidia_embedding_service_initialization():
    """Test NVIDIA embedding service initialization"""
    service = NVIDIAEmbeddingService(api_key="test_key")
    assert service.client.api_key == "test_key"


@pytest.mark.asyncio
async def test_nvidia_embed_single_text(nvidia_embedding_service, mock_httpx_response):
    """Test single text embedding"""
    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_httpx_response
        )

        result = await nvidia_embedding_service.embed("Hello world")

        assert "embeddings" in result
        assert result["model"] == "nvidia/nv-embedqa-e5-v5"
        assert len(result["embeddings"]) == 1


@pytest.mark.asyncio
async def test_nvidia_embed_batch(nvidia_embedding_service, mock_httpx_response):
    """Test batch embedding"""
    # Update mock for batch response
    mock_httpx_response.json.return_value["data"] = [
        {"embedding": [0.1] * 768, "index": 0},
        {"embedding": [0.2] * 768, "index": 1},
        {"embedding": [0.3] * 768, "index": 2},
    ]

    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_httpx_response
        )

        texts = ["Text 1", "Text 2", "Text 3"]
        result = await nvidia_embedding_service.embed(texts)

        assert len(result["embeddings"]) == 3


@pytest.mark.asyncio
async def test_nvidia_embed_query(nvidia_embedding_service, mock_httpx_response):
    """Test query embedding"""
    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_httpx_response
        )

        embedding = await nvidia_embedding_service.embed_query("What is AI?")

        assert isinstance(embedding, list)
        assert len(embedding) > 0


@pytest.mark.asyncio
async def test_nvidia_embed_passages(nvidia_embedding_service, mock_httpx_response):
    """Test passage embeddings"""
    mock_httpx_response.json.return_value["data"] = [
        {"embedding": [0.1] * 768, "index": 0},
        {"embedding": [0.2] * 768, "index": 1},
    ]

    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_httpx_response
        )

        passages = ["Passage 1", "Passage 2"]
        embeddings = await nvidia_embedding_service.embed_passages(passages)

        assert len(embeddings) == 2
        assert all(isinstance(emb, list) for emb in embeddings)


@pytest.mark.asyncio
async def test_nvidia_embed_with_dimensions(
    nvidia_embedding_service, mock_httpx_response
):
    """Test embedding with custom dimensions"""
    with patch("app.services.nvidia.client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_httpx_response
        )

        result = await nvidia_embedding_service.embed("Test", dimensions=512)

        assert result["model"] == "nvidia/nv-embedqa-e5-v5"


@pytest.mark.asyncio
async def test_nvidia_embed_batch_size_limit(nvidia_embedding_service):
    """Test batch size limit"""
    texts = ["Text"] * 33  # Exceeds limit of 32

    with pytest.raises(ValueError, match="Maximum 32 texts"):
        await nvidia_embedding_service.embed(texts)


@pytest.mark.asyncio
async def test_nvidia_embed_list_models(nvidia_embedding_service):
    """Test listing embedding models"""
    models = await nvidia_embedding_service.list_models()
    assert isinstance(models, list)
    assert len(models) > 0


@pytest.mark.asyncio
async def test_nvidia_embed_get_model_info(nvidia_embedding_service):
    """Test getting embedding model information"""
    info = await nvidia_embedding_service.get_model_info("nvidia/nv-embedqa-e5-v5")
    assert info is not None
    assert info["id"] == "nvidia/nv-embedqa-e5-v5"
    assert info["category"] == "embedding"
