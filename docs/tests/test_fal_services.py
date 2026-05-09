"""
Unit tests for fal.ai generation services
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.fal.client import FalClient
from app.services.fal.queue_manager import QueueManager
from app.services.fal.image_generation import ImageGenerationService
from app.services.fal.audio_generation import AudioGenerationService
from app.services.fal.video_generation import VideoGenerationService


class TestImageGenerationService:
    """Test ImageGenerationService"""
    
    @pytest.fixture
    def client(self):
        """Create mock client"""
        return MagicMock(spec=FalClient)
    
    @pytest.fixture
    def queue_mgr(self):
        """Create mock queue manager"""
        return MagicMock(spec=QueueManager)
    
    @pytest.fixture
    def service(self, client, queue_mgr):
        """Create ImageGenerationService instance"""
        return ImageGenerationService(client, queue_mgr)
    
    @pytest.mark.asyncio
    async def test_generate_flux_pro_wait(self, service, client, queue_mgr):
        """Test flux-pro generation with wait=True"""
        client.submit_job = AsyncMock(return_value={
            "status": "IN_QUEUE",
            "request_id": "test-id",
            "status_url": "https://queue.fal.run/status",
            "response_url": "https://queue.fal.run/response"
        })
        
        queue_mgr.wait_for_completion = AsyncMock(return_value={
            "images": [{"url": "https://example.com/image.jpg"}]
        })
        
        result = await service.generate_flux_pro("test prompt", wait=True)
        
        assert result["job_id"] == "test-id"
        assert "result" in result
        client.submit_job.assert_called_once()
        queue_mgr.wait_for_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_flux_pro_no_wait(self, service, client, queue_mgr):
        """Test flux-pro generation with wait=False"""
        client.submit_job = AsyncMock(return_value={
            "status": "IN_QUEUE",
            "request_id": "test-id"
        })
        
        result = await service.generate_flux_pro("test prompt", wait=False)
        
        assert result["status"] == "IN_QUEUE"
        client.submit_job.assert_called_once()
        queue_mgr.wait_for_completion.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_imagen4(self, service, client, queue_mgr):
        """Test imagen4 generation"""
        client.submit_job = AsyncMock(return_value={
            "status": "IN_QUEUE",
            "request_id": "test-id",
            "status_url": "https://queue.fal.run/status",
            "response_url": "https://queue.fal.run/response"
        })
        
        queue_mgr.wait_for_completion = AsyncMock(return_value={
            "images": [{"url": "https://example.com/image.jpg"}]
        })
        
        result = await service.generate_imagen4("test prompt", variant="preview")
        
        assert result["job_id"] == "test-id"
        client.submit_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_veo3(self, service, client, queue_mgr):
        """Test veo3 generation"""
        client.submit_job = AsyncMock(return_value={
            "status": "IN_QUEUE",
            "request_id": "test-id",
            "status_url": "https://queue.fal.run/status",
            "response_url": "https://queue.fal.run/response"
        })
        
        queue_mgr.wait_for_completion = AsyncMock(return_value={
            "images": [{"url": "https://example.com/image.jpg"}]
        })
        
        result = await service.generate_veo3("test prompt", fast=False)
        
        assert result["job_id"] == "test-id"
        client.submit_job.assert_called_once()


class TestAudioGenerationService:
    """Test AudioGenerationService"""
    
    @pytest.fixture
    def client(self):
        """Create mock client"""
        return MagicMock(spec=FalClient)
    
    @pytest.fixture
    def queue_mgr(self):
        """Create mock queue manager"""
        return MagicMock(spec=QueueManager)
    
    @pytest.fixture
    def service(self, client, queue_mgr):
        """Create AudioGenerationService instance"""
        return AudioGenerationService(client, queue_mgr)
    
    @pytest.mark.asyncio
    async def test_generate_music(self, service, client, queue_mgr):
        """Test music generation"""
        client.submit_job = AsyncMock(return_value={
            "status": "IN_QUEUE",
            "request_id": "test-id",
            "status_url": "https://queue.fal.run/status",
            "response_url": "https://queue.fal.run/response"
        })
        
        queue_mgr.wait_for_completion = AsyncMock(return_value={
            "audio": {"url": "https://example.com/audio.mp3"}
        })
        
        result = await service.generate_music(
            lyrics="[verse]\nTest lyrics",
            genres="pop rock"
        )
        
        assert result["job_id"] == "test-id"
        client.submit_job.assert_called_once()
        assert "yue" in client.submit_job.call_args[0][0]


class TestVideoGenerationService:
    """Test VideoGenerationService"""
    
    @pytest.fixture
    def client(self):
        """Create mock client"""
        return MagicMock(spec=FalClient)
    
    @pytest.fixture
    def queue_mgr(self):
        """Create mock queue manager"""
        return MagicMock(spec=QueueManager)
    
    @pytest.fixture
    def service(self, client, queue_mgr):
        """Create VideoGenerationService instance"""
        return VideoGenerationService(client, queue_mgr)
    
    @pytest.mark.asyncio
    async def test_generate_from_text(self, service, client, queue_mgr):
        """Test text-to-video generation"""
        client.submit_job = AsyncMock(return_value={
            "status": "IN_QUEUE",
            "request_id": "test-id",
            "status_url": "https://queue.fal.run/status",
            "response_url": "https://queue.fal.run/response"
        })
        
        queue_mgr.wait_for_completion = AsyncMock(return_value={
            "video": {"url": "https://example.com/video.mp4"}
        })
        
        result = await service.generate_from_text("test prompt")
        
        assert result["job_id"] == "test-id"
        client.submit_job.assert_called_once()
        assert "veo2" in client.submit_job.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_generate_from_image(self, service, client, queue_mgr):
        """Test image-to-video generation"""
        client.submit_job = AsyncMock(return_value={
            "status": "IN_QUEUE",
            "request_id": "test-id",
            "status_url": "https://queue.fal.run/status",
            "response_url": "https://queue.fal.run/response"
        })
        
        queue_mgr.wait_for_completion = AsyncMock(return_value={
            "video": {"url": "https://example.com/video.mp4"}
        })
        
        result = await service.generate_from_image(
            "test prompt",
            "https://example.com/image.jpg"
        )
        
        assert result["job_id"] == "test-id"
        client.submit_job.assert_called_once()
        call_args = client.submit_job.call_args[0][1]
        assert call_args["image_url"] == "https://example.com/image.jpg"

