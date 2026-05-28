# Deepgram API Integration Documentation

## Overview

The Deepgram API integration provides three main capabilities:

1. **Speech-to-Text** - Transcribe audio files to text with high accuracy
2. **Text-to-Speech** - Convert text to natural-sounding speech using Aura voices
3. **Text Summarization** - Summarize long text documents

## Configuration

Add your Deepgram API key to `config/config.json`:

```json
{
  "deepgram": {
    "api_key": "YOUR_DEEPGRAM_API_KEY",
    "base_url": "https://api.deepgram.com/v1",
    "default_stt_model": "nova-2",
    "default_tts_model": "aura-asteria-en",
    "timeout": 120.0
  }
}
```

**Note:** For production, store the API key in an environment variable instead of the config file.

## API Endpoints

All endpoints are prefixed with `/api/v1/deepgram`

### Speech-to-Text

#### POST `/api/v1/deepgram/transcribe`

Transcribe audio from URL or base64-encoded audio.

**Request Body:**

```json
{
  "audio": "https://example.com/audio.wav",
  "model": "nova-2",
  "language": "en",
  "punctuate": true,
  "diarize": false,
  "smart_format": true,
  "detect_language": false,
  "return_timestamps": false
}
```

**Response:**

```json
{
  "transcript": "Hello, this is a test transcription.",
  "confidence": 0.99,
  "words": [
    {
      "word": "hello",
      "start": 0.0,
      "end": 0.5,
      "confidence": 0.99
    }
  ],
  "model": "nova-2",
  "model_info": {
    "name": "Nova 2",
    "version": "2024-01-01.0000",
    "arch": "nova-2"
  },
  "duration": 25.93,
  "channels": 1,
  "language": "en",
  "request_id": "test-request-id"
}
```

#### POST `/api/v1/deepgram/transcribe/upload`

Transcribe an uploaded audio file.

**Request:** Multipart form data

- `file`: Audio file (max 10MB)
- `model`: Optional model name
- `language`: Optional language code
- `punctuate`: Boolean (default: true)
- `diarize`: Boolean (default: false)
- `smart_format`: Boolean (default: true)
- `detect_language`: Boolean (default: false)
- `return_timestamps`: Boolean (default: false)

**Response:** Same as `/transcribe` endpoint

### Text-to-Speech

#### POST `/api/v1/deepgram/speak`

Convert text to speech using Deepgram's Aura voices.

**Request Body:**

```json
{
  "text": "Hello, how can I help you today?",
  "model": "aura-asteria-en",
  "encoding": "mp3",
  "sample_rate": 24000
}
```

**Response:**

```json
{
  "audio_base64": "base64_encoded_audio_data...",
  "audio_url": null,
  "model": "aura-asteria-en",
  "duration_ms": 2500,
  "content_type": "audio/mpeg",
  "text": "Hello, how can I help you today?"
}
```

### Text Summarization

#### POST `/api/v1/deepgram/summarize`

Summarize long text documents.

**Request Body:**

```json
{
  "text": "Long text to summarize...",
  "language": "en",
  "max_length": 200
}
```

**Response:**

```json
{
  "summary": "Summarized version of the text.",
  "original_text": "Long text to summarize...",
  "model": null,
  "language": "en",
  "original_length": 500,
  "summary_length": 50
}
```

### Model Information

#### GET `/api/v1/deepgram/models`

List available models and voices.

**Query Parameters:**

- `category`: Optional filter - `stt` (speech-to-text) or `tts` (text-to-speech)

**Response:**

```json
{
  "speech_to_text": {
    "models": ["nova-3", "nova-2", "enhanced", "base", "whisper"],
    "model_info": {
      "nova-2": {
        "name": "Nova 2",
        "description": "High accuracy, balanced performance",
        "use_case": "General transcription"
      }
    }
  },
  "text_to_speech": {
    "voices": ["aura-asteria-en", "aura-luna-en", ...],
    "voice_info": {
      "aura-asteria-en": {
        "name": "Asteria",
        "gender": "female",
        "description": "Warm and friendly female voice"
      }
    }
  }
}
```

## Available Models

### Speech-to-Text Models

| Model                | Description                         | Use Case                                       |
| -------------------- | ----------------------------------- | ---------------------------------------------- |
| `nova-3`             | Latest and most accurate            | General transcription, highest accuracy        |
| `nova-2`             | High accuracy, balanced performance | General transcription (default)                |
| `nova-2-phonecall`   | Optimized for phone calls           | Phone calls, telephony                         |
| `nova`               | Original Nova model                 | General transcription                          |
| `nova-phonecall`     | Nova optimized for phone calls      | Phone calls                                    |
| `enhanced`           | Enhanced accuracy model             | General transcription                          |
| `enhanced-phonecall` | Enhanced model for phone calls      | Phone calls                                    |
| `base`               | Base model, cost-effective          | Cost-sensitive applications                    |
| `base-phonecall`     | Base model for phone calls          | Phone calls, cost-sensitive                    |
| `whisper`            | OpenAI Whisper model                | General transcription, open-source alternative |

