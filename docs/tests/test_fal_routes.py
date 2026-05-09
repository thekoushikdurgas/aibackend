"""
Integration tests for fal.ai API routes
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.fal import FalClient, QueueManager


class TestFalImageRoutes:
    """Test image generation routes"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.mark.asyncio
    @patch('app.api.routes.fal.images.get_image_service')
    async def test_generate_flux_image(self, mock_get_service, client):
        """Test flux-pro image generation endpoint"""
        mock_service = MagicMock()
        mock_service.generate_flux_pro = AsyncMock(return_value={
            "job_id": "test-id",
            "result": {"images": [{"url": "https://example.com/image.jpg"}]},
            "model": "flux-pro/v1.1-ultra"
        })
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/fal/images/flux-pro/v1.1-ultra",
            json={"prompt": "test prompt"}
        )
        
        assert response.status_code == 200
        assert "job_id" in response.json()
        mock_service.generate_flux_pro.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.api.routes.fal.images.get_image_service')
    async def test_generate_imagen4_image(self, mock_get_service, client):
        """Test imagen4 image generation endpoint"""
        mock_service = MagicMock()
        mock_service.generate_imagen4 = AsyncMock(return_value={
            "job_id": "test-id",
            "result": {"images": [{"url": "https://example.com/image.jpg"}]},
            "model": "imagen4/preview"
        })
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/fal/images/imagen4/preview",
            json={"prompt": "test prompt"}
        )
        
        assert response.status_code == 200
        mock_service.generate_imagen4.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.api.routes.fal.images.get_image_service')
    async def test_generate_veo3_image(self, mock_get_service, client):
        """Test veo3 image generation endpoint"""
        mock_service = MagicMock()
        mock_service.generate_veo3 = AsyncMock(return_value={
            "job_id": "test-id",
            "result": {"images": [{"url": "https://example.com/image.jpg"}]},
            "model": "veo3"
        })
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/fal/images/veo3",
            json={"prompt": "test prompt"}
        )
        
        assert response.status_code == 200
        mock_service.generate_veo3.assert_called_once()


class TestFalAudioRoutes:
    """Test audio generation routes"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.mark.asyncio
    @patch('app.api.routes.fal.audio.get_audio_service')
    async def test_generate_audio(self, mock_get_service, client):
        """Test audio generation endpoint"""
        mock_service = MagicMock()
        mock_service.generate_music = AsyncMock(return_value={
            "job_id": "test-id",
            "result": {"audio": {"url": "https://example.com/audio.mp3"}},
            "model": "yue"
        })
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/fal/audio/yue",
            json={
                "lyrics": "[verse]\nTest lyrics",
                "genres": "pop rock"
            }
        )
        
        assert response.status_code == 200
        mock_service.generate_music.assert_called_once()


class TestFalVideoRoutes:
    """Test video generation routes"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.mark.asyncio
    @patch('app.api.routes.fal.video.get_video_service')
    async def test_text_to_video(self, mock_get_service, client):
        """Test text-to-video endpoint"""
        mock_service = MagicMock()
        mock_service.generate_from_text = AsyncMock(return_value={
            "job_id": "test-id",
            "result": {"video": {"url": "https://example.com/video.mp4"}},
            "model": "veo2"
        })
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/fal/video/veo2/text-to-video",
            json={"prompt": "test prompt"}
        )
        
        assert response.status_code == 200
        mock_service.generate_from_text.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.api.routes.fal.video.get_video_service')
    async def test_image_to_video(self, mock_get_service, client):
        """Test image-to-video endpoint"""
        mock_service = MagicMock()
        mock_service.generate_from_image = AsyncMock(return_value={
            "job_id": "test-id",
            "result": {"video": {"url": "https://example.com/video.mp4"}},
            "model": "veo2"
        })
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/fal/video/veo2/image-to-video",
            json={
                "prompt": "test prompt",
                "image_url": "https://example.com/image.jpg"
            }
        )
        
        assert response.status_code == 200
        mock_service.generate_from_image.assert_called_once()


class TestFalQueueRoutes:
    """Test queue management routes"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.mark.asyncio
    @patch('app.api.routes.fal.queue.get_fal_client')
    async def test_get_job_status(self, mock_get_client, client):
        """Test job status endpoint"""
        mock_fal_client = MagicMock(spec=FalClient)
        mock_fal_client.get_status = AsyncMock(return_value={
            "status": "COMPLETED",
            "request_id": "test-id"
        })
        mock_get_client.return_value = mock_fal_client
        
        response = client.get(
            "/api/v1/fal/queue/status",
            params={"status_url": "https://queue.fal.run/status"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "COMPLETED"
        mock_fal_client.get_status.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.api.routes.fal.queue.get_fal_client')
    async def test_get_job_result(self, mock_get_client, client):
        """Test job result endpoint"""
        mock_fal_client = MagicMock(spec=FalClient)
        mock_fal_client.get_result = AsyncMock(return_value={
            "images": [{"url": "https://example.com/image.jpg"}]
        })
        mock_get_client.return_value = mock_fal_client
        
        response = client.get(
            "/api/v1/fal/queue/result",
            params={"response_url": "https://queue.fal.run/response"}
        )
        
        assert response.status_code == 200
        assert "images" in response.json()
        mock_fal_client.get_result.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.api.routes.fal.queue.get_fal_client')
    async def test_cancel_job(self, mock_get_client, client):
        """Test job cancellation endpoint"""
        mock_fal_client = MagicMock(spec=FalClient)
        mock_fal_client.cancel_job = AsyncMock(return_value={
            "cancelled": True
        })
        mock_get_client.return_value = mock_fal_client
        
        response = client.post(
            "/api/v1/fal/queue/cancel",
            json={"cancel_url": "https://queue.fal.run/cancel"}
        )
        
        assert response.status_code == 200
        assert response.json()["cancelled"] is True
        mock_fal_client.cancel_job.assert_called_once()

