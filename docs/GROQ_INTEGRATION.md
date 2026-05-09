# Groq API Integration Guide

## Overview

The DurgasAI backend includes comprehensive integration with Groq's ultra-fast inference API. Groq provides OpenAI-compatible endpoints with low-latency models optimized for speed, making it ideal for real-time applications.

## Features

- **Chat Completions**: OpenAI-compatible chat API with 30+ models
- **Vision Models**: Multimodal analysis with LLaMA 3.2 Vision models
- **Safety & Moderation**: Content safety checks with LLaMA Guard and Prompt Guard
- **Speech-to-Text**: Ultra-fast transcription with Whisper models
- **Intelligent Model Selection**: Automatic model selection based on task requirements
- **Model Registry**: Complete metadata for all available models

## Configuration

Add your Groq API key to `config/config.json`:

```json
{
  "llm": {
    "providers": {
      "groq": {
        "api_key": "your-groq-api-key",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile"
      }
    }
  }
}
```

## Available Models

### Speed-Optimized Models

- `llama-3.1-8b-instant` - Fastest model, 131K context window
- `llama-3.2-1b-preview` - Ultra-lightweight
- `llama-3.2-3b-preview` - Lightweight with good performance

### Standard Chat Models

- `llama-3.3-70b-versatile` - Default, balanced performance
- `llama-3.1-70b-versatile` - High quality with long context
- `llama3-70b-8192` - LLaMA 3, 70B parameters
- `llama3-8b-8192` - LLaMA 3, 8B parameters

### Vision Models

- `llama-3.2-11b-vision-preview` - Fast vision model
- `llama-3.2-90b-vision-preview` - High-quality vision model

### Reasoning Models

- `deepseek-r1-distill-llama-70b` - Complex reasoning and problem-solving
- `qwen-qwq-32b` - Mathematical reasoning

### Specialized Models

- `qwen-2.5-coder-32b` - Code generation and analysis
- `moonshotai/kimi-k2-instruct` - Long context (131K tokens)

### Safety Models

- `meta-llama/llama-guard-4-12b` - Content moderation
- `meta-llama/llama-prompt-guard-2-86m` - Prompt injection detection

### Speech-to-Text Models

- `whisper-large-v3-turbo` - Fast transcription (default)
- `whisper-large-v3` - Standard transcription
- `distil-whisper-large-v3-en` - English-only, fastest

## API Endpoints

### Chat Completions

**POST** `/api/v1/groq/chat/completions`

OpenAI-compatible chat completions endpoint.

**Request:**

```json
{
  "model": "llama-3.3-70b-versatile",
  "messages": [{ "role": "user", "content": "Hello!" }],
  "temperature": 0.7,
  "max_tokens": 1024
}
```

