# NVIDIA AI API Integration Guide

## Overview

The DurgasAI backend includes comprehensive integration with NVIDIA's AI API, providing access to 50+ state-of-the-art models for chat completions, embeddings, vision analysis, and self-hosted deployments via NVIDIA NIM.

## Features

- **50+ Chat Models**: Nemotron, Llama, Mistral, Gemma, Phi, DeepSeek, Qwen, and more
- **Embeddings**: High-quality text embeddings for RAG and semantic search
- **Vision Models**: Multimodal analysis with Llama 3.2 Vision and Phi-4
- **NIM Support**: Self-hosted model deployment management
- **Image & Video Generation**: Stable Diffusion and Stable Video Diffusion
- **OpenAI-Compatible**: Drop-in replacement for OpenAI API

## Configuration

### Setup

1. Get your NVIDIA API key from [https://build.nvidia.com/explore/discover](https://build.nvidia.com/explore/discover)

2. Add configuration to `config/config.json`:

```json
{
  "llm": {
    "providers": {
      "nvidia": {
        "api_key": "your-nvidia-api-key",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "genai_base_url": "https://ai.api.nvidia.com/v1",
        "nim_base_url": "",
        "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
        "chat_model": "nvidia/llama-3.3-nemotron-super-49b-v1",
        "embedding_model": "nvidia/nv-embedqa-e5-v5",
        "vision_model": "meta/llama-3.2-90b-vision-instruct",
        "timeout": 120.0,
        "chat_timeout": 120.0,
        "embedding_timeout": 60.0,
        "vision_timeout": 180.0,
        "nim_timeout": 300.0
      }
    }
  }
}
```

## API Endpoints

### Dedicated NVIDIA Routes

All dedicated routes are under `/api/v1/nvidia/`:

#### Chat Completions

- `POST /api/v1/nvidia/chat/completions` - Generate chat completions
- `POST /api/v1/nvidia/chat/stream` - Stream chat completions
- `GET /api/v1/nvidia/chat/models` - List available models
- `GET /api/v1/nvidia/chat/models/{model_id}` - Get model information

#### Embeddings

- `POST /api/v1/nvidia/embeddings` - Generate embeddings
- `POST /api/v1/nvidia/embeddings/batch` - Batch embeddings
- `GET /api/v1/nvidia/embeddings/models` - List embedding models

#### Vision

- `POST /api/v1/nvidia/vision/analyze` - Analyze image with text
- `POST /api/v1/nvidia/vision/multimodal` - Multi-image analysis
- `POST /api/v1/nvidia/vision/video-frames` - Video frame analysis

#### NIM (Self-Hosted)

- `GET /api/v1/nvidia/nim/health` - Health check
- `GET /api/v1/nvidia/nim/models` - List deployed models
- `GET /api/v1/nvidia/nim/models/{model_id}` - Get model info
- `POST /api/v1/nvidia/nim/infer` - Run inference
- `GET /api/v1/nvidia/nim/metrics` - Get deployment metrics

#### Image & Video

- `POST /api/v1/nvidia/image/generate` - Generate images
- `POST /api/v1/nvidia/video/generate` - Generate videos

### Integrated Routes

NVIDIA is also available through existing unified routes:

- `POST /api/v1/chat` - Use `provider: "nvidia"` in request
- `POST /api/v1/embeddings/nvidia` - NVIDIA embeddings
- `POST /api/v1/vision/nvidia` - NVIDIA vision analysis

## Usage Examples

### Chat Completions

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/nvidia/chat/completions",
        json={
            "messages": [
                {"role": "user", "content": "What is AI?"}
            ],
            "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
            "temperature": 0.7,
            "max_tokens": 1024
        }
    )
    print(response.json())
```

### Embeddings

```python
response = await client.post(
    "http://localhost:8000/api/v1/nvidia/embeddings",
    json={
        "input": "Hello world",
        "model": "nvidia/nv-embedqa-e5-v5",
        "input_type": "query"
    }
)
```

### Vision Analysis

```python
response = await client.post(
    "http://localhost:8000/api/v1/nvidia/vision/analyze",
    json={
        "prompt": "What is in this image?",
        "image_url": "https://example.com/image.jpg",
        "model": "meta/llama-3.2-90b-vision-instruct"
    }
)
```

## Model Selection Guide

### Chat Models

**For General Purpose:**

- `nvidia/llama-3.3-nemotron-super-49b-v1` - Balanced performance
- `nvidia/llama-3.1-nemotron-ultra-253b-v1` - Highest quality

**For Reasoning:**

- `deepseek-ai/deepseek-r1` - Complex problem solving

**For Code:**

- `meta/codellama-70b` - Code generation
- `google/codegemma-7b` - Lightweight code model

**For Long Context:**

- `moonshotai/kimi-k2-instruct` - 131K context window
- `meta/llama-3.1-405b-instruct` - 131K context

### Vision Models

- `meta/llama-3.2-90b-vision-instruct` - High-quality vision (default)
- `meta/llama-3.2-11b-vision-instruct` - Faster vision model
- `microsoft/phi-4-multimodal-instruct` - Efficient multimodal

### Embedding Models

- `nvidia/nv-embedqa-e5-v5` - Optimized for Q&A (default)
- `nvidia/nv-embed-v2` - General-purpose embeddings

## Best Practices

1. **Model Selection**: Choose models based on your use case (see Model Selection Guide)
2. **Timeout Configuration**: Adjust timeouts per service type (chat, vision, etc.)
3. **Batch Processing**: Use batch endpoints for embeddings when processing multiple texts
4. **Error Handling**: Check `nvcf_reqid` and `nvcf_status` headers for debugging
5. **Rate Limiting**: Monitor NVIDIA-specific headers for rate limit information

## Error Handling

NVIDIA API responses include special headers:

- `Nvcf-Reqid`: Request ID for tracking
- `Nvcf-Status`: Request status (fulfilled, processing, etc.)
- `Nvcf-Percent-Complete`: Progress for long-running requests

These are automatically included in all responses.

## NIM (Self-Hosted) Setup

For self-hosted deployments:

1. Deploy NVIDIA NIM on your infrastructure
2. Set `nim_base_url` in config to your NIM endpoint
3. Use `/api/v1/nvidia/nim/*` endpoints for inference

## Migration from Other Providers

NVIDIA API is OpenAI-compatible, making migration straightforward:

1. Update API key in config
2. Change `base_url` to NVIDIA endpoint
3. Update model names to NVIDIA model IDs
4. Test with existing code - should work with minimal changes

## Support

For issues or questions:

- NVIDIA API Docs: [https://build.nvidia.com/explore/discover](https://build.nvidia.com/explore/discover)
- Check logs for `Nvcf-Reqid` when reporting issues
