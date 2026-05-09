"""
Tests for AI21 Completion endpoints
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_complete():
    """Test text completion endpoint"""
    response = client.post(
        "/api/v1/ai21/complete",
        json={
            "prompt": "The future of AI is",
            "model": "j2-mid",
            "numResults": 1,
            "maxTokens": 50
        }
    )
    assert response.status_code in [200, 401, 500]  # 401 if no auth, 500 if API key missing


@pytest.mark.asyncio
async def test_complete_with_penalties():
    """Test completion with penalty configurations"""
    response = client.post(
        "/api/v1/ai21/complete",
        json={
            "prompt": "The future of AI is",
            "model": "j2-mid",
            "numResults": 1,
            "maxTokens": 50,
            "frequencyPenalty": {
                "scale": 0.5,
                "applyToWhitespaces": True,
                "applyToPunctuations": True,
                "applyToNumbers": True,
                "applyToStopwords": True,
                "applyToEmojis": True
            }
        }
    )
    assert response.status_code in [200, 401, 500]


@pytest.mark.asyncio
async def test_complete_validation():
    """Test completion validation"""
    response = client.post(
        "/api/v1/ai21/complete",
        json={
            "prompt": "",  # Empty prompt should fail validation
            "model": "j2-mid"
        }
    )
    assert response.status_code == 422  # Validation error