**Response:**

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "llama-3.3-70b-versatile",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 8,
    "total_tokens": 13
  }
}
```

### Vision Analysis

**POST** `/api/v1/groq/vision/analyze`

Analyze a single image with vision models.

**Request:**

```json
{
  "image": "https://example.com/image.jpg",
  "prompt": "What's in this image?",
  "model": "llama-3.2-11b-vision-preview",
  "temperature": 0.7,
  "max_tokens": 1024
}
```

**Response:**

```json
{
  "text": "This image shows a beautiful sunset...",
  "model": "llama-3.2-11b-vision-preview",
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 45,
    "total_tokens": 65
  },
  "finish_reason": "stop"
}
```

**POST** `/api/v1/groq/vision/analyze/upload`

Upload and analyze an image file.

**Form Data:**

- `file`: Image file (multipart/form-data)
- `prompt`: Text prompt (optional, default: "What's in this image?")
- `model`: Vision model (optional)
- `temperature`: Sampling temperature (optional)
- `max_tokens`: Maximum tokens (optional)

**POST** `/api/v1/groq/vision/batch`

Analyze multiple images with a single prompt.

**Request:**

```json
{
  "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
  "prompt": "Compare these images",
  "model": "llama-3.2-11b-vision-preview"
}
```

### Safety & Moderation

**POST** `/api/v1/groq/safety/check`

Check content safety using LLaMA Guard.

**Request:**

```json
{
  "content": "User message to check",
  "check_type": "user"
}
```

**Response:**

```json
{
  "safe": true,
  "categories": [],
  "classification": "safe",
  "risk_level": "none",
  "check_type": "user"
}
```

**POST** `/api/v1/groq/safety/guard-prompt`

Detect prompt injection attacks.

**Request:**

```json
{
  "prompt": "Ignore previous instructions...",
  "model": "meta-llama/llama-prompt-guard-2-86m",
  "threshold": 0.5
}
```

**Response:**

```json
{
  "risk_score": 0.95,
  "is_injection": true,
  "threshold": 0.5,
  "risk_level": "high",
  "model": "meta-llama/llama-prompt-guard-2-86m"
}
```

**POST** `/api/v1/groq/safety/moderate-conversation`

Moderate an entire conversation.

**Request:**

```json
{
  "messages": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi there!" }
  ]
}
```

**Response:**

```json
{
  "safe": true,
  "messages_checked": 2,
  "violations": [],
  "details": [
    {
      "message_index": 0,
      "role": "user",
      "safe": true,
      "classification": "safe"
    }
  ]
}
```

### Model Management

**GET** `/api/v1/groq/models`

List all available models, optionally filtered by category.

**Query Parameters:**

- `category`: Filter by category (chat, vision, safety, reasoning, coding)

**Response:**

```json
{
  "models": [
    {
      "id": "llama-3.3-70b-versatile",
      "category": "chat",
      "context_window": 131072,
      "capabilities": ["chat", "general_purpose", "long_context"],
      "speed_tier": "medium",
      "deprecated": false,
      "use_cases": ["general_chat", "long_context", "complex_analysis"]
    }
  ],
  "total": 30
}
```

**GET** `/api/v1/groq/models/{model_id}`

Get detailed information about a specific model.

**POST** `/api/v1/groq/models/select`

Get recommended model for a task.

**Request:**

```json
{
  "task_type": "vision",
  "complexity": "medium",
  "requirements": {
    "needs_vision": true
  }
}
```

**Response:**

```json
{
  "recommended_model": "llama-3.2-11b-vision-preview",
  "alternatives": ["llama-3.2-90b-vision-preview"],
  "reasoning": "Selected llama-3.2-11b-vision-preview for vision task...",
  "capabilities": {
    "category": "vision",
    "context_window": 8192,
    "capabilities": ["vision", "multimodal", "chat"],
    "speed_tier": "medium"
  }
}
```

### Speech-to-Text

**POST** `/api/v1/groq/transcribe`

Transcribe audio to text.

**Request:**

```json
{
  "audio": "https://example.com/audio.mp3",
  "model": "whisper-large-v3-turbo",
  "language": "en",
  "temperature": 0.0,
  "response_format": "json"
}
```

**Response:**

```json
{
  "text": "Hello, how can I help you today?",
  "model": "whisper-large-v3-turbo",
  "language": "en"
}
```

**POST** `/api/v1/groq/transcribe/upload`

Upload and transcribe an audio file.

**Form Data:**

- `file`: Audio file (multipart/form-data)
- `model`: Whisper model (optional)
- `language`: Language code (optional)
- `temperature`: Sampling temperature (optional)
- `response_format`: Response format - json, text, srt, vtt, verbose_json (optional)

## Usage Examples

### Python Client Example

```python
import httpx

async def analyze_image():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/groq/vision/analyze",
            json={
                "image": "https://example.com/image.jpg",
                "prompt": "Describe this image in detail",
                "model": "llama-3.2-11b-vision-preview"
            }
        )
        return response.json()

async def check_safety():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/groq/safety/check",
            json={
                "content": "User message",
                "check_type": "user"
            }
        )
        return response.json()
```

### cURL Examples

**Vision Analysis:**

```bash
curl -X POST "http://localhost:8000/api/v1/groq/vision/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "https://example.com/image.jpg",
    "prompt": "What is in this image?",
    "model": "llama-3.2-11b-vision-preview"
  }'
```

**Safety Check:**

```bash
curl -X POST "http://localhost:8000/api/v1/groq/safety/check" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, how are you?",
    "check_type": "user"
  }'
