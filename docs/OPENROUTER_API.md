# OpenRouter API Documentation

## Overview

OpenRouter provides a unified interface for accessing 100+ LLM models from multiple providers including OpenAI, Anthropic, Google, Meta, Mistral, and more. This implementation provides production-ready access to all models from the Postman collection.

## Features

- **60+ Chat Models** across 12 provider categories
- **9 Embedding Models** from multiple providers
- **Auto-routing** via `openrouter/auto` model
- **Streaming support** with Server-Sent Events
- **Cost tracking** and usage analytics
- **Production-grade error handling** with exponential backoff retries
- **Response caching** for deterministic requests
- **Comprehensive monitoring** with request/response logging

## Base URL

All endpoints are available at `/api/v1/openrouter`

## Authentication

OpenRouter uses Bearer token authentication. Configure your API key in `config.json`:

```json
{
  "llm": {
    "providers": {
      "openrouter": {
        "api_key": "your-api-key-here",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openrouter/auto",
        "site_url": "https://your-site.com",
        "app_name": "YourApp",
        "enable_auto_routing": true,
        "fallback_models": ["openai/gpt-4o-mini", "anthropic/claude-3.5-haiku"]
      }
    }
  }
}
```

## Endpoints

### Chat Completions

#### POST `/chat/completions`

Generate chat completions using any OpenRouter model.

**Request:**

```json
{
  "message": "Explain quantum computing",
  "model": "openai/gpt-4o",
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": false,
  "context": "Optional context string",
  "conversation_history": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help?"
    }
  ]
}
```

**Response:**

