"""
API endpoint tests for DurgasAI Backend
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def api_key_headers():
    """Headers with API key for authenticated requests"""
    return {"X-API-Key": settings.api_key}


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_health_check(self, client):
        """Test main health endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data

    def test_readiness_probe(self, client):
        """Test readiness probe"""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_liveness_probe(self, client):
        """Test liveness probe"""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


class TestAuthEndpoints:
    """Tests for authentication endpoints"""

    def test_get_token_valid_api_key(self, client):
        """Test getting token with valid API key"""
        response = client.post("/api/v1/auth/token", json={"api_key": settings.api_key})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_get_token_invalid_api_key(self, client):
        """Test getting token with invalid API key"""
        response = client.post("/api/v1/auth/token", json={"api_key": "invalid_key"})
        assert response.status_code == 401


class TestChatEndpoints:
    """Tests for chat endpoints"""

    def test_list_providers(self, client):
        """Test listing LLM providers"""
        response = client.get("/api/v1/chat/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert len(data["providers"]) > 0


class TestAgentEndpoints:
    """Tests for agent endpoints"""

    def test_list_agents(self, client):
        """Test listing available agents"""
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 5  # 5 agents defined

    def test_analyze_structure(self, client):
        """Test structure analysis endpoint"""
        response = client.post(
            "/api/v1/analysis/structure",
            json={
                "url": "https://example.com",
                "title": "Example",
                "html": "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "structure_stats" in data


class TestAnalysisEndpoints:
    """Tests for analysis endpoints"""

    def test_extract_text(self, client):
        """Test text extraction endpoint"""
        response = client.post(
            "/api/v1/analysis/extract-text",
            json={
                "url": "https://example.com",
                "html": "<html><body><p>Test content here.</p></body></html>",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "Test content" in data["text"]

    def test_basic_seo_analysis(self, client):
        """Test basic SEO analysis endpoint"""
        response = client.post(
            "/api/v1/analysis/seo-basic",
            json={
                "url": "https://example.com",
                "html": """
                <html>
                    <head>
                        <title>Test Page Title</title>
                        <meta name="description" content="Test description">
                    </head>
                    <body><h1>Main Heading</h1></body>
                </html>
                """,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "scores" in data
        assert "seo_data" in data


class TestRAGEndpoints:
    """Tests for RAG endpoints"""

    def test_rag_stats(self, client, api_key_headers):
        """Test RAG stats endpoint"""
        response = client.get("/api/v1/rag/stats", headers=api_key_headers)
        # May require auth, so check for either 200 or 401
        assert response.status_code in [200, 401]


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "DurgasAI Backend"
        assert "version" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