### Text-to-Speech Voices

| Voice             | Gender | Description                 |
| ----------------- | ------ | --------------------------- |
| `aura-asteria-en` | Female | Warm and friendly (default) |
| `aura-luna-en`    | Female | Clear and professional      |
| `aura-stella-en`  | Female | Energetic and expressive    |
| `aura-athena-en`  | Female | Confident and authoritative |
| `aura-hera-en`    | Female | Sophisticated and elegant   |
| `aura-orion-en`   | Male   | Deep and resonant           |
| `aura-arcas-en`   | Male   | Warm and friendly           |
| `aura-perseus-en` | Male   | Strong and confident        |
| `aura-angus-en`   | Male   | Professional and clear      |
| `aura-orpheus-en` | Male   | Smooth and expressive       |
| `aura-helios-en`  | Male   | Bright and energetic        |
| `aura-zeus-en`    | Male   | Powerful and authoritative  |

## Usage Examples

### Python Example - Speech-to-Text

```python
import httpx

async def transcribe_audio():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/deepgram/transcribe",
            json={
                "audio": "https://dpgr.am/spacewalk.wav",
                "model": "nova-2",
                "return_timestamps": True
            }
        )
        result = response.json()
        print(result["transcript"])
```

### Python Example - Text-to-Speech

```python
import httpx
import base64

async def generate_speech():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/deepgram/speak",
            json={
                "text": "Hello, how can I help you today?",
                "model": "aura-asteria-en"
            }
        )
        result = response.json()

        # Decode and save audio
        audio_bytes = base64.b64decode(result["audio_base64"])
        with open("output.mp3", "wb") as f:
            f.write(audio_bytes)
```

### cURL Example - Speech-to-Text

```bash
curl -X POST "http://localhost:8000/api/v1/deepgram/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "audio": "https://dpgr.am/spacewalk.wav",
    "model": "nova-2",
    "return_timestamps": true
  }'
```

### cURL Example - File Upload

```bash
curl -X POST "http://localhost:8000/api/v1/deepgram/transcribe/upload" \
  -F "file=@audio.wav" \
  -F "model=nova-2" \
  -F "return_timestamps=true"
```

## Advanced Features

### Speaker Diarization

Identify different speakers in the audio:

```json
{
  "audio": "https://example.com/meeting.wav",
  "diarize": true
}
```

### Smart Formatting

Automatically format numbers, dates, and other entities:

```json
{
  "audio": "https://example.com/audio.wav",
  "smart_format": true
}
```

### Language Detection

Automatically detect the language:

```json
{
  "audio": "https://example.com/audio.wav",
  "detect_language": true
}
```

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK` - Success
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Missing or invalid API key
- `413 Payload Too Large` - File size exceeds limit (10MB)
- `500 Internal Server Error` - Server error

Error response format:

```json
{
  "detail": "Error message description"
}
```

## Rate Limits

Deepgram API rate limits depend on your plan. Check your Deepgram dashboard for current limits.

## Best Practices

1. **Model Selection:**

   - Use `nova-2` or `nova-3` for general transcription
   - Use `*-phonecall` models for phone call audio
   - Use `base` models for cost-sensitive applications

2. **Audio Format:**

   - Supported formats: WAV, MP3, M4A, FLAC, OGG
   - Recommended: WAV or MP3 for best compatibility
   - Maximum file size: 10MB

3. **Performance:**

   - Use remote URLs for large files instead of base64
   - Enable `smart_format` for better readability
   - Use `return_timestamps` only when needed

4. **Security:**
   - Store API keys in environment variables
   - Validate file sizes before upload
   - Sanitize user inputs

## Troubleshooting

### Common Issues

1. **API Key Not Configured**

   - Ensure `deepgram_api_key` is set in config.json or environment variable
   - Check that the API key is valid

2. **File Size Exceeds Limit**

   - Maximum file size is 10MB
   - Use remote URLs for larger files
   - Compress audio files before upload

3. **Transcription Returns Empty**

   - Check audio quality and format
   - Verify language parameter matches audio language
   - Try different models

4. **TTS Audio Not Playing**
   - Verify audio_base64 is properly decoded
   - Check content_type matches expected format
   - Ensure audio player supports the encoding format

## Additional Resources

- [Deepgram API Documentation](https://developers.deepgram.com/reference/deepgram-api-overview)
- [Deepgram Models Guide](https://developers.deepgram.com/docs/model)
- [Deepgram Aura Voices](https://developers.deepgram.com/docs/aura-voices)
