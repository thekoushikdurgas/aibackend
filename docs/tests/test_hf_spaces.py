"""
Tests for HuggingFace Gradio Spaces integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.huggingface.spaces import (
    GradioSpacesClient,
    RAGService,
    AgenticAIService
)


@pytest.fixture
def mock_hf_client():
    """Mock HuggingFace client"""
    client = AsyncMock()
    client.gradio_predict = AsyncMock(return_value={"event_id": "test-event-123"})
    client.gradio_poll = AsyncMock(return_value=["Test result"])
    return client


@pytest.fixture
def gradio_client(mock_hf_client):
    """Gradio Spaces client fixture"""
    with patch("app.services.huggingface.spaces.HuggingFaceClient", return_value=mock_hf_client):
        client = GradioSpacesClient()
        client.client = mock_hf_client
        return client


@pytest.fixture
def rag_service(mock_hf_client):
    """RAG service fixture"""
    with patch("app.services.huggingface.spaces.HuggingFaceClient", return_value=mock_hf_client):
        service = RAGService()
        service.client.client = mock_hf_client
        return service


@pytest.fixture
def agentic_service(mock_hf_client):
    """Agentic AI service fixture"""
    with patch("app.services.huggingface.spaces.HuggingFaceClient", return_value=mock_hf_client):
        service = AgenticAIService()
        service.client.client = mock_hf_client
        return service


@pytest.mark.asyncio
async def test_gradio_predict(gradio_client, mock_hf_client):
    """Test Gradio predict method"""
    space_url = "https://test-space.hf.space"
    data = ["test", "data"]
    
    result = await gradio_client.predict(space_url, data)
    
    assert result == {"event_id": "test-event-123"}
    mock_hf_client.gradio_predict.assert_called_once_with(space_url, data, None)


@pytest.mark.asyncio
async def test_gradio_poll(gradio_client, mock_hf_client):
    """Test Gradio poll method"""
    space_url = "https://test-space.hf.space"
    event_id = "test-event-123"
    
    result = await gradio_client.poll(space_url, event_id)
    
    assert result == ["Test result"]
    mock_hf_client.gradio_poll.assert_called_once()


@pytest.mark.asyncio
async def test_gradio_predict_and_wait(gradio_client, mock_hf_client):
    """Test predict and wait convenience method"""
    space_url = "https://test-space.hf.space"
    data = ["test", "data"]
    
    result = await gradio_client.predict_and_wait(space_url, data)
    
    assert result == ["Test result"]
    mock_hf_client.gradio_predict.assert_called_once()
    mock_hf_client.gradio_poll.assert_called_once()


@pytest.mark.asyncio
async def test_naive_rag_predict(rag_service, mock_hf_client):
    """Test naive RAG predict"""
    question = "What is AI?"
    framework = "LangChain"
    
    result = await rag_service.naive_rag_predict(question, framework)
    
    assert result == {"event_id": "test-event-123"}
    mock_hf_client.gradio_predict.assert_called_once()


@pytest.mark.asyncio
async def test_naive_rag_poll(rag_service, mock_hf_client):
    """Test naive RAG poll"""
    event_id = "test-event-123"
    
    result = await rag_service.naive_rag_poll(event_id)
    
    assert isinstance(result, str)
    mock_hf_client.gradio_poll.assert_called_once()


@pytest.mark.asyncio
async def test_naive_rag_complete(rag_service, mock_hf_client):
    """Test complete naive RAG workflow"""
    question = "What is AI?"
    
    result = await rag_service.naive_rag(question)
    
    assert isinstance(result, str)
    mock_hf_client.gradio_predict.assert_called_once()
    mock_hf_client.gradio_poll.assert_called_once()


@pytest.mark.asyncio
async def test_advanced_rag_predict(rag_service, mock_hf_client):
    """Test advanced RAG predict"""
    question = "Recommend hotels"
    num_results = 2
    rerank = 1
    
    result = await rag_service.advanced_rag_predict(question, num_results, rerank)
    
    assert result == {"event_id": "test-event-123"}
    mock_hf_client.gradio_predict.assert_called_once()


@pytest.mark.asyncio
async def test_agentic_crewai_predict(agentic_service, mock_hf_client):
    """Test crewAI agentic RAG predict"""
    # Set URL to avoid ValueError
    agentic_service.crewai_url = "https://test-crewai.hf.space"
    
    question = "Research quantum computing"
    
    result = await agentic_service.agentic_rag_crewai_predict(question)
    
    assert result == {"event_id": "test-event-123"}
    mock_hf_client.gradio_predict.assert_called_once()


@pytest.mark.asyncio
async def test_agentic_crewai_complete(agentic_service, mock_hf_client):
    """Test complete crewAI workflow"""
    agentic_service.crewai_url = "https://test-crewai.hf.space"
    
    question = "Research quantum computing"
    
    result = await agentic_service.agentic_rag_crewai(question)
    
    assert result == ["Test result"]
    mock_hf_client.gradio_predict.assert_called_once()
    mock_hf_client.gradio_poll.assert_called_once()


@pytest.mark.asyncio
async def test_agentic_langgraph_predict(agentic_service, mock_hf_client):
    """Test LangGraph agentic RAG predict"""
    agentic_service.langgraph_url = "https://test-langgraph.hf.space"
    
    question = "Research AI safety"
    
    result = await agentic_service.agentic_rag_langgraph_predict(question)
    
    assert result == {"event_id": "test-event-123"}
    mock_hf_client.gradio_predict.assert_called_once()


@pytest.mark.asyncio
async def test_agentic_openai_requires_key(agentic_service):
    """Test OpenAI agentic RAG requires API key"""
    agentic_service.openai_url = "https://test-openai.hf.space"
    
    question = "Research topic"
    
    with pytest.raises(ValueError, match="OpenAI API key required"):
        await agentic_service.agentic_rag_openai_predict(question)


@pytest.mark.asyncio
async def test_parse_gradio_stream():
    """Test SSE stream parsing"""
    from app.services.llm.hf_client import HuggingFaceClient
    
    client = HuggingFaceClient()
    
    # Mock response with SSE data
    mock_response = AsyncMock()
    mock_response.aiter_lines = AsyncMock(return_value=iter([
        "event: complete",
        'data: ["{\\"result\\": \\"test\\"}"]'
    ]))
    
    result = await client._parse_gradio_stream(mock_response)
    
    assert result is not None

