# OpenRouter API Integration

## Overview

OpenRouter provides a unified interface for accessing 100+ LLM models from multiple providers including OpenAI, Anthropic, Google, Meta, Mistral, DeepSeek, xAI, Cohere, and more. This integration adds OpenRouter as a new LLM provider to your backend, enabling seamless access to diverse AI models through a single API.

## Features

- **Unified Model Access**: Access 100+ models from multiple providers
- **Auto-Routing**: Intelligent model selection based on query characteristics
- **OpenAI-Compatible API**: Full compatibility with OpenAI API format
- **Embeddings Support**: Multiple embedding models available
- **Model Registry**: Dynamic model discovery and caching
- **Usage Monitoring**: Track requests, errors, and performance
- **Council Integration**: Use OpenRouter models in multi-model council system

## Configuration

### 1. Add OpenRouter to Config

Edit `backend/config/config.json`:

```json
{
  "llm": {
    "providers": {
      "openrouter": {
        "api_key": "your-openrouter-api-key",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openrouter/auto",
        "site_url": "https://durgasai.app",
        "app_name": "DurgasAI",
        "enable_auto_routing": true,
        "fallback_models": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"]
      }
    }
  }
}
```

### 2. Get OpenRouter API Key

1. Sign up at [https://openrouter.ai/](https://openrouter.ai/)
2. Create an API key in your dashboard
3. Add the key to your config file

## Usage

### Chat Completions

#### Using OpenAI-Compatible Endpoint

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/v1/openai/chat/completions",
    json={
        "model": "openai/gpt-4o",
        "messages": [
            {"role": "user", "content": "Explain quantum computing"}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
)
```

#### Using Direct OpenRouter Endpoint

```python
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMConfig

provider = get_llm_provider("openrouter")
config = LLMConfig(model="openai/gpt-4o")
response = await provider.generate(
    prompt="Explain quantum computing",
    config=config
)
```

### Auto-Routing

Use `openrouter/auto` to let OpenRouter select the best model:

```python
config = LLMConfig(model="openrouter/auto")
response = await provider.generate(
    prompt="Complex reasoning task requiring step-by-step analysis",
    config=config
)
```

Or use the auto-route API:

```python
response = httpx.post(
    "http://localhost:8000/api/v1/openrouter/auto-route",
    json={
        "query": "Your query here",
        "prefer_speed": False,
        "max_cost": 0.01
    }
)
```

### Embeddings

```python
from app.services.openrouter import OpenRouterEmbeddingService

service = OpenRouterEmbeddingService()
embedding = await service.embed_text("Your text here")
```

Or via API:

```python
response = httpx.post(
    "http://localhost:8000/api/v1/openrouter/embeddings",
    json={
        "text": "Your text here",
        "model": "openai/text-embedding-3-small"
    }
)
```

## Available Models

### Popular Models

- **OpenAI**: `openai/gpt-4o`, `openai/gpt-4o-mini`, `openai/o1`, `openai/o3-mini`
- **Anthropic**: `anthropic/claude-3.5-sonnet`, `anthropic/claude-3.5-haiku`, `anthropic/claude-opus-4.1`
- **Google**: `google/gemini-2.0-flash-001`, `google/gemini-3-pro-preview`, `google/gemini-pro-1.5`
- **Meta**: `meta-llama/llama-3.3-70b-instruct`, `meta-llama/llama-3.2-90b-vision-instruct`
- **Mistral**: `mistralai/mistral-large`, `mistralai/mistral-small`, `mistralai/codestral`
- **DeepSeek**: `deepseek/deepseek-r1`, `deepseek/deepseek-chat`
- **xAI**: `x-ai/grok-2`

### Embedding Models

- `openai/text-embedding-3-small` (1536 dims)
- `openai/text-embedding-3-large` (3072 dims)
- `google/gemini-embedding-001` (768 dims)
- `mistralai/mistral-embed-2312` (1024 dims)
- `qwen/qwen3-embedding-8b` (2048 dims)

## API Endpoints

### OpenRouter-Specific Endpoints

- `GET /api/v1/openrouter/models` - List all available models
- `GET /api/v1/openrouter/models/{model_id}` - Get model details
- `POST /api/v1/openrouter/auto-route` - Test auto-routing
- `GET /api/v1/openrouter/providers` - List all providers
- `GET /api/v1/openrouter/limits` - Check rate limits
- `POST /api/v1/openrouter/embeddings` - Generate embeddings
- `GET /api/v1/openrouter/embeddings/models` - List embedding models

### OpenAI-Compatible Endpoints

- `POST /api/v1/openai/chat/completions` - Chat completions (supports OpenRouter models)
- `POST /api/v1/openai/embeddings` - Embeddings (supports OpenRouter models)
- `GET /api/v1/openai/models` - List models (includes OpenRouter models)

## Examples

### Example 1: Simple Chat

```bash
curl -X POST http://localhost:8000/api/v1/openai/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### Example 2: Auto-Routing

```bash
curl -X POST http://localhost:8000/api/v1/openrouter/auto-route \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Solve this complex math problem step by step",
    "prefer_speed": false
  }'
```

### Example 3: Embeddings

```bash
curl -X POST http://localhost:8000/api/v1/openrouter/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Machine learning is fascinating",
    "model": "openai/text-embedding-3-small"
  }'
```

## Cost Management

OpenRouter charges per token based on the model used. Monitor costs:

1. Check your OpenRouter dashboard for usage
2. Use `max_cost` parameter in auto-route to limit spending
3. Monitor usage via the monitoring service

## Rate Limiting

OpenRouter manages rate limits based on your plan. The integration:

- Respects rate limits automatically
- Implements exponential backoff on 429 errors
- Caches model lists to reduce API calls

## Error Handling

The integration handles errors gracefully:

- **429 Rate Limit**: Automatic retry with backoff
- **Model Unavailable**: Falls back to alternative models
- **API Errors**: Detailed error messages in responses

## Council Integration

OpenRouter models can be used in the council system:

```python
from app.services.council import select_council_models

# OpenRouter will be included if available and healthy
models = await select_council_models(min_models=3, max_models=5)
```

## Monitoring

Track usage and performance:

```python
from app.services.openrouter import get_monitor

monitor = get_monitor()
stats = monitor.get_stats(window_minutes=60)
health = monitor.check_health()
```

## Best Practices

1. **Use Auto-Routing**: Let OpenRouter select optimal models for simple queries
2. **Specify Models**: Use specific models for production workloads
3. **Monitor Costs**: Track token usage and costs regularly
4. **Cache Model Lists**: Model lists are cached for 1 hour
5. **Handle Errors**: Implement retry logic for production
6. **Use Fallbacks**: Configure fallback models in config

## Troubleshooting

### API Key Issues

- Ensure API key is set in config.json
- Check key is valid in OpenRouter dashboard
- Verify key has necessary permissions

### Model Not Found

- Check model ID is correct (e.g., `openai/gpt-4o` not `gpt-4o`)
- Verify model is available in OpenRouter
- Use `/api/v1/openrouter/models` to list available models

### Rate Limiting

- Check your OpenRouter plan limits
- Implement request queuing for high-volume usage
- Use caching to reduce API calls

## Support

- OpenRouter Docs: [https://openrouter.ai/docs](https://openrouter.ai/docs)
- OpenRouter Models: [https://openrouter.ai/models](https://openrouter.ai/models)
- OpenRouter Dashboard: [https://openrouter.ai/keys](https://openrouter.ai/keys)

## Migration Notes

- OpenRouter is added as a new provider (doesn't replace existing ones)
- Existing providers continue to work unchanged
- OpenRouter is optional - system works without it
- No breaking changes to existing APIs
