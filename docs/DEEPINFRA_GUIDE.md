# Deep Infra API Integration Guide

## Overview

Deep Infra provides cost-effective AI inference with a wide selection of models. This guide covers all available endpoints and capabilities in the DurgasAI backend integration.

## Table of Contents

1. [Authentication](#authentication)
2. [Configuration](#configuration)
3. [API Endpoints](#api-endpoints)
4. [Model Catalog](#model-catalog)
5. [Usage Examples](#usage-examples)
6. [Error Handling](#error-handling)
7. [Rate Limits & Pricing](#rate-limits--pricing)

## Authentication

All Deep Infra API requests require an API key. Get your API key from [Deep Infra Dashboard](https://deepinfra.com).

Set the API key in `config/config.json`:

```json
{
  "llm": {
    "providers": {
      "deepinfra": {
        "api_key": "your_api_key_here",
        "base_url": "https://api.deepinfra.com/v1/openai",
        "inference_base_url": "https://api.deepinfra.com/v1",
        "model": "google/gemma-7b-it",
        "embedding_model": "thenlper/gte-large",
        "image_model": "black-forest-labs/FLUX-1-schnell"
      }
    }
  }
}
```

## Configuration

### Base URLs

Deep Infra uses two different base URLs:

- **OpenAI-compatible API**: `https://api.deepinfra.com/v1/openai`
  - Used for: Chat completions, text completions, embeddings
- **Direct Inference API**: `https://api.deepinfra.com/v1`
  - Used for: Direct model inference (text and image generation)

### Configuration Options

| Option               | Description                    | Default                               |
| -------------------- | ------------------------------ | ------------------------------------- |
| `api_key`            | Deep Infra API key             | Required                              |
| `base_url`           | OpenAI-compatible API base URL | `https://api.deepinfra.com/v1/openai` |
| `inference_base_url` | Direct inference API base URL  | `https://api.deepinfra.com/v1`        |
| `model`              | Default chat/completion model  | `google/gemma-7b-it`                  |
| `embedding_model`    | Default embedding model        | `thenlper/gte-large`                  |
| `image_model`        | Default image generation model | `black-forest-labs/FLUX-1-schnell`    |

## API Endpoints

### 1. Chat Completions

**Endpoint**: `POST /api/v1/deepinfra/chat/completions`

OpenAI-compatible chat endpoint with conversation history support.

**Request Body**:

```json
{
  "message": "Explain the importance of low latency LLMs",
  "model": "google/gemma-7b-it",
  "temperature": 0.7,
  "max_tokens": 1024,
  "conversation_history": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help you?"
    }
  ],
  "context": "Optional context string"
}
```

**Response**:

```json
{
  "message": "Response text...",
  "provider": "deepinfra",
  "model": "google/gemma-7b-it",
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 474,
    "total_tokens": 492
  },
  "finish_reason": "stop",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**cURL Example**:

```bash
curl -X POST http://localhost:8000/api/v1/deepinfra/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing",
    "model": "meta-llama/Meta-Llama-3-70B-Instruct",
    "temperature": 0.7,
    "max_tokens": 1024
  }'
```

### 2. Text Completions

**Endpoint**: `POST /api/v1/deepinfra/completions`

Simple prompt-to-text generation without conversation history.

**Request Body**:

```json
{
  "prompt": "Write a limerick about APIs",
  "model": "google/gemma-7b-it",
  "max_tokens": 250,
  "temperature": 0.7,
  "top_p": 1.0,
  "stop": ["\n\n"]
}
```

**Response**:

```json
{
  "text": "Generated text completion...",
  "model": "google/gemma-7b-it",
  "usage": {
    "prompt_tokens": 8,
    "completion_tokens": 38,
    "total_tokens": 46
  },
  "finish_reason": "stop"
}
```

**cURL Example**:

```bash
curl -X POST http://localhost:8000/api/v1/deepinfra/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a Python function to calculate fibonacci",
    "max_tokens": 200
  }'
```

### 3. Embeddings

**Endpoint**: `POST /api/v1/deepinfra/embeddings`

Generate vector embeddings for text. Supports single text or batch processing.

**Request Body (Single Text)**:

```json
{
  "input": "I was looking for something interesting to write about...",
  "model": "thenlper/gte-large"
}
```

**Request Body (Batch)**:

```json
{
  "input": ["First text to embed", "Second text to embed", "Third text to embed"],
  "model": "thenlper/gte-large"
}
```

**Response**:

```json
{
  "embeddings": [
    [0.123, -0.456, 0.789, ...],
    [0.234, -0.567, 0.890, ...]
  ],
  "model": "thenlper/gte-large",
  "usage": {
    "prompt_tokens": 19,
    "total_tokens": 19
  }
}
```

**cURL Example**:

```bash
curl -X POST http://localhost:8000/api/v1/deepinfra/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Machine learning is fascinating",
    "model": "thenlper/gte-large"
  }'
```

**Alternative Endpoint**: `POST /api/v1/embeddings/deepinfra`

Also available through the general embeddings route.

### 4. Direct Model Inference

**Endpoint**: `POST /api/v1/deepinfra/inference`

Direct inference using model-specific endpoints. Supports both text and image models.

**Request Body (Text Model)**:

```json
{
  "model_path": "bigcode/starcoder",
  "input": {
    "input": "def fibonacci(n):"
  }
}
```

**Request Body (Image Model)**:

```json
{
  "model_path": "black-forest-labs/FLUX-1-dev",
  "input": {
    "prompt": "A photo of an astronaut riding a horse on Mars"
  }
}
```

**Response (Text)**:

```json
{
  "data": {
    "generated_text": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
  },
  "model": "bigcode/starcoder"
}
```

**Response (Image)**:

```json
{
  "image": "base64_encoded_image_string",
  "content_type": "image/png",
  "model": "black-forest-labs/FLUX-1-dev"
}
```

**cURL Example (Text)**:

```bash
curl -X POST http://localhost:8000/api/v1/deepinfra/inference \
  -H "Content-Type: application/json" \
  -d '{
    "model_path": "EleutherAI/gpt-j-6B",
    "input": {
      "input": "The future of AI is"
    }
  }'
```

### 5. Image Generation

**Endpoint**: `POST /api/v1/deepinfra/images/generate`

Generate images using FLUX or SDXL models.

**Request Body**:

```json
{
  "prompt": "A beautiful sunset over mountains with vibrant colors",
  "model": "black-forest-labs/FLUX-1-schnell",
  "negative_prompt": "blurry, low quality, distorted",
  "num_inference_steps": 4,
  "guidance_scale": 3.5,
  "seed": 42
}
```

**Response**:

```json
{
  "image": "base64_encoded_image_string",
  "model": "black-forest-labs/FLUX-1-schnell",
  "content_type": "image/png",
  "format": "base64"
}
```

**cURL Example**:

```bash
curl -X POST http://localhost:8000/api/v1/deepinfra/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cyberpunk cityscape at night",
    "model": "black-forest-labs/FLUX-1-dev"
  }'
```

### 6. List Models

**Endpoint**: `GET /api/v1/deepinfra/models`

List available models, optionally filtered by category.

**Query Parameters**:

- `category` (optional): Filter by category
  - `chat`: Chat completion models
  - `completion`: Text completion models
  - `embedding`: Embedding models
  - `inference_text`: Direct inference text models
  - `inference_image`: Direct inference image models

**Response (All Models)**:

```json
{
  "chat": ["google/gemma-7b-it", "meta-llama/Meta-Llama-3-70B-Instruct", ...],
  "completion": ["google/gemma-7b-it", ...],
  "embedding": ["thenlper/gte-large"],
  "inference": {
    "text": ["bigcode/starcoder", "gpt2", ...],
    "image": ["black-forest-labs/FLUX-1-dev", ...]
  }
}
```

**Response (Filtered)**:

```json
{
  "models": ["google/gemma-7b-it", "meta-llama/Meta-Llama-3-70B-Instruct", ...],
  "category": "chat",
  "count": 40
}
```

**cURL Example**:

```bash
curl http://localhost:8000/api/v1/deepinfra/models?category=chat
```

### 7. List Image Models

**Endpoint**: `GET /api/v1/deepinfra/images/models`

List available image generation models with descriptions.

**Response**:

```json
{
  "models": {
    "black-forest-labs/FLUX-1-dev": {
      "name": "FLUX-1-dev",
      "description": "High-quality image generation, slower but best quality",
      "recommended_steps": 50,
      "guidance_scale": 3.5
    },
    "black-forest-labs/FLUX-1-schnell": {
      "name": "FLUX-1-schnell",
      "description": "Fast image generation with good quality",
      "recommended_steps": 4,
      "guidance_scale": 3.5
    },
    "stabilityai/sdxl-turbo": {
      "name": "SDXL Turbo",
      "description": "Ultra-fast image generation",
      "recommended_steps": 1,
      "guidance_scale": 0.0
    }
  },
  "count": 3
}
```

## Model Catalog

### Chat Models (40+ models)

#### Meta Llama Family

- `meta-llama/Llama-2-7b-chat-hf`
- `meta-llama/Llama-2-13b-chat-hf`
- `meta-llama/Llama-2-70b-chat-hf`
- `meta-llama/Meta-Llama-3-8B-Instruct`
- `meta-llama/Meta-Llama-3-70B-Instruct`
- `meta-llama/Meta-Llama-3.1-8B-Instruct`
- `meta-llama/Meta-Llama-3.1-70B-Instruct`
- `meta-llama/Meta-Llama-3.1-405B-Instruct`
- `meta-llama/Llama-3.2-1B-Instruct`
- `meta-llama/Llama-3.2-3B-Instruct`
- `meta-llama/Llama-3.2-11B-Vision-Instruct` (Vision)
- `meta-llama/Llama-3.2-90B-Vision-Instruct` (Vision)
- `meta-llama/Llama-3.3-70B-Instruct`
- `meta-llama/Llama-3.3-70B-Instruct-Turbo`
- `meta-llama/Llama-4-Scout-17B-16E-Instruct`
- `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`
- `meta-llama/Llama-Guard-4-12B` (Safety)

#### Google Gemma

- `google/gemma-7b-it`
- `google/gemma-3-4b-it`
- `google/gemma-3-12b-it`
- `google/gemma-3-27b-it`

#### DeepSeek

- `deepseek-ai/DeepSeek-V3`
- `deepseek-ai/DeepSeek-R1`
- `deepseek-ai/DeepSeek-R1-0528`
- `deepseek-ai/DeepSeek-R1-Turbo`
- `deepseek-ai/DeepSeek-R1-Distill-Llama-70B`
- `deepseek-ai/DeepSeek-Prover-V2-671B`

#### Mistral/Mixtral

- `mistralai/Mistral-7B-Instruct-v0.1`
- `mistralai/Mistral-7B-Instruct-v0.2`
- `mistralai/Mixtral-8x7B-Instruct-v0.1`

#### Qwen

- `Qwen/Qwen3-14B`
- `Qwen/Qwen3-32B`
- `Qwen/Qwen3-30B-A3B`
- `Qwen/Qwen3-235B-A22B`

#### Code Models

- `codellama/CodeLlama-34b-Instruct-hf`
- `codellama/CodeLlama-70b-Instruct-hf`
- `bigcode/starcoder2-15b`
- `Phind/Phind-CodeLlama-34B-v2`

#### Other Models

- `01-ai/Yi-34B-Chat`
- `microsoft/phi-4`
- `openai/gpt-oss-20b`
- `openai/gpt-oss-120b`
- `moonshotai/Kimi-K2-Instruct`
- `Austism/chronos-hermes-13b-v2`
- `cognitivecomputations/dolphin-2.6-mixtral-8x7b`
- `deepinfra/airoboros-70b`
- `DeepInfra/pygmalion-13b-4bit-128g`
- `Gryphe/MythoMax-L2-13b`
- `lizpreciatior/lzlv_70b_fp16_hf`

#### Vision Models

- `llava-hf/llava-1.5-7b-hf`

### Completion Models

Subset of chat models that support the `/completions` endpoint:

- `google/gemma-7b-it`
- `meta-llama/Meta-Llama-3-8B-Instruct`
- `meta-llama/Meta-Llama-3-70B-Instruct`

### Embedding Models

- `thenlper/gte-large` (1024 dimensions)

### Direct Inference Models

#### Text Models

- `bigcode/starcoder`
- `EleutherAI/gpt-j-6B`
- `EleutherAI/gpt-neo-125M`
- `EleutherAI/gpt-neo-1.3B`
- `EleutherAI/pythia-2.8b`
- `EleutherAI/pythia-12b`
- `gpt2`
- `meta-llama/Meta-Llama-3-8B-Instruct`
- `meta-llama/Meta-Llama-3-70B-Instruct`
- `Salesforce/codegen-16B-mono`

#### Image Models

- `black-forest-labs/FLUX-1-dev` (High quality, slower)
- `black-forest-labs/FLUX-1-schnell` (Fast, good quality)
- `stabilityai/sdxl-turbo` (Ultra-fast)

## Usage Examples

### Python SDK Usage

```python
from app.services.llm.deepinfra import DeepInfraProvider
from app.services.image.deepinfra_image import DeepInfraImageGenerator
from app.services.llm.base import LLMConfig

# Initialize provider
provider = DeepInfraProvider(api_key="your_api_key")

# Chat completion
response = await provider.generate(
    prompt="Explain quantum computing",
    config=LLMConfig(model="meta-llama/Meta-Llama-3-70B-Instruct")
)
print(response.text)

# Text completion
response = await provider.complete(
    prompt="Write a Python function",
    config=LLMConfig(model="google/gemma-7b-it")
)
print(response.text)

# Embeddings
result = await provider.generate_embeddings(
    text="Machine learning is fascinating",
    model="thenlper/gte-large"
)
print(result["embeddings"])

# Image generation
generator = DeepInfraImageGenerator(api_key="your_api_key")
result = await generator.generate_image(
    prompt="A beautiful sunset",
    model="black-forest-labs/FLUX-1-schnell"
)
image_base64 = result["image"]
```

### Streaming Chat Completions

```python
async for chunk in provider.stream(
    prompt="Tell me a story",
    config=LLMConfig(model="google/gemma-7b-it")
):
    print(chunk, end="", flush=True)
```

## Error Handling

### Common Error Codes

| Status Code | Description           | Solution                                       |
| ----------- | --------------------- | ---------------------------------------------- |
| 400         | Bad Request           | Check request payload format                   |
| 401         | Unauthorized          | Verify API key is correct                      |
| 404         | Model Not Found       | Check model name spelling                      |
| 429         | Rate Limit Exceeded   | Wait and retry with exponential backoff        |
| 500         | Internal Server Error | Retry request or contact support               |
| 503         | Service Unavailable   | Model temporarily unavailable, try again later |

### Error Response Format

```json
{
  "error": {
    "message": "Invalid API key",
    "type": "authentication_error",
    "code": 401
  }
}
```

### Retry Logic

The integration includes automatic retry logic with exponential backoff for transient errors. For rate limits (429), the system will automatically retry after the specified delay.

## Rate Limits & Pricing

### Rate Limits

Rate limits vary by plan and model. Check your Deep Infra dashboard for specific limits.

- **Free Tier**: Limited requests per minute
- **Paid Plans**: Higher rate limits based on subscription

### Pricing

Deep Infra uses pay-per-use pricing:

- **Chat/Completions**: Charged per token (input + output)
- **Embeddings**: Charged per token
- **Image Generation**: Charged per image

Pricing varies by model. Check [Deep Infra Pricing](https://deepinfra.com/pricing) for current rates.

### Cost Optimization Tips

1. **Use appropriate models**: Smaller models for simple tasks, larger for complex ones
2. **Set max_tokens**: Limit output length to control costs
3. **Batch embeddings**: Process multiple texts in one request
4. **Cache responses**: Cache frequently used embeddings and completions
5. **Monitor usage**: Track usage through Deep Infra dashboard

## Best Practices

1. **Model Selection**

   - Use `google/gemma-7b-it` for general tasks (cost-effective)
   - Use `meta-llama/Meta-Llama-3-70B-Instruct` for complex reasoning
   - Use `deepseek-ai/DeepSeek-V3` for coding tasks
   - Use `black-forest-labs/FLUX-1-schnell` for fast image generation

2. **Temperature Settings**

   - `0.0-0.3`: Deterministic, factual responses
   - `0.5-0.7`: Balanced creativity and accuracy (default)
   - `0.8-1.0`: Creative, varied responses

3. **Token Management**

   - Set appropriate `max_tokens` to control costs
   - Monitor token usage in responses
   - Use streaming for long responses

4. **Error Handling**

   - Implement retry logic for transient errors
   - Handle rate limits gracefully
   - Log errors for debugging

5. **Performance**
   - Use streaming for better user experience
   - Batch embeddings when possible
   - Cache frequently used results

## Integration with Benchmark System

Deep Infra endpoints are automatically integrated with the benchmark system:

```bash
# Benchmark Deep Infra
curl -X POST http://localhost:8000/api/v1/benchmark/single \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "deepinfra",
    "model": "google/gemma-7b-it",
    "prompt": "Explain AI",
    "temperature": 0.7,
    "max_tokens": 1024
  }'
```

## Support & Resources

- **Deep Infra Documentation**: [https://deepinfra.com/docs](https://deepinfra.com/docs)
- **Model Catalog**: [https://deepinfra.com/models](https://deepinfra.com/models)
- **Dashboard**: [https://deepinfra.com/dashboard](https://deepinfra.com/dashboard)
- **API Status**: [https://status.deepinfra.com](https://status.deepinfra.com)

## Changelog

### Version 1.0.0 (Current)

- ✅ Chat completions with conversation history
- ✅ Text completions
- ✅ Embeddings (single and batch)
- ✅ Direct model inference
- ✅ Image generation (FLUX and SDXL)
- ✅ Comprehensive model catalog (60+ models)
- ✅ Streaming support
- ✅ Error handling and retry logic
- ✅ Benchmark integration
- ✅ Comprehensive test coverage