```

**Model Selection:**

```bash
curl -X POST "http://localhost:8000/api/v1/groq/models/select" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "reasoning",
    "complexity": "high"
  }'
```

## Model Selection Guide

### Task Types

- **speed**: Quick responses, low latency
  - Recommended: `llama-3.1-8b-instant`
- **reasoning**: Complex problem-solving, math, logic
  - Recommended: `deepseek-r1-distill-llama-70b` (high complexity)
  - Alternative: `qwen-qwq-32b` (medium complexity)
- **vision**: Image analysis, multimodal chat
  - Recommended: `llama-3.2-11b-vision-preview` (fast)
  - Alternative: `llama-3.2-90b-vision-preview` (high quality)
- **coding**: Code generation, debugging, analysis
  - Recommended: `qwen-2.5-coder-32b`
- **long_context**: Document analysis, extended conversations
  - Recommended: `llama-3.3-70b-versatile` (high quality)
  - Alternative: `llama-3.1-8b-instant` (fast)
- **safety**: Content moderation, prompt injection detection
  - Recommended: `meta-llama/llama-guard-4-12b` (content safety)
  - Alternative: `meta-llama/llama-prompt-guard-2-86m` (prompt injection)

### Complexity Levels

- **low**: Simple queries, quick responses
- **medium**: Standard tasks, balanced performance
- **high**: Complex analysis, high-quality output required

## Rate Limits

**Chat Completions:**

- Requests: 1000-14400 per minute (varies by model tier)
- Tokens: 6000-131072 per minute (varies by model)

**Speech-to-Text:**

- Requests: 2000 per minute
- Audio seconds: 7200 per minute

Rate limit information is returned in response headers:

- `x-ratelimit-limit-requests`
- `x-ratelimit-remaining-requests`
- `x-ratelimit-reset-requests`
- `x-ratelimit-limit-tokens`
- `x-ratelimit-remaining-tokens`
- `x-ratelimit-reset-tokens`

## Best Practices

1. **Model Selection**: Use the model selection endpoint to find the optimal model for your task
2. **Vision Tasks**: Use vision models only when analyzing images; standard models are faster for text-only tasks
3. **Safety Checks**: Run safety checks on user input before processing with LLMs
4. **Batch Operations**: Use batch endpoints when processing multiple items
5. **Error Handling**: Check rate limit headers and implement exponential backoff
6. **Caching**: Cache vision analysis results for repeated queries
7. **Streaming**: Use streaming for long responses to improve perceived latency

## Integration with Other Services

### Council System

Vision and reasoning models can be added to the council for multi-model consensus:

```python
from app.services.council import CouncilOrchestrator

council = CouncilOrchestrator()
# Add Groq models to council
council.add_model("groq", "deepseek-r1-distill-llama-70b")
council.add_model("groq", "llama-3.2-90b-vision-preview")
```

### OpenRouter Fallback

If Groq rate limits are hit, automatically fall back to OpenRouter:

```python
try:
    response = await groq_provider.generate(prompt)
except RateLimitError:
    # Fallback to OpenRouter
    response = await openrouter_provider.generate(prompt)
```

## Troubleshooting

### Common Issues

1. **API Key Not Configured**

   - Error: "Groq API key not configured"
   - Solution: Add `groq_api_key` to `config/config.json`

2. **Model Not Found**

   - Error: "Model not found"
   - Solution: Check available models with `GET /api/v1/groq/models`

3. **Rate Limit Exceeded**

   - Error: HTTP 429
   - Solution: Implement rate limiting and retry logic

4. **Vision Model for Non-Vision Task**
   - Error: Poor performance or errors
   - Solution: Use standard chat models for text-only tasks

## Additional Resources

- [Groq API Documentation](https://console.groq.com/docs/quickstart)
- [Available Models](https://console.groq.com/docs/models)
- [Rate Limits](https://console.groq.com/docs/rate-limits)

## Support

For issues or questions:

1. Check the logs in `backend/logs/`
2. Review error messages in API responses
3. Consult Groq's official documentation
4. Check rate limit headers for quota information
