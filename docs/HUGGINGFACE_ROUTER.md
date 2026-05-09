# HuggingFace Router Guide

## Overview

HuggingFace Router provides unified access to multiple inference providers through a single API endpoint and API key. This allows you to use models from different providers without managing separate API keys.

## Why Use the Router?

1. **Single API Key**: One HuggingFace token for all providers
2. **Unified Interface**: Consistent API across providers
3. **Easy Switching**: Change providers without code changes
4. **Cost Management**: Centralized billing through HuggingFace

## Supported Providers

### Cerebras

- **Base URL**: `https://router.huggingface.co/cerebras/v1`
- **Best For**: High-quality reasoning, large models
- **Models**: Llama-4-Scout, Llama-3.3-70B, GPT-OSS-120B

### Fireworks AI

- **Base URL**: `https://router.huggingface.co/fireworks-ai/v1`
- **Best For**: Fast inference, good quality
- **Models**: DeepSeek-R1, Qwen3 variants, GPT-OSS models

### Groq

- **Base URL**: `https://router.huggingface.co/groq/openai/v1`
- **Best For**: Ultra-fast inference, real-time applications
- **Models**: Kimi-K2, GPT-OSS models

### Together AI

- **Base URL**: `https://router.huggingface.co/together/v1`
- **Best For**: Large models, research
- **Models**: DeepSeek-R1, Kimi-K2, GPT-OSS models

### Nebius AI

- **Base URL**: `https://router.huggingface.co/nebius/v1`
- **Best For**: Google models, embeddings
- **Models**: Gemma-3-27B, Qwen3-Embedding-8B

### Novita

- **Base URL**: `https://router.huggingface.co/novita/v3/openai`
- **Best For**: Advanced models, specialized tasks
- **Models**: DeepSeek-Prover, Llama-4 variants

### SambaNova

- **Base URL**: `https://router.huggingface.co/sambanova/v1`
- **Best For**: Enterprise-grade inference
- **Models**: DeepSeek-R1-Distill-Llama-70B

### Scaleway

- **Base URL**: `https://router.huggingface.co/scaleway/v1`
- **Best For**: European data residency
- **Models**: GPT-OSS-120B

## Router vs Direct Provider API

### When to Use Router

✅ **Use Router when:**

- You want single API key management
- You need to switch providers easily
- You're building a multi-provider application
- You want centralized billing

### When to Use Direct Provider API

✅ **Use Direct Provider API when:**

- You need provider-specific features (e.g., Groq vision, function calling)
- You want direct control over provider settings
- You have existing provider accounts
- You need provider-specific optimizations

## Usage Examples

### Using Router

```python
from app.services.llm.huggingface import HuggingFaceProvider

# Use Cerebras via Router
provider = HuggingFaceProvider(
    api_key="hf_...",  # Single HF token
    provider="cerebras"
)

response = await provider.generate(
    prompt="Explain AI",
    config=LLMConfig(model="meta-llama/Llama-4-Scout-17B-16E-Instruct")
)
```

### Using Direct Provider

```python
from app.services.llm.cerebras import CerebrasProvider

# Direct Cerebras API
provider = CerebrasProvider(
    api_key="cerebras_...",  # Provider-specific key
    base_url="https://api.cerebras.ai/v1"
)

response = await provider.generate(...)
```

## Model Recommendations by Use Case

### General Chat

- **Fast**: Groq (`moonshotai/kimi-k2-instruct`)
- **Balanced**: Fireworks (`deepseek-r1`)
- **Quality**: Cerebras (`meta-llama/Llama-4-Scout-17B-16E-Instruct`)

### Reasoning Tasks

- **Best**: Cerebras (`meta-llama/Llama-4-Scout-17B-16E-Instruct`)
- **Alternative**: Together (`deepseek-ai/DeepSeek-R1`)

### Code Generation

- **Best**: Groq (`qwen-2.5-coder-32b`) - via direct API
- **Router**: Fireworks (`qwen3-30b-a3b`)

### Multilingual

- **Best**: Together (`moonshotai/Kimi-K2-Instruct`)
- **Alternative**: Fireworks (`qwen3-235b-a22b`)

### Embeddings

- **Best**: Nebius (`Qwen/Qwen3-Embedding-8B`)

## Rate Limits

Each provider has different rate limits:

| Provider           | Requests/Day | Tokens/Minute |
| ------------------ | ------------ | ------------- |
| HuggingFace Native | 14,400       | 60,000        |
| Cerebras           | Varies       | Varies        |
| Groq               | Varies       | Varies        |
| Fireworks          | Varies       | Varies        |
| Together           | Varies       | Varies        |

Check response headers for current limits:

- `x-ratelimit-limit-requests-day`
- `x-ratelimit-remaining-requests-day`
- `x-ratelimit-limit-tokens-minute`
- `x-ratelimit-remaining-tokens-minute`

## Pricing

Pricing varies by provider and model. Check HuggingFace pricing page for details:

- Router pricing: Based on model and provider
- Direct provider: Check provider's pricing

## Configuration

### Router Configuration

```json
{
  "llm": {
    "providers": {
      "huggingface": {
        "api_key": "hf_...",
        "inference_provider": "groq",
        "model": "moonshotai/kimi-k2-instruct"
      }
    }
  }
}
```

### Switching Providers

Change `inference_provider` in config:

- `"hf"` - HuggingFace native
- `"cerebras"` - Cerebras
- `"groq"` - Groq
- `"fireworks"` - Fireworks AI
- `"together"` - Together AI
- `"nebius"` - Nebius AI
- `"novita"` - Novita
- `"sambanova"` - SambaNova
- `"scaleway"` - Scaleway

## Error Handling

### Provider-Specific Errors

Some providers may have unique error codes. The Router normalizes these to standard HTTP status codes.

### Model Availability

Not all models are available on all providers. Check model availability:

- HuggingFace Model Hub: Filter by `inference_provider`
- Provider documentation

### Fallback Strategy

```python
providers = ["groq", "fireworks", "together"]

for provider_name in providers:
    try:
        provider = HuggingFaceProvider(provider=provider_name)
        response = await provider.generate(...)
        break
    except Exception as e:
        logger.warning(f"{provider_name} failed: {e}")
        continue
```

## Best Practices

1. **Start with Router**: Use Router for simplicity
2. **Monitor Rate Limits**: Check headers and implement backoff
3. **Cache Responses**: Cache common queries to reduce API calls
4. **Use Appropriate Models**: Match model to task (reasoning, coding, etc.)
5. **Handle 503 Errors**: Models may need loading time
6. **Set Timeouts**: Long-running requests should have timeouts

## Troubleshooting

### Model Not Found

- Check model name spelling
- Verify model is available on selected provider
- Try different provider

### Rate Limit Exceeded

- Check rate limit headers
- Implement exponential backoff
- Consider using different provider

### Slow Responses

- Try faster provider (Groq, Fireworks)
- Use smaller model
- Check network latency

### Authentication Errors

- Verify API key is valid
- Check key has necessary permissions
- Ensure key is for HuggingFace (not provider-specific)

## Migration from Direct Providers

If you're currently using direct provider APIs:

1. **Get HuggingFace Token**: Sign up at huggingface.co
2. **Update Config**: Change `inference_provider` to router provider
3. **Update API Key**: Use HF token instead of provider key
4. **Test**: Verify same models work via Router
5. **Monitor**: Check for any differences in behavior

Most code changes are minimal - just provider name and API key.
