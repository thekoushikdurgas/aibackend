# Hyperbolic API Integration

## Overview

The Hyperbolic API integration provides access to 23 AI models across text generation, vision, audio, and image generation capabilities. Hyperbolic is "the open access AI cloud" offering OpenAI-compatible endpoints.

## Configuration

### Setup

1. Add your Hyperbolic API key to `config/config.json`:

```json
{
  "llm": {
    "providers": {
      "hyperbolic": {
        "api_key": "your-api-key-here",
        "base_url": "https://api.hyperbolic.xyz/v1",
        "default_text_model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "default_vision_model": "meta-llama/Llama-3.2-90B-Vision-Instruct",
        "default_image_model": "FLUX.1-dev",
        "timeout": 120.0
      }
    }
  }
}
```

2. Get your API key from [https://app.hyperbolic.xyz/](https://app.hyperbolic.xyz/)

## Available Models

### Text Generation Models (12 models)

- **DeepSeek Models**:

  - `deepseek-ai/DeepSeek-R1-Zero` - Reasoning model
  - `deepseek-ai/DeepSeek-R1` - Reasoning model
  - `deepseek-ai/DeepSeek-V2.5` - Chat and code
  - `deepseek-ai/DeepSeek-V3` - Advanced reasoning, chat, and code

- **Meta Llama Models**:

  - `meta-llama/Llama-3.2-3B-Instruct` - Small, efficient
  - `meta-llama/Meta-Llama-3-70B-Instruct` - Balanced performance
  - `meta-llama/Meta-Llama-3.1-8B-Instruct` - Medium size
  - `meta-llama/Meta-Llama-3.1-70B-Instruct` - High performance (default)
  - `meta-llama/Meta-Llama-3.1-405B-Instruct` - Largest, most capable
  - `meta-llama/Llama-3.3-70B-Instruct` - Latest 70B model

- **Other Models**:
  - `NousResearch/Hermes-3-Llama-3.1-70B` - Fine-tuned for instruction following
  - `Qwen/Qwen2.5-72B-Instruct` - Multilingual, code-capable

### Vision Models (4 models)

- `meta-llama/Llama-3.2-90B-Vision-Instruct` - Large vision model (default)
- `mistralai/Pixtral-12B-2409` - Efficient vision model
- `Qwen/Qwen2-VL-7B-Instruct` - Small vision model
- `Qwen/Qwen2-VL-72B-Instruct` - Large vision model

### Image Generation Models (6 models)

- `FLUX.1-dev` - High-quality image generation (default)
- `SD1.5` - Stable Diffusion 1.5
- `SD2` - Stable Diffusion 2
- `SDXL1.0-base` - Stable Diffusion XL base
- `SDXL-turbo` - Fast SDXL generation
- `SSD` - Super-fast generation

### Audio Generation Models (1 model)

- `Melo TTS` - Text-to-speech with multiple language support

## API Endpoints

### Base URL

All endpoints are available at `/api/v1/hyperbolic/`

### Text Generation

#### POST `/chat/completions`

Chat completions for text generation.

**Request:**

```json
{
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "Hello!" }
  ],
  "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
  "temperature": 0.7,
  "max_tokens": 2048,
  "top_p": 0.9,
  "presence_penalty": 0.0,
  "stream": false
}
```

**Response:**

```json
{
  "id": "chat-123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  }
}
```

### Vision Completions

#### POST `/vision/completions`

Multimodal completions with image understanding.

**Request:**

```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "What is in this image?" },
        {
          "type": "image_url",
          "image_url": {
            "url": "https://example.com/image.jpg"
          }
        }
      ]
    }
  ],
  "model": "meta-llama/Llama-3.2-90B-Vision-Instruct",
  "max_tokens": 2048,
  "temperature": 0.7
}
```

### Audio Generation

#### POST `/audio/generation`

Text-to-speech generation.

**Request:**

```json
{
  "text": "Hello, world!",
  "speed": 1.0
}
```

**Response:** Binary audio data (WAV format)

### Image Generation

#### POST `/image/generation`

Text-to-image generation.

**Request:**

```json
{
  "prompt": "A beautiful sunset over mountains",
  "model_name": "FLUX.1-dev",
  "steps": 30,
  "cfg_scale": 5.0,
  "height": 1024,
  "width": 1024,
  "enable_refiner": false,
  "backend": "auto"
}
```

**Response:**

```json
{
  "image": "base64_encoded_image_data",
  "model": "FLUX.1-dev"
}
```

### Model Listing

#### GET `/models`

List all available models.

**Response:**

```json
{
  "text": ["model1", "model2", ...],
  "vision": ["model1", "model2", ...],
  "image": ["model1", "model2", ...],
  "audio": ["Melo TTS"],
  "total": 23
}
```

#### GET `/models/text`

List text generation models.

#### GET `/models/vision`

List vision models.

#### GET `/models/image`

List image generation models.

#### GET `/models/audio`

List audio generation models.

#### GET `/models/{model_name}`

Get detailed information about a specific model.

### Health Check

#### GET `/health`

Check if Hyperbolic API is accessible.

**Response:**

```json
{
  "status": "healthy",
  "service": "hyperbolic"
}
```

## Usage Examples

### Python Client

```python
from app.services.hyperbolic import HyperbolicTextService

service = HyperbolicTextService()
response = await service.chat_completion(
    messages=[{"role": "user", "content": "Hello!"}],
    model="meta-llama/Meta-Llama-3.1-70B-Instruct"
)
print(response["choices"][0]["message"]["content"])
```

### LLM Provider

```python
from app.services.llm import get_llm_provider

provider = get_llm_provider("hyperbolic")
response = await provider.generate("What is AI?")
print(response.text)
```

### Vision

```python
from app.services.hyperbolic import HyperbolicVisionService

service = HyperbolicVisionService()
response = await service.vision_completion(
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image"},
            {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}}
        ]
    }],
    model="meta-llama/Llama-3.2-90B-Vision-Instruct"
)
```

### Image Generation

```python
from app.services.hyperbolic import HyperbolicImageService

service = HyperbolicImageService()
response = await service.generate_image(
    prompt="A futuristic city at night",
    model_name="FLUX.1-dev",
    steps=30,
    height=1024,
    width=1024
)
```

## Integration with Existing Systems

### LLM Factory

Hyperbolic is automatically available through the LLM factory:

```python
from app.services.llm import LLMProviderFactory

provider = LLMProviderFactory.get_provider("hyperbolic")
```

### Council Agent

Hyperbolic models are included in the council agent's model selection pool. They will be automatically considered when selecting models for multi-model consensus.

### Chat Endpoint

The main chat endpoint (`/api/v1/chat`) supports Hyperbolic:

```json
{
  "provider": "hyperbolic",
  "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
  "prompt": "Hello!"
}
```

## Parameters

### Text Generation Parameters

- `temperature` (0.0-2.0): Controls randomness. Lower = more deterministic.
- `max_tokens` (1-4096): Maximum tokens to generate.
- `top_p` (0.0-1.0): Nucleus sampling parameter.
- `presence_penalty` (-2.0 to 2.0): Encourages new topics.
- `stop`: List of stop sequences.

### Image Generation Parameters

- `steps` (1-100): Number of generation steps. More = higher quality, slower.
- `cfg_scale` (1.0-20.0): Guidance scale. Higher = more adherence to prompt.
- `height`/`width` (64-2048): Image dimensions in pixels.
- `enable_refiner`: Whether to use refiner for higher quality.
- `backend`: Backend selection ("auto" or specific backend).

### Audio Generation Parameters

- `speed` (0.5-2.0): Speech speed multiplier. 1.0 = normal speed.

## Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid parameters)
- `401`: Unauthorized (missing or invalid API key)
- `429`: Rate limited (too many requests)
- `500`: Server error
- `503`: Service unavailable (model loading)

The client automatically retries on transient errors (429, 503) with exponential backoff.

## Rate Limits

Rate limits are enforced by Hyperbolic. The client automatically handles rate limiting with retry logic.

## Best Practices

1. **Model Selection**: Choose models based on your needs:

   - Fast responses: Use smaller models (3B, 8B)
   - High quality: Use larger models (70B, 405B)
   - Reasoning tasks: Use DeepSeek-R1 or DeepSeek-V3
   - Vision tasks: Use vision models

2. **Streaming**: Enable streaming for better user experience with long responses:

   ```json
   { "stream": true }
   ```

3. **Token Limits**: Be mindful of `max_tokens` to control response length and costs.

4. **Error Handling**: Always handle exceptions and check response status codes.

5. **Caching**: Consider caching responses for repeated queries.

## Support

- API Documentation: [https://docs.hyperbolic.xyz/docs/rest-api](https://docs.hyperbolic.xyz/docs/rest-api)
- Models: [https://app.hyperbolic.xyz/models](https://app.hyperbolic.xyz/models)
- Account: [https://app.hyperbolic.xyz/](https://app.hyperbolic.xyz/)

## License

This integration follows the Hyperbolic API terms of service.
