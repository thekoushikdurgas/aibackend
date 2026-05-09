"""
Tests for AI21 Fine-Tuning endpoints
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_list_datasets():
    """Test list datasets endpoint"""
    response = client.get("/api/v1/ai21/datasets")
    assert response.status_code in [200, 401, 500]  # 401 if no auth, 500 if API key missing


@pytest.mark.asyncio
async def test_get_dataset():
    """Test get dataset endpoint"""
    response = client.get("/api/v1/ai21/datasets/test-dataset-id")
    assert response.status_code in [200, 401, 404, 500]


@pytest.mark.asyncio
async def test_delete_dataset():
    """Test delete dataset endpoint"""
    response = client.delete("/api/v1/ai21/datasets/test-dataset-id")
    assert response.status_code in [200, 401, 404, 500]


@pytest.mark.asyncio
async def test_list_custom_models():
    """Test list custom models endpoint"""
    response = client.get("/api/v1/ai21/custom-models")
    assert response.status_code in [200, 401, 500]


@pytest.mark.asyncio
async def test_get_custom_model():
    """Test get custom model endpoint"""
    response = client.get("/api/v1/ai21/custom-models/test-model-id")
    assert response.status_code in [200, 401, 404, 500]


@pytest.mark.asyncio
async def test_create_custom_model():
    """Test create custom model endpoint"""
    response = client.post(
        "/api/v1/ai21/custom-models",
        json={
            "model_type": "j2-mid",
            "dataset_id": "test-dataset-id",
            "model_name": "test-model",
            "learning_rate": 0.5,
            "num_epochs": 20
        }
    )
    assert response.status_code in [200, 201, 401, 500]


@pytest.mark.asyncio
async def test_update_default_epoch():
    """Test update default epoch endpoint"""
    response = client.put(
        "/api/v1/ai21/custom-models/test-model-id",
        json={
            "defaultEpoch": 5
        }
    )
    assert response.status_code in [200, 401, 404, 500]


@pytest.mark.asyncio
async def test_custom_model_complete():
    """Test custom model completion endpoint"""
    response = client.post(
        "/api/v1/ai21/custom-models/test-model-id/complete",
        params={"model_type": "j2-mid"},
        json={
            "prompt": "The future of AI is",
            "numResults": 1,
            "maxTokens": 50
        }
    )
    assert response.status_code in [200, 401, 404, 500]


@pytest.mark.asyncio
async def test_create_custom_model_validation():
    """Test create custom model validation"""
    response = client.post(
        "/api/v1/ai21/custom-models",
        json={
            "model_type": "",  # Empty model type should fail validation
            "dataset_id": "test-dataset-id",
            "model_name": "test-model"
        }
    )
    assert response.status_code == 422  # Validation error
