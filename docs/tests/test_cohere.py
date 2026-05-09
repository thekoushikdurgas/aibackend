"""
Tests for Cohere integration
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cohere import (
    CohereEmbeddings,
    CohereClassifier,
    CohereReranker,
    CohereConnectors,
    CohereDatasets,
    CohereFineTune,
    CohereSummarizer,
    CohereTokenizer
)
from app.services.llm.cohere import CohereProvider
from app.services.llm.base import LLMConfig


class TestCohereEmbeddings:
    """Test Cohere embeddings service"""
    
    @pytest.mark.asyncio
    async def test_embed(self):
        """Test embedding generation"""
        with patch('app.services.cohere.embeddings.CohereClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value={
                "embeddings": [[0.1, 0.2, 0.3]],
                "id": "test-id",
                "texts": ["test text"],
                "meta": {}
            })
            mock_client.return_value = mock_instance
            
            embeddings = CohereEmbeddings()
            result = await embeddings.embed(
                texts=["test text"],
                input_type="search_document"
            )
            
            assert "embeddings" in result
            assert len(result["embeddings"]) == 1
            mock_instance.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_embed_job(self):
        """Test creating embed job"""
        with patch('app.services.cohere.embeddings.CohereClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value={
                "job_id": "job-123",
                "status": "pending"
            })
            mock_client.return_value = mock_instance
            
            embeddings = CohereEmbeddings()
            result = await embeddings.create_embed_job(
                dataset_id="dataset-123",
                input_type="search_document"
            )
            
            assert "job_id" in result
            mock_instance.post.assert_called_once()


class TestCohereClassifier:
    """Test Cohere classification service"""
    
    @pytest.mark.asyncio
    async def test_classify(self):
        """Test text classification"""
        with patch('app.services.cohere.classification.CohereClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value={
                "classifications": [{
                    "input": "test input",
                    "prediction": "positive",
                    "confidence": 0.95,
                    "labels": {"positive": 0.95, "negative": 0.05}
                }],
                "id": "test-id",
                "meta": {}
            })
            mock_client.return_value = mock_instance
            
            classifier = CohereClassifier()
            result = await classifier.classify(
                inputs=["test input"],
                examples=[
                    {"text": "positive example", "label": "positive"},
                    {"text": "negative example", "label": "negative"}
                ]
            )
            
            assert "classifications" in result
            assert len(result["classifications"]) == 1
            mock_instance.post.assert_called_once()


class TestCohereReranker:
    """Test Cohere reranking service"""
    
    @pytest.mark.asyncio
    async def test_rerank(self):
        """Test document reranking"""
        with patch('app.services.cohere.reranking.CohereClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value={
                "results": [
                    {"index": 0, "relevance_score": 0.95, "document": "doc1"},
                    {"index": 1, "relevance_score": 0.80, "document": "doc2"}
                ],
                "id": "test-id",
                "meta": {}
            })
            mock_client.return_value = mock_instance
            
            reranker = CohereReranker()
            result = await reranker.rerank(
                query="test query",
                documents=["doc1", "doc2", "doc3"],
                top_n=2
            )
            
            assert "results" in result
            assert len(result["results"]) == 2
            assert result["results"][0]["relevance_score"] > result["results"][1]["relevance_score"]
            mock_instance.post.assert_called_once()


class TestCohereConnectors:
    """Test Cohere connectors service"""
    
    @pytest.mark.asyncio
    async def test_create_connector(self):
        """Test creating a connector"""
        with patch('app.services.cohere.connectors.CohereClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value={
                "id": "connector-123",
                "name": "Test Connector",
                "url": "https://example.com",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            })
            mock_client.return_value = mock_instance
            
            connectors = CohereConnectors()
            result = await connectors.create_connector(
                name="Test Connector",
                url="https://example.com"
            )
            
            assert "id" in result
            mock_instance.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_connectors(self):
        """Test listing connectors"""
        with patch('app.services.cohere.connectors.CohereClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value={
                "connectors": [
                    {"id": "connector-1", "name": "Connector 1"},
                    {"id": "connector-2", "name": "Connector 2"}
                ]
            })
            mock_client.return_value = mock_instance
            
            connectors = CohereConnectors()
            result = await connectors.list_connectors()
            
            assert "connectors" in result
            mock_instance.get.assert_called_once()


class TestCohereProvider:
    """Test Cohere LLM provider"""
    
    @pytest.mark.asyncio
    async def test_generate(self):
        """Test text generation"""
        with patch('app.services.llm.cohere.httpx.AsyncClient') as mock_client_class:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "text": "Test response",
                "generation_id": "gen-123",
                "finish_reason": "COMPLETE",
                "meta": {
                    "billed_units": {
                        "input_tokens": 10,
                        "output_tokens": 5
                    },
                    "tokens": {
                        "input_tokens": 10,
                        "output_tokens": 5
                    }
                }
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            provider = CohereProvider()
            config = LLMConfig(model="command", temperature=0.7, max_tokens=100)
            response = await provider.generate(
                prompt="Test prompt",
                config=config
            )
            
            assert response.text == "Test response"
            assert response.provider == "cohere"
            assert response.usage is not None
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check"""
        with patch('app.services.llm.cohere.httpx.AsyncClient') as mock_client_class:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            provider = CohereProvider()
            healthy = await provider.health_check()
            
            assert healthy is True
            mock_client.get.assert_called_once_with("/models")
    
    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing models"""
        with patch('app.services.llm.cohere.httpx.AsyncClient') as mock_client_class:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "models": [
                    {"name": "command"},
                    {"name": "command-light"}
                ]
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            provider = CohereProvider()
            models = await provider.list_models()
            
            assert len(models) == 2
            assert "command" in models
            mock_client.get.assert_called_once_with("/models")


class TestCohereSummarizer:
    """Test Cohere summarization service"""
    
    @pytest.mark.asyncio
    async def test_summarize(self):
        """Test text summarization"""
        with patch('app.services.cohere.summarization.CohereClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value={
                "summary": "This is a summary",
                "id": "test-id",
                "meta": {}
            })
            mock_client.return_value = mock_instance
            
            summarizer = CohereSummarizer()
            result = await summarizer.summarize(
                text="This is a long text that needs to be summarized..."
            )
            
            assert "summary" in result
            mock_instance.post.assert_called_once()


class TestCohereTokenizer:
    """Test Cohere tokenization service"""
    
    @pytest.mark.asyncio
    async def test_tokenize(self):
        """Test tokenization"""
        with patch('app.services.cohere.tokenization.CohereClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value={
                "tokens": [1, 2, 3, 4, 5],
                "token_strings": ["token", "strings"]
            })
            mock_client.return_value = mock_instance
            
            tokenizer = CohereTokenizer()
            result = await tokenizer.tokenize("test text")
            
            assert "tokens" in result
            mock_instance.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detokenize(self):
        """Test detokenization"""
        with patch('app.services.cohere.tokenization.CohereClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value={
                "text": "test text"
            })
            mock_client.return_value = mock_instance
            
            tokenizer = CohereTokenizer()
            result = await tokenizer.detokenize([1, 2, 3, 4, 5])
            
            assert "text" in result
            mock_instance.post.assert_called_once()
