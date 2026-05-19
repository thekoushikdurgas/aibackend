"""
Integration tests for Cohere API workflows
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cohere.classification import CohereClassifier
from app.services.cohere.embeddings import CohereEmbeddings
from app.services.cohere.reranking import CohereReranker


class TestCohereChatWithRAG:
    """Test chat with RAG connectors workflow"""

    @pytest.mark.asyncio
    async def test_chat_with_web_search(self):
        """Test chat with web search connector"""
        with patch("app.services.llm.cohere.httpx.AsyncClient") as mock_client_class:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "text": "Test response with citations",
                "generation_id": "gen-123",
                "finish_reason": "COMPLETE",
                "citations": [
                    {
                        "start": 0,
                        "end": 10,
                        "text": "Test response",
                        "document_ids": ["doc-1"],
                    }
                ],
                "documents": [
                    {
                        "id": "doc-1",
                        "snippet": "Test snippet",
                        "url": "https://example.com",
                    }
                ],
                "search_queries": [{"text": "test query"}],
                "meta": {
                    "billed_units": {"input_tokens": 10, "output_tokens": 5},
                    "tokens": {"input_tokens": 10, "output_tokens": 5},
                },
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            from app.services.llm.cohere import CohereProvider
            from app.services.llm.base import LLMConfig

            provider = CohereProvider()
            config = LLMConfig(model="command")
            response = await provider.generate(prompt="What is AI?", config=config)

            assert response.text == "Test response with citations"
            assert response.raw_response is not None
            assert "citations" in response.raw_response


class TestCohereEmbedJobsWorkflow:
    """Test embed jobs workflow"""

    @pytest.mark.asyncio
    async def test_create_and_check_embed_job(self):
        """Test creating and checking embed job status"""
        with patch("app.services.cohere.embeddings.CohereClient") as mock_client:
            mock_instance = AsyncMock()

            # Mock create job
            mock_instance.post = AsyncMock(
                return_value={
                    "job_id": "job-123",
                    "status": "pending",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            )

            # Mock get job
            mock_instance.get = AsyncMock(
                return_value={
                    "job_id": "job-123",
                    "status": "complete",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            )

            mock_client.return_value = mock_instance

            embeddings = CohereEmbeddings()

            # Create job
            result = await embeddings.create_embed_job(
                dataset_id="dataset-123", input_type="search_document"
            )
            assert result["job_id"] == "job-123"

            # Check status
            status = await embeddings.get_embed_job("job-123")
            assert status["status"] == "complete"


class TestCohereClassificationPipeline:
    """Test classification pipeline"""

    @pytest.mark.asyncio
    async def test_classify_spam_emails(self):
        """Test spam email classification"""
        with patch("app.services.cohere.classification.CohereClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value={
                    "classifications": [
                        {
                            "input": "Confirm your email address",
                            "prediction": "Not spam",
                            "confidence": 0.95,
                            "labels": {"Spam": 0.05, "Not spam": 0.95},
                        },
                        {
                            "input": "hey i need u to send some $",
                            "prediction": "Spam",
                            "confidence": 0.98,
                            "labels": {"Spam": 0.98, "Not spam": 0.02},
                        },
                    ],
                    "id": "test-id",
                    "meta": {},
                }
            )
            mock_client.return_value = mock_instance

            classifier = CohereClassifier()
            result = await classifier.classify(
                inputs=["Confirm your email address", "hey i need u to send some $"],
                examples=[
                    {"text": "Dermatologists don't like her!", "label": "Spam"},
                    {
                        "text": "Your parcel will be delivered today",
                        "label": "Not spam",
                    },
                ],
            )

            assert len(result["classifications"]) == 2
            assert result["classifications"][0]["prediction"] == "Not spam"
            assert result["classifications"][1]["prediction"] == "Spam"


class TestCohereRerankingInSearch:
    """Test reranking in search workflow"""

    @pytest.mark.asyncio
    async def test_rerank_search_results(self):
        """Test reranking search results"""
        with patch("app.services.cohere.reranking.CohereClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value={
                    "results": [
                        {"index": 2, "relevance_score": 0.95, "document": "doc3"},
                        {"index": 0, "relevance_score": 0.80, "document": "doc1"},
                        {"index": 1, "relevance_score": 0.60, "document": "doc2"},
                    ],
                    "id": "test-id",
                    "meta": {},
                }
            )
            mock_client.return_value = mock_instance

            reranker = CohereReranker()
            result = await reranker.rerank(
                query="What is the capital of the United States?",
                documents=[
                    "Carson City is the capital of Nevada",
                    "The capital of the Northern Mariana Islands is Saipan",
                    "Washington, D.C. is the capital of the United States",
                ],
                top_n=3,
            )

            assert len(result["results"]) == 3
            # Check that results are sorted by relevance
            scores = [r["relevance_score"] for r in result["results"]]
            assert scores == sorted(scores, reverse=True)


class TestCohereRAGIntegration:
    """Test RAG integration with Cohere"""

    @pytest.mark.asyncio
    async def test_retrieve_with_reranking(self):
        """Test RAG retrieval with Cohere reranking"""
        with patch("app.services.rag.retriever.ChromaVectorStore") as mock_store:
            # Mock initial retrieval
            mock_store_instance = AsyncMock()
            mock_store_instance.search = MagicMock(
                return_value=[
                    {"content": "doc1", "score": 0.7, "metadata": {}},
                    {"content": "doc2", "score": 0.6, "metadata": {}},
                    {"content": "doc3", "score": 0.5, "metadata": {}},
                ]
            )
            mock_store.return_value = mock_store_instance

            # Mock Cohere reranking
            with patch("app.services.cohere.reranking.CohereClient") as mock_cohere:
                mock_cohere_instance = AsyncMock()
                mock_cohere_instance.post = AsyncMock(
                    return_value={
                        "results": [
                            {"index": 2, "relevance_score": 0.95},
                            {"index": 0, "relevance_score": 0.80},
                            {"index": 1, "relevance_score": 0.60},
                        ]
                    }
                )
                mock_cohere.return_value = mock_cohere_instance

                from app.services.rag.retriever import RAGRetriever

                retriever = RAGRetriever(vector_store=mock_store_instance)

                results = await retriever.retrieve_with_reranking(
                    query="test query", k=10, rerank_top_n=3
                )

                assert len(results) == 3
                assert results[0]["relevance_score"] == 0.95