```json
{
  "message": "Quantum computing is...",
  "provider": "openrouter (OpenAI)",
  "model": "openai/gpt-4o",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 150,
    "total_tokens": 160,
    "cost": 0.0004
  },
  "finish_reason": "stop",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Models

#### GET `/models`

List all available OpenRouter models with details.

**Query Parameters:**

- `force_refresh` (boolean): Force refresh of model cache

**Response:**

```json
[
  {
    "id": "openai/gpt-4o",
    "name": "GPT-4o",
    "description": "OpenAI's most advanced model",
    "context_length": 128000,
    "pricing": {
      "prompt": "0.0025",
      "completion": "0.01"
    },
    "capabilities": ["chat", "vision"],
    "top_provider": {
      "name": "OpenAI"
    }
  }
]
```

#### GET `/models/{model_id}`

Get detailed information about a specific model.

**Response:**

```json
{
  "id": "openai/gpt-4o",
  "name": "GPT-4o",
  "description": "OpenAI's most advanced model",
  "context_length": 128000,
  "pricing": {
    "prompt": "0.0025",
    "completion": "0.01"
  },
  "capabilities": ["chat", "vision"],
  "top_provider": {
    "name": "OpenAI"
  }
}
```

### Providers

#### GET `/providers`

List all providers available through OpenRouter.

**Response:**

```json
{
  "providers": [
    {
      "name": "gpt",
      "model_count": 10,
      "models": ["openai/gpt-4o", "openai/gpt-4o-mini", ...]
    },
    {
      "name": "claude",
      "model_count": 6,
      "models": ["anthropic/claude-3.5-sonnet", ...]
    }
  ],
  "total": 12
}
```

#### GET `/providers/{provider_name}/models`

Get all models for a specific provider.

**Response:**

```json
{
  "provider": "gpt",
  "models": [
    {
      "id": "openai/gpt-4o",
      "name": "GPT-4o",
      ...
    }
  ],
  "total": 10
}
```

### Auto-Routing

#### POST `/auto-route`

Intelligently select the best model based on query characteristics.

**Request:**

```json
{
  "query": "Explain quantum computing in detail",
  "requirements": {
    "context_length": 10000
  },
  "prefer_speed": false,
  "max_cost": 0.01
}
```

**Response:**

```json
{
  "selected_model": "openai/gpt-4o",
  "reasoning": "High quality, good at code",
  "alternatives": ["anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash-001"],
  "estimated_cost": 0.0125
}
```

### Categories

#### GET `/categories`

Get models categorized by capability.

**Response:**

```json
{
  "chat": {
    "models": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", ...],
    "count": 45
  },
  "reasoning": {
    "models": ["openai/o1", "openai/o3-mini", "deepseek/deepseek-r1"],
    "count": 5
  },
  "vision": {
    "models": ["openai/gpt-4o", "google/gemini-2.0-flash-001", ...],
    "count": 12
  },
  "code": {
    "models": ["openai/gpt-4o", "mistralai/codestral", ...],
    "count": 8
  },
  "fast": {
    "models": ["openai/gpt-4o-mini", "google/gemini-2.0-flash-001", ...],
    "count": 15
  },
  "long_context": {
    "models": ["anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5", ...],
    "count": 10
  }
}
```

### Embeddings

#### POST `/embeddings`

Generate embeddings using OpenRouter API.

**Request:**

```json
{
  "text": "Hello world",
  "model": "openai/text-embedding-3-small"
}
```

Or for batch:

```json
{
  "texts": ["Hello", "World"],
  "model": "openai/text-embedding-3-small"
}
```

**Response:**

```json
{
  "embedding": [0.1, 0.2, 0.3, ...],
  "model": "openai/text-embedding-3-small",
  "usage": {
    "total_tokens": 10
  },
  "cost": 0.000002
}
```

#### GET `/embeddings/models`

List available embedding models with metadata.

**Response:**

```json
{
  "models": [
    {
      "id": "openai/text-embedding-3-small",
      "dimensions": 1536,
      "max_input_tokens": 8191,
      "pricing": {
        "prompt": "0.02",
        "completion": "0"
      }
    }
  ],
  "default": "openai/text-embedding-3-small",
  "total": 9
}
```

### Statistics and Monitoring

#### GET `/stats`

Get usage statistics and analytics.

**Query Parameters:**

- `window_minutes` (integer): Time window in minutes (None = all time)

**Response:**

```json
{
  "window_minutes": 60,
  "total_requests": 100,
  "successful_requests": 98,
  "failed_requests": 2,
  "success_rate": 0.98,
  "total_tokens": 50000,
  "total_prompt_tokens": 30000,
  "total_completion_tokens": 20000,
  "total_cost": 0.125,
  "average_latency_ms": 850.5,
  "error_counts": {
    "http_error": 2
  },
  "model_usage": {
    "openai/gpt-4o": 50,
    "anthropic/claude-3.5-sonnet": 30
  },
  "health": {
    "status": "healthy",
    "success_rate": 0.98
  }
}
```

#### GET `/limits`

Check rate limits and health status.

**Response:**

```json
{
  "status": "healthy",
  "message": "Rate limits are managed by OpenRouter. Check your dashboard for details.",
  "health_check": true,
  "monitoring": {
    "success_rate": 0.98,
    "total_requests": 100,
    "failed_requests": 2,
    "average_latency_ms": 850.5,
    "total_tokens": 50000,
    "total_cost": 0.125
  }
}
```

## Supported Models

### Chat Models by Provider

#### Claude (Anthropic)

- `anthropic/claude-opus-4.1`
- `anthropic/claude-3.5-sonnet`
- `anthropic/claude-3.5-haiku`
- `anthropic/claude-3-opus`
- `anthropic/claude-3-sonnet`
- `anthropic/claude-3-haiku`

#### GPT (OpenAI)

- `openai/gpt-oss-120b`
- `openai/gpt-oss-20b`
- `openai/o3-mini`
- `openai/o3-mini-high`
- `openai/o1`
- `openai/gpt-4o`
- `openai/gpt-4o-mini`
- `openai/chatgpt-4o-latest`
- `openai/gpt-4-turbo-preview`
- `openai/gpt-3.5-turbo`

#### Gemini (Google)

- `google/gemini-3-pro-preview`
- `google/gemini-2.0-flash-001`
- `google/gemini-pro-1.5`
- `google/gemini-flash-1.5`
- `google/gemini-pro`
- `google/gemma-2-27b-it`
- `google/gemma-2-9b-it`

#### Llama (Meta)

- `meta-llama/llama-3.3-70b-instruct`
- `meta-llama/llama-3.2-90b-vision-instruct`
- `meta-llama/llama-3.2-11b-vision-instruct`
- `meta-llama/llama-3.2-3b-instruct`
- `meta-llama/llama-3.2-1b-instruct`
- `meta-llama/llama-3.1-405b-instruct`

#### Mistral

- `mistralai/mistral-large`
- `mistralai/mistral-small`
- `mistralai/mistral-tiny`
- `mistralai/mixtral-8x7b-instruct`
- `mistralai/codestral`
- `mistralai/mistral-nemo`

#### Cohere

- `cohere/command-r-plus`
- `cohere/command-r`
- `cohere/command`

#### DeepSeek

- `deepseek/deepseek-r1`
- `deepseek/deepseek-chat`

#### Grok (xAI)

- `x-ai/grok-2`

#### Nova (Amazon)

- `amazon/nova-pro-v1`
- `amazon/nova-lite-v1`

#### Router

- `openrouter/auto` - Automatic model selection

### Embedding Models

- `google/gemini-embedding-001` (768 dimensions)
- `openai/text-embedding-3-small` (1536 dimensions)
- `openai/text-embedding-3-large` (3072 dimensions)
- `openai/text-embedding-ada-002` (1536 dimensions)
- `mistralai/mistral-embed-2312` (1024 dimensions)
- `mistralai/codestral-embed-2505` (1024 dimensions)
- `qwen/qwen3-embedding-0.6b` (512 dimensions)
- `qwen/qwen3-embedding-4b` (1024 dimensions)
- `qwen/qwen3-embedding-8b` (2048 dimensions)

## Error Handling

The implementation includes production-grade error handling:

- **Exponential backoff retries** for transient errors
- **Automatic fallback** to alternative models
- **Rate limit handling** with intelligent retry delays
- **Comprehensive error logging** with monitoring integration

### Error Response Format

```json
{
  "detail": "OpenRouter API error: Rate limit exceeded"
}
```

## Cost Tracking

All requests automatically track:

- Token usage (prompt, completion, total)
- Estimated cost based on model pricing
- Cost per request and aggregated costs

Costs are calculated using model pricing from OpenRouter and included in response metadata.

## Caching

Deterministic requests (temperature=0.0) are automatically cached for 5 minutes to reduce API calls and costs. Cache can be disabled by setting `cache_enabled=False` in provider initialization.

## Monitoring

All requests are automatically monitored with:

- Request/response logging
- Latency tracking
- Success/failure rates
- Error categorization
- Model usage statistics
- Cost aggregation

Access monitoring data via `/api/v1/openrouter/stats` endpoint.

## Examples

### Python Example

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/openrouter/chat/completions",
        json={
            "message": "Explain quantum computing",
            "model": "openai/gpt-4o",
            "temperature": 0.7,
            "max_tokens": 2048
        }
    )
    print(response.json())
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/openrouter/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing",
    "model": "openai/gpt-4o",
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

### Auto-Routing Example

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/openrouter/auto-route",
        json={
            "query": "I need to analyze a large codebase",
            "requirements": {"context_length": 100000},
            "prefer_speed": False
        }
    )
    result = response.json()
    print(f"Selected: {result['selected_model']}")
    print(f"Reasoning: {result['reasoning']}")
```

## Best Practices

1. **Use auto-routing** for optimal model selection: `openrouter/auto`
2. **Set fallback models** in config for reliability
3. **Monitor costs** via `/stats` endpoint
4. **Use caching** for deterministic requests (temperature=0.0)
5. **Handle rate limits** - implementation includes automatic retry
6. **Track usage** - monitor token usage and costs regularly

## Rate Limits

Rate limits are managed by OpenRouter. The implementation includes:

- Automatic retry with exponential backoff
- Rate limit detection and handling
- Fallback to alternative models on rate limit errors

Check your OpenRouter dashboard for your specific rate limits.

## Support

For issues or questions:

- Check OpenRouter documentation: https://openrouter.ai/docs
- Review model list: https://openrouter.ai/models
- Check monitoring stats: `/api/v1/openrouter/stats`
