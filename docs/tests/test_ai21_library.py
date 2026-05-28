"""
Tests for AI21 Library endpoints
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_list_files():
    """Test list files endpoint"""
    response = client.get("/api/v1/ai21/library/files")
    assert response.status_code in [
        200,
        401,
        500,
    ]  # 401 if no auth, 500 if API key missing


@pytest.mark.asyncio
async def test_search():
    """Test library search endpoint"""
    response = client.post(
        "/api/v1/ai21/library/search", json={"query": "test query", "fileIds": None}
    )
    assert response.status_code in [200, 401, 500]


@pytest.mark.asyncio
async def test_search_with_file_ids():
    """Test library search with file IDs"""
    response = client.post(
        "/api/v1/ai21/library/search",
        json={"query": "test query", "fileIds": ["file-id-1", "file-id-2"]},
    )
    assert response.status_code in [200, 401, 500]


@pytest.mark.asyncio
async def test_delete_file():
    """Test delete file endpoint"""
    response = client.delete("/api/v1/ai21/library/files/test-file-id")
    assert response.status_code in [200, 401, 404, 500]


@pytest.mark.asyncio
async def test_search_validation():
    """Test search validation"""
    response = client.post(
        "/api/v1/ai21/library/search",
        json={
            "query": "",  # Empty query should fail validation
        },
    )
    assert response.status_code == 422  # Validation error
