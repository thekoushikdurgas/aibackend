"""
Comprehensive tests for Deepgram services
Speech-to-Text, Text-to-Speech, and Text Summarization
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64

from app.services.multimodal.deepgram_speech import DeepgramSpeechToTextService
from app.services.multimodal.deepgram_tts import DeepgramTextToSpeechService
from app.services.nlp.deepgram_text import DeepgramTextService


@pytest.fixture
def mock_stt_response():
    """Mock httpx response for speech-to-text"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "metadata": {
            "transaction_key": "deprecated",
            "request_id": "test-request-id",
            "sha256": "test-hash",
            "created": "2024-01-01T00:00:00.000Z",
            "duration": 25.93,
            "channels": 1,
            "models": ["test-model-uuid"],
            "model_info": {
                "test-model-uuid": {
                    "name": "nova-2",
                    "version": "2024-01-01.0000",
                    "arch": "nova-2"
                }
            }
        },
        "results": {
            "channels": [{
                "alternatives": [{
                    "transcript": "Hello, this is a test transcription.",
                    "confidence": 0.99,
                    "words": [
                        {
                            "word": "hello",
                            "start": 0.0,
                            "end": 0.5,
                            "confidence": 0.99
                        },
                        {
                            "word": "this",
                            "start": 0.5,
                            "end": 0.8,
                            "confidence": 0.98
                        }
                    ]
                }]
            }]
        }
    }
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


@pytest.fixture
def mock_summarization_response():
    """Mock httpx response for text summarization"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "summary": "This is a summarized version of the text."
    }
    response.raise_for_status = MagicMock()
    return response


class TestDeepgramSpeechToTextService:
    """Tests for DeepgramSpeechToTextService"""
    
    @pytest.mark.asyncio
    async def test_transcribe_with_url(self, mock_stt_response):
        """Test transcription with remote URL"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_stt_response)
            
            service = DeepgramSpeechToTextService(api_key="test-key")
            result = await service.transcribe(
                audio="https://example.com/audio.wav",
                model="nova-2"
            )
            
            assert result["transcript"] == "Hello, this is a test transcription."
            assert result["model"] == "nova-2"
            assert result["confidence"] == 0.99
            assert result["duration"] == 25.93
    
    @pytest.mark.asyncio
    async def test_transcribe_with_bytes(self, mock_stt_response):
        """Test transcription with audio bytes"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_stt_response)
            
            service = DeepgramSpeechToTextService(api_key="test-key")
            audio_bytes = b"fake_audio_data"
            result = await service.transcribe(
                audio=audio_bytes,
                model="nova-2",
                return_timestamps=True
            )
            
            assert result["transcript"] == "Hello, this is a test transcription."
            assert result["words"] is not None
            assert len(result["words"]) == 2
    
    @pytest.mark.asyncio
    async def test_transcribe_with_base64(self, mock_stt_response):
        """Test transcription with base64-encoded audio"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_stt_response)
            
            service = DeepgramSpeechToTextService(api_key="test-key")
            audio_base64 = base64.b64encode(b"fake_audio_data").decode("utf-8")
            result = await service.transcribe(audio=audio_base64)
            
            assert result["transcript"] == "Hello, this is a test transcription."
    
    @pytest.mark.asyncio
    async def test_transcribe_with_options(self, mock_stt_response):
        """Test transcription with various options"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_stt_response)
            
            service = DeepgramSpeechToTextService(api_key="test-key")
            result = await service.transcribe(
                audio="https://example.com/audio.wav",
                punctuate=True,
                diarize=True,
                smart_format=True,
                detect_language=True
            )
            
            assert result["transcript"] == "Hello, this is a test transcription."
    
    @pytest.mark.asyncio
    async def test_transcribe_api_error(self):
        """Test transcription with API error"""
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {"err_msg": "Invalid request"}
        error_response.raise_for_status.side_effect = Exception("Bad Request")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=error_response)
            
            service = DeepgramSpeechToTextService(api_key="test-key")
            
            with pytest.raises(Exception) as exc_info:
                await service.transcribe(audio="https://example.com/audio.wav")
            
            assert "Deepgram speech-to-text API error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing available models"""
        service = DeepgramSpeechToTextService(api_key="test-key")
        models = await service.list_models()
        
        assert isinstance(models, list)
        assert "nova-2" in models
        assert "nova-3" in models
        assert "whisper" in models
    
    def test_get_model_info(self):
        """Test getting model information"""
        service = DeepgramSpeechToTextService(api_key="test-key")
        info = service.get_model_info("nova-2")
        
        assert info["name"] == "Nova 2"
        assert "description" in info
        assert "use_case" in info


