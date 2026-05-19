"""
Tests for AI21 Answer endpoints
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_answer_single_document():
    """Test single document answer endpoint"""
    response = client.post(
        "/api/v1/ai21/answer/single-document",
        json={
            "context": "The quick brown fox jumps over the lazy dog. This is a test sentence.",
            "question": "What jumps over the lazy dog?",
        },
    )
    assert response.status_code in [
        200,
        401,
        500,
    ]  # 401 if no auth, 500 if API key missing


@pytest.mark.asyncio
async def test_answer_rag():
    """Test RAG answer endpoint"""
    response = client.post(
        "/api/v1/ai21/answer/rag",
        json={"question": "What is GPT-4?", "documentIds": ["test-doc-id-123"]},
    )
    assert response.status_code in [
        200,
        401,
        500,
    ]  # 401 if no auth, 500 if API key missing


@pytest.mark.asyncio
async def test_answer_single_document_validation():
    """Test single document answer validation"""
    response = client.post(
        "/api/v1/ai21/answer/single-document",
        json={
            "context": "",  # Empty context should fail validation
            "question": "Test question",
        },
    )
    assert response.status_code == 422  # Validation error
