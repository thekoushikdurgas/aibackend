"""
Comprehensive tests for ElevenLabs services
Text-to-Speech, Voice Management, and Model Management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64

from app.services.multimodal.elevenlabs_tts import ElevenLabsTextToSpeechService


@pytest.fixture
def mock_voices_response():
    """Mock httpx response for voices list"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "voices": [
            {
                "voice_id": "pMsXgVXv3BLzUgSXRplE",
                "name": "Rachel",
                "category": "premade",
                "labels": {
                    "accent": "American",
                    "description": "expressive",
                    "age": "middle-aged",
                    "gender": "female",
                    "use_case": "social media"
                },
                "preview_url": "https://example.com/preview.mp3",
                "fine_tuning": {
                    "state": {
                        "eleven_multilingual_v2": "fine_tuned"
                    }
                },
                "high_quality_base_model_ids": ["eleven_multilingual_v2"],
                "is_owner": False,
                "is_legacy": False,
                "is_mixed": False
            }
        ]
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_models_response():
    """Mock httpx response for models list"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = [
        {
            "model_id": "eleven_multilingual_v2",
            "name": "Eleven Multilingual v2",
            "description": "High quality model",
            "can_be_finetuned": True,
            "can_do_text_to_speech": True,
            "can_do_voice_conversion": False,
            "can_use_style": True,
            "can_use_speaker_boost": True,
            "languages": [{"language_id": "en", "name": "English"}],
            "maximum_text_length_per_request": 10000,
            "model_rates": {"character_cost_multiplier": 1.0},
            "concurrency_group": "standard"
        }
    ]
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_tts_response():
    """Mock httpx response for text-to-speech"""
    response = MagicMock()
    response.status_code = 200
    response.content = b"fake_audio_bytes"
    response.headers = {"content-type": "audio/mpeg"}
    response.raise_for_status = MagicMock()
    return response


class TestElevenLabsTextToSpeechService:
    """Tests for ElevenLabsTextToSpeechService"""
    
    @pytest.mark.asyncio
    async def test_list_voices(self, mock_voices_response):
        """Test listing all voices"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_voices_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            voices = await service.list_voices()
            
            assert len(voices) == 1
            assert voices[0]["voice_id"] == "pMsXgVXv3BLzUgSXRplE"
            assert voices[0]["name"] == "Rachel"
    
    @pytest.mark.asyncio
    async def test_list_voices_caching(self, mock_voices_response):
        """Test that voices are cached"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_voices_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            
            # First call
            voices1 = await service.list_voices()
            # Second call should use cache
            voices2 = await service.list_voices()
            
            # Should only call API once
            assert mock_get.call_count == 1
            assert len(voices1) == len(voices2)
    
    @pytest.mark.asyncio
    async def test_get_voice(self, mock_voices_response):
        """Test getting a specific voice"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_voices_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            voice = await service.get_voice("pMsXgVXv3BLzUgSXRplE")
            
            assert voice is not None
            assert voice["voice_id"] == "pMsXgVXv3BLzUgSXRplE"
            assert voice["name"] == "Rachel"
    
    @pytest.mark.asyncio
    async def test_get_voice_not_found(self, mock_voices_response):
        """Test getting a non-existent voice"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_voices_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            voice = await service.get_voice("nonexistent")
            
            assert voice is None
    
    @pytest.mark.asyncio
    async def test_filter_voices_by_gender(self, mock_voices_response):
        """Test filtering voices by gender"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_voices_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            voices = await service.filter_voices(gender="female")
            
            assert len(voices) == 1
            assert voices[0]["labels"]["gender"] == "female"
    
    @pytest.mark.asyncio
    async def test_filter_voices_no_match(self, mock_voices_response):
        """Test filtering voices with no matches"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_voices_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            voices = await service.filter_voices(gender="male")
            
            assert len(voices) == 0
    
    @pytest.mark.asyncio
    async def test_list_models(self, mock_models_response):
        """Test listing all models"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_models_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            models = await service.list_models()
            
            assert len(models) == 1
            assert models[0]["model_id"] == "eleven_multilingual_v2"
            assert models[0]["can_do_text_to_speech"] is True
    
    @pytest.mark.asyncio
    async def test_get_model(self, mock_models_response):
        """Test getting a specific model"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_models_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            model = await service.get_model("eleven_multilingual_v2")
            
            assert model is not None
            assert model["model_id"] == "eleven_multilingual_v2"
    
    @pytest.mark.asyncio
    async def test_validate_text_length_valid(self, mock_models_response, mock_voices_response):
        """Test text length validation with valid text"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[mock_models_response, mock_voices_response])
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            result = await service.validate_text_length("Short text", "eleven_multilingual_v2")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_text_length_invalid(self, mock_models_response):
        """Test text length validation with text exceeding limit"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_models_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            long_text = "x" * 20000  # Exceeds 10000 limit
            
            with pytest.raises(Exception) as exc_info:
                await service.validate_text_length(long_text, "eleven_multilingual_v2")
            
            assert "exceeds model limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_generate_tts(self, mock_tts_response, mock_voices_response, mock_models_response):
        """Test TTS generation"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[mock_voices_response, mock_models_response])
            mock_post = AsyncMock(return_value=mock_tts_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            result = await service.generate(
                text="Hello, this is a test.",
                voice_id="pMsXgVXv3BLzUgSXRplE",
                model_id="eleven_multilingual_v2"
            )
            
            assert result["voice_id"] == "pMsXgVXv3BLzUgSXRplE"
            assert result["model_id"] == "eleven_multilingual_v2"
            assert result["text"] == "Hello, this is a test."
            assert result["audio_base64"] is not None
            assert base64.b64decode(result["audio_base64"]) == b"fake_audio_bytes"
    
    @pytest.mark.asyncio
    async def test_generate_tts_with_voice_settings(self, mock_tts_response, mock_voices_response, mock_models_response):
        """Test TTS generation with custom voice settings"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[mock_voices_response, mock_models_response])
            mock_post = AsyncMock(return_value=mock_tts_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            result = await service.generate(
                text="Test text",
                voice_id="pMsXgVXv3BLzUgSXRplE",
                voice_settings={
                    "stability": 0.7,
                    "similarity_boost": 0.8,
                    "use_speaker_boost": True
                }
            )
            
            assert result["audio_base64"] is not None
            # Verify voice_settings were passed to API
            call_args = mock_post.call_args
            assert "voice_settings" in call_args[1]["json"]
    
    @pytest.mark.asyncio
    async def test_generate_tts_invalid_voice(self, mock_voices_response):
        """Test TTS generation with invalid voice ID"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_voices_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            
            with pytest.raises(Exception) as exc_info:
                await service.generate(
                    text="Test",
                    voice_id="invalid_voice_id"
                )
            
            assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_generate_tts_no_api_key(self):
        """Test TTS generation without API key"""
        service = ElevenLabsTextToSpeechService(api_key=None)
        
        with pytest.raises(Exception) as exc_info:
            await service.generate(text="Test")
        
        assert "api key" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_generate_tts_api_error(self, mock_voices_response, mock_models_response):
        """Test TTS generation with API error"""
        error_response = MagicMock()
        error_response.status_code = 401
        error_response.text = "Unauthorized"
        error_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[mock_voices_response, mock_models_response])
            mock_post = AsyncMock(return_value=error_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            
            with pytest.raises(Exception) as exc_info:
                await service.generate(text="Test")
            
            assert "api key" in str(exc_info.value).lower() or "unauthorized" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_generate_tts_rate_limit(self, mock_voices_response, mock_models_response):
        """Test TTS generation with rate limit error"""
        error_response = MagicMock()
        error_response.status_code = 429
        error_response.text = "Rate limit exceeded"
        error_response.raise_for_status.side_effect = Exception("429 Rate Limit")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[mock_voices_response, mock_models_response])
            mock_post = AsyncMock(return_value=error_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            
            with pytest.raises(Exception) as exc_info:
                await service.generate(text="Test")
            
            assert "rate limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_generate_stream(self, mock_voices_response, mock_models_response):
        """Test streaming TTS generation"""
        stream_response = MagicMock()
        stream_response.status_code = 200
        stream_response.raise_for_status = MagicMock()
        stream_response.aiter_bytes = AsyncMock(return_value=iter([b"chunk1", b"chunk2", b"chunk3"]))
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[mock_voices_response, mock_models_response])
            mock_stream = AsyncMock(return_value=stream_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            mock_client.return_value.__aenter__.return_value.stream = mock_stream
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            
            chunks = []
            async for chunk in service.generate_stream(
                text="Test streaming",
                voice_id="pMsXgVXv3BLzUgSXRplE"
            ):
                chunks.append(chunk)
            
            assert len(chunks) == 3
            assert chunks[0] == b"chunk1"
    
    @pytest.mark.asyncio
    async def test_list_voices_api_error(self):
        """Test handling API errors when listing voices"""
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        error_response.raise_for_status.side_effect = Exception("500 Internal Server Error")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=error_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            
            with pytest.raises(Exception):
                await service.list_voices()
    
    @pytest.mark.asyncio
    async def test_list_models_api_error(self):
        """Test handling API errors when listing models"""
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        error_response.raise_for_status.side_effect = Exception("500 Internal Server Error")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=error_response)
            
            service = ElevenLabsTextToSpeechService(api_key="test-key")
            
            with pytest.raises(Exception):
                await service.list_models()

