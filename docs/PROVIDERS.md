# LLM Provider Configuration Guide

## Overview

This guide covers configuration and usage of all supported LLM providers in DurgasAI.

## Provider Configuration

All providers are configured in `config/config.json` under the `llm.providers` section.

### Common Configuration Fields

All providers support:

- `api_key` (string, required): API key for authentication
- `base_url` (string, optional): Custom API endpoint URL
- `model` (string, required): Default model identifier

## Provider Details

### Fireworks AI

**Base URL:** `https://api.fireworks.ai/inference/v1`  
**Endpoint:** `/chat/completions`  
**API Key:** Get from [Fireworks AI Dashboard](https://fireworks.ai)

**Configuration:**

```json
{
  "fireworks": {
    "api_key": "your_api_key_here",
    "base_url": "https://api.fireworks.ai/inference/v1",
    "model": "accounts/fireworks/models/llama-v3-70b-instruct"
  }
}
```

**Available Models:**

- `accounts/fireworks/models/gemma-7b-it`
- `accounts/fireworks/models/llama-v2-70b-chat`
- `accounts/fireworks/models/llama-v3-70b-instruct`
- `accounts/fireworks/models/llama-v3p1-405b-instruct`
- `accounts/fireworks/models/mixtral-8x7b-instruct`

**Rate Limits:** Varies by plan (typically 500+ RPM)  
**Pricing:** Pay-per-use, competitive rates

### Deep Infra

**Base URL:** `https://api.deepinfra.com/v1/openai`  
**Endpoint:** `/chat/completions`  
**API Key:** Get from [Deep Infra Dashboard](https://deepinfra.com)

**Configuration:**

```json
{
  "deepinfra": {
    "api_key": "your_api_key_here",
    "base_url": "https://api.deepinfra.com/v1/openai",
    "model": "google/gemma-7b-it"
  }
}
```

**Available Models:**

- `google/gemma-7b-it`
- `llama-2-70b-chat-hf`
- `meta-llama/Meta-Llama-3-70B-Instruct`
- `mistralai/Mixtral-8x7B-Instruct-v0.1`

**Rate Limits:** Varies by plan  
**Pricing:** Cost-effective, pay-per-use

### Anyscale

**Base URL:** `https://api.endpoints.anyscale.com/v1`  
**Endpoint:** `/chat/completions`  
**API Key:** Get from [Anyscale Console](https://console.anyscale.com)

**Configuration:**

```json
{
  "anyscale": {
    "api_key": "your_api_key_here",
    "base_url": "https://api.endpoints.anyscale.com/v1",
    "model": "meta-llama/Llama-3-70b-chat-hf"
  }
}
```

**Available Models:**

- `meta-llama/Llama-2-70b-chat-hf`
- `meta-llama/Llama-3-70b-chat-hf`
- `mistralai/Mixtral-8x7b-Instruct-v0.1`

**Rate Limits:** Enterprise-grade, scalable  
**Pricing:** Contact for enterprise pricing

### Lepton AI

**Base URL:** Dynamic per model (e.g., `https://llama3-70b.lepton.run`)  
**Endpoint:** `/api/v1/chat/completions`  
**API Key:** Get from [Lepton AI Dashboard](https://www.lepton.ai)

**Configuration:**

```json
{
  "lepton": {
    "api_key": "your_api_key_here",
    "base_url": "",
    "model": "llama3-70b"
  }
}
```

**Available Models:**

- `llama2-70b-4096`
- `llama3-70b`
- `mixtral-8x7b`

**Rate Limits:** Ultra-low latency, optimized  
**Pricing:** Pay-per-use

### OctoAI

**Base URL:** `https://text.octoai.run/v1`  
**Endpoint:** `/chat/completions`  
**API Key:** Get from [OctoAI Console](https://octo.ai)

**Configuration:**

```json
{
  "octoai": {
    "api_key": "your_api_key_here",
    "base_url": "https://text.octoai.run/v1",
    "model": "meta-llama-3-70b-instruct"
  }
}
```

**Available Models:**

- `llama-2-70b-chat`
- `meta-llama-3-70b-instruct`
- `meta-llama-3.1-405b-instruct`
- `mixtral-8x7b-instruct`

**Rate Limits:** Optimized model serving  
**Pricing:** Pay-per-use

### Together AI

**Base URL:** `https://api.together.xyz/v1`  
**Endpoint:** `/chat/completions`  
**API Key:** Get from [Together AI Dashboard](https://together.ai)

**Configuration:**

```json
{
  "together": {
    "api_key": "your_api_key_here",
    "base_url": "https://api.together.xyz/v1",
    "model": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
  }
}
```

**Available Models:**

- `meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo`
- `mistralai/Mixtral-8x7B-Instruct-v0.1`

**Rate Limits:** Collaborative infrastructure  
**Pricing:** Pay-per-use

### Mistral AI

**Base URL:** `https://api.mistral.ai/v1`  
**Endpoint:** `/chat/completions`  
**API Key:** Get from [Mistral AI Platform](https://console.mistral.ai)

**Configuration:**

```json
{
  "mistral": {
    "api_key": "your_api_key_here",
    "base_url": "https://api.mistral.ai/v1",
    "model": "open-mixtral-8x7b"
  }
}
```

**Available Models:**

- `open-mixtral-8x7b`
- `mistral-large`
- `mistral-medium`
- `mistral-small`
- `pixtral-12b`

**Rate Limits:** Varies by tier  
**Pricing:** Pay-per-use, competitive rates

### Perplexity AI

**Base URL:** `https://api.perplexity.ai`  
**Endpoint:** `/chat/completions`  
**API Key:** Get from [Perplexity AI](https://www.perplexity.ai)

**Configuration:**

```json
{
  "perplexity": {
    "api_key": "your_api_key_here",
    "base_url": "https://api.perplexity.ai",
    "model": "mixtral-8x7b-instruct"
  }
}
```

**Available Models:**

- `mixtral-8x7b-instruct`
- `llama-3-sonar-large-32k-online`
- `llama-3-sonar-small-32k-online`
- `llama-3.1-sonar-large-128k-online`

**Rate Limits:** Varies by plan  
**Pricing:** Pay-per-use  
**Special Features:** Search-augmented generation with web search

## Best Practices

### 1. API Key Security

- Never commit API keys to version control
- Use environment variables or secure configuration management
- Rotate keys regularly
- Use different keys for development and production

### 2. Rate Limiting

- Monitor your usage to avoid rate limit errors
- Implement exponential backoff for retries
- Use connection pooling for high-volume applications
- Consider provider-specific rate limits when benchmarking

### 3. Model Selection

- Choose models based on your latency vs. quality requirements
- Test multiple providers to find the best fit
- Consider cost per token for high-volume use cases
- Use the benchmark API to compare performance

### 4. Error Handling

- Implement retry logic with exponential backoff
- Handle rate limit errors gracefully
- Log errors for debugging and monitoring
- Use health checks before critical operations

### 5. Performance Optimization

- Use streaming for better perceived latency
- Cache responses when appropriate
- Batch requests when possible
- Monitor metrics to identify bottlenecks

## Health Checks

All providers implement a `health_check()` method that can be used to verify availability:

```python
from app.services.llm import get_llm_provider

provider = get_llm_provider("fireworks")
is_healthy = await provider.health_check()
```

## Model Lists

Get available models for a provider:

```python
provider = get_llm_provider("fireworks")
models = await provider.list_models()
```

## Troubleshooting

### Common Issues

1. **API Key Not Configured**

   - Ensure API key is set in `config.json`
   - Check for typos in provider name
   - Verify key has necessary permissions

2. **Rate Limit Errors**

   - Reduce request frequency
   - Implement exponential backoff
   - Consider upgrading provider plan

3. **Timeout Errors**

   - Increase timeout in provider configuration
   - Check network connectivity
   - Verify provider status

4. **Model Not Found**
   - Verify model name is correct
   - Check provider's model list
   - Ensure model is available in your region/plan

## Support

For provider-specific issues:

- Check provider documentation
- Contact provider support
- Review provider status pages
- Check API changelogs for breaking changes
