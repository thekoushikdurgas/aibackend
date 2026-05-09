"""
Unit tests for fal.ai client
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.fal.client import FalClient


class TestFalClient:
    """Test FalClient"""
    
    @pytest.fixture
    def client(self):
        """Create FalClient instance"""
        return FalClient(api_key="test-api-key", timeout=30.0)
    
    def test_init_with_api_key(self):
        """Test client initialization with API key"""
        client = FalClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.base_url == "https://queue.fal.run/fal-ai"
    
    def test_init_without_api_key(self):
        """Test client initialization without API key"""
        with patch('app.services.fal.client.settings') as mock_settings:
            mock_settings.fal_api_key = None
            mock_settings.fal_base_url = "https://queue.fal.run/fal-ai"
            mock_settings.fal_default_timeout = 600.0
            client = FalClient()
            assert client.api_key is None
    
    def test_get_headers(self, client):
        """Test header generation"""
        headers = client._get_headers()
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" in headers
        assert headers["Authorization"] == "Key test-api-key"
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_submit_job_success(self, mock_client_class, client):
        """Test successful job submission"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "IN_QUEUE",
            "request_id": "test-request-id",
            "status_url": "https://queue.fal.run/status",
            "response_url": "https://queue.fal.run/response",
            "cancel_url": "https://queue.fal.run/cancel"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        result = await client.submit_job("flux-pro/v1.1-ultra", {"prompt": "test"})
        
        assert result["status"] == "IN_QUEUE"
        assert result["request_id"] == "test-request-id"
        mock_client_instance.post.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_submit_job_missing_api_key(self, mock_client_class):
        """Test job submission without API key"""
        client = FalClient(api_key=None)
        
        with pytest.raises(ValueError, match="API key not configured"):
            await client.submit_job("flux-pro/v1.1-ultra", {"prompt": "test"})
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_status_success(self, mock_client_class, client):
        """Test successful status check"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "COMPLETED",
            "request_id": "test-request-id"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        result = await client.get_status("https://queue.fal.run/status")
        
        assert result["status"] == "COMPLETED"
        mock_client_instance.get.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_result_success(self, mock_client_class, client):
        """Test successful result retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "images": [{"url": "https://example.com/image.jpg"}]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        result = await client.get_result("https://queue.fal.run/response")
        
        assert "images" in result
        mock_client_instance.get.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_cancel_job_success(self, mock_client_class, client):
        """Test successful job cancellation"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"cancelled": True}
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        result = await client.cancel_job("https://queue.fal.run/cancel")
        
        assert result["cancelled"] is True
        mock_client_instance.post.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_submit_job_http_error(self, mock_client_class, client):
        """Test job submission with HTTP error"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        ))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        with pytest.raises(httpx.HTTPStatusError):
            await client.submit_job("flux-pro/v1.1-ultra", {"prompt": "test"})