class TestDeepgramTextToSpeechService:
    """Tests for DeepgramTextToSpeechService"""
    
    @pytest.mark.asyncio
    async def test_generate_speech(self, mock_tts_response):
        """Test generating speech from text"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_tts_response)
            
            service = DeepgramTextToSpeechService(api_key="test-key")
            result = await service.generate(
                text="Hello, this is a test.",
                model="aura-asteria-en"
            )
            
            assert result["model"] == "aura-asteria-en"
            assert result["text"] == "Hello, this is a test."
            assert result["audio_base64"] is not None
            assert result["content_type"] == "audio/mpeg"
    
    @pytest.mark.asyncio
    async def test_generate_with_options(self, mock_tts_response):
        """Test generating speech with encoding options"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_tts_response)
            
            service = DeepgramTextToSpeechService(api_key="test-key")
            result = await service.generate(
                text="Test text",
                encoding="wav",
                sample_rate=48000
            )
            
            assert result["audio_base64"] is not None
    
    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generating speech with API error"""
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.text = "Invalid request"
        error_response.raise_for_status.side_effect = Exception("Bad Request")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=error_response)
            
            service = DeepgramTextToSpeechService(api_key="test-key")
            
            with pytest.raises(Exception) as exc_info:
                await service.generate(text="Test")
            
            assert "Deepgram text-to-speech API error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_voices(self):
        """Test listing available voices"""
        service = DeepgramTextToSpeechService(api_key="test-key")
        voices = await service.list_voices()
        
        assert isinstance(voices, list)
        assert "aura-asteria-en" in voices
        assert "aura-luna-en" in voices
        assert len(voices) == 12
    
    def test_get_voice_info(self):
        """Test getting voice information"""
        service = DeepgramTextToSpeechService(api_key="test-key")
        info = service.get_voice_info("aura-asteria-en")
        
        assert info["name"] == "Asteria"
        assert "gender" in info
        assert "description" in info


class TestDeepgramTextService:
    """Tests for DeepgramTextService"""
    
    @pytest.mark.asyncio
    async def test_summarize_text(self, mock_summarization_response):
        """Test text summarization"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_summarization_response)
            
            service = DeepgramTextService(api_key="test-key")
            result = await service.summarize(
                text="This is a long text that needs to be summarized. " * 10,
                language="en"
            )
            
            assert result["summary"] == "This is a summarized version of the text."
            assert result["language"] == "en"
            assert result["original_length"] > 0
            assert result["summary_length"] > 0
    
    @pytest.mark.asyncio
    async def test_summarize_with_max_length(self, mock_summarization_response):
        """Test text summarization with max length"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_summarization_response)
            
            service = DeepgramTextService(api_key="test-key")
            result = await service.summarize(
                text="Long text here",
                language="en",
                max_length=100
            )
            
            assert result["summary"] is not None
    
    @pytest.mark.asyncio
    async def test_summarize_api_error(self):
        """Test summarization with API error"""
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {"err_msg": "Invalid request"}
        error_response.raise_for_status.side_effect = Exception("Bad Request")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=error_response)
            
            service = DeepgramTextService(api_key="test-key")
            
            with pytest.raises(Exception) as exc_info:
                await service.summarize(text="Test text")
            
            assert "Deepgram text summarization API error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_summarize_without_api_key(self):
        """Test summarization without API key"""
        service = DeepgramTextService(api_key=None)
        
        with pytest.raises(Exception) as exc_info:
            await service.summarize(text="Test")
        
        assert "Deepgram API key not configured" in str(exc_info.value)


class TestDeepgramServiceInitialization:
    """Tests for service initialization"""
    
    def test_stt_service_init_without_key(self):
        """Test STT service initialization without API key"""
        service = DeepgramSpeechToTextService(api_key=None)
        assert service.api_key is None
    
    def test_tts_service_init_without_key(self):
        """Test TTS service initialization without API key"""
        service = DeepgramTextToSpeechService(api_key=None)
        assert service.api_key is None
    
    def test_text_service_init_without_key(self):
        """Test Text service initialization without API key"""
        service = DeepgramTextService(api_key=None)
        assert service.api_key is None
    
    def test_stt_service_init_with_custom_config(self):
        """Test STT service with custom configuration"""
        service = DeepgramSpeechToTextService(
            api_key="custom-key",
            model="nova-3",
            base_url="https://custom.url",
            timeout=60.0
        )
        
        assert service.api_key == "custom-key"
        assert service.model == "nova-3"
        assert service.base_url == "https://custom.url"
        assert service.timeout == 60.0
