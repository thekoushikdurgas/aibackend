# HuggingFace API Integration Guide

## Overview

This backend provides comprehensive integration with HuggingFace APIs, including:

- **Chat Completions** via Router (multiple providers)
- **Inference API** for multimodal tasks
- **Gradio Spaces** for RAG and Agentic AI
- **Object Detection** for image analysis

## Table of Contents

1. [Chat Completions](#chat-completions)
2. [Multimodal APIs](#multimodal-apis)
3. [Gradio Spaces](#gradio-spaces)
4. [Object Detection](#object-detection)
5. [Rate Limits and Error Handling](#rate-limits-and-error-handling)
6. [Model Selection Guide](#model-selection-guide)

## Chat Completions

### Supported Providers

All providers are accessible via HuggingFace Router using a single API key:

- **HuggingFace Native** (`hf`)
- **Cerebras** (`cerebras`)
- **Fireworks AI** (`fireworks`)
- **Groq** (`groq`)
- **Nebius AI** (`nebius`)
- **Novita** (`novita`)
- **SambaNova** (`sambanova`)
- **Scaleway** (`scaleway`)
- **Together AI** (`together`)

### Usage

```python
from app.services.llm.huggingface import HuggingFaceProvider

provider = HuggingFaceProvider(
    api_key="your_hf_token",
    provider="cerebras"  # or "groq", "fireworks", etc.
)

response = await provider.generate(
    prompt="What is AI?",
    config=LLMConfig(
        model="meta-llama/Llama-4-Scout-17B-16E-Instruct",
        max_tokens=500,
        temperature=0.7
    )
)
```

### Recommended Models by Provider

#### Cerebras

- `meta-llama/Llama-4-Scout-17B-16E-Instruct`
- `meta-llama/Llama-3.3-70B-Instruct`
- `gpt-oss-120b`

#### Fireworks AI

- `deepseek-r1`
- `openai/gpt-oss-120b`
- `openai/gpt-oss-20b`
- `qwen3-30b-a3b`
- `qwen3-235b-a22b`

#### Groq

- `moonshotai/kimi-k2-instruct`
- `openai/gpt-oss-120b`
- `openai/gpt-oss-20b`

#### Together AI

- `deepseek-ai/DeepSeek-R1`
- `moonshotai/Kimi-K2-Instruct`
- `openai/gpt-oss-120b`
- `openai/gpt-oss-20b`

#### Nebius AI

- `google/gemma-3-27b-it`
- `Qwen/Qwen3-Embedding-8B`

#### Novita

- `deepseek/deepseek-prover-v2-671b`
- `meta-llama/llama-4-scout-17b-16e-instruct`
- `meta-llama/llama-4-maverick-17b-128e-instruct-fp8`
- `moonshotai/kimi-k2-instruct`

## Multimodal APIs

### Text-to-Image

Supports FLUX.1, Stable Diffusion 3.5, and other models.

**Endpoint:** `POST /api/multimodal/text-to-image`

```json
{
  "prompt": "A beautiful sunset over mountains",
  "model": "black-forest-labs/FLUX.1-dev",
  "negative_prompt": "blurry, low quality",
  "num_inference_steps": 50,
  "guidance_scale": 7.5
}
```

**Supported Models:**

- `black-forest-labs/FLUX.1-dev`
- `black-forest-labs/FLUX.1-schnell`
- `stabilityai/stable-diffusion-xl-base-1.0`
- `stabilityai/stable-diffusion-3.5-large`
- `stabilityai/stable-diffusion-3.5-large-turbo`
- `stabilityai/stable-diffusion-3.5-medium`

### Image-to-Text

**Endpoint:** `POST /api/multimodal/image-to-text`

**Supported Models:**

- `Salesforce/blip-image-captioning-large`

### Speech-to-Text

**Endpoint:** `POST /api/multimodal/speech-to-text`

**Supported Models:**

- `openai/whisper-large-v3`
- `openai/whisper-large-v3-turbo`

### Text-to-Speech

**Endpoint:** `POST /api/multimodal/text-to-speech`

**Supported Models:**

- `facebook/fastspeech2-en-ljspeech`

### Text-to-Audio

**Endpoint:** `POST /api/multimodal/text-to-audio`

**Supported Models:**

- `facebook/musicgen-small`
- `facebook/musicgen-stereo-large`

### Summarization

**Endpoint:** `POST /api/nlp/summarize`

**Supported Models:**

- `facebook/bart-large-cnn`

## Gradio Spaces

Gradio Spaces provide async RAG and Agentic AI capabilities.

### Async Pattern

Gradio Spaces use an async pattern:

1. **POST** request returns `event_id`
2. **GET** request polls for results using `event_id`
3. Results come as Server-Sent Events (SSE)

### Naive RAG

Simple question-answering with LangChain.

**Start:** `POST /api/hf-spaces/rag/naive`

```json
{
  "question": "What is the GPT-4 API's cost?",
  "framework": "LangChain",
  "api_key": "optional-openai-key"
}
```

**Poll:** `GET /api/hf-spaces/rag/naive/{event_id}`

**Complete (wait):** `POST /api/hf-spaces/rag/naive/complete`

### Advanced RAG

Recommendation system with retrieval pre/post-processing.

**Start:** `POST /api/hf-spaces/rag/advanced`

```json
{
  "question": "Recommend hotels near Financial District",
  "num_results": 2,
  "rerank": 1,
  "api_key": "optional-openai-key"
}
```

**Poll:** `GET /api/hf-spaces/rag/advanced/{event_id}`

### Agentic RAG - crewAI

Multi-agent deep research system.

**Start:** `POST /api/hf-spaces/agentic/crewai`

```json
{
  "question": "Research quantum computing advances",
  "api_key": "optional-key"
}
```

**Poll:** `GET /api/hf-spaces/agentic/crewai/{event_id}`

### Agentic RAG - LangGraph

Multi-agent system with LangGraph.

**Start:** `POST /api/hf-spaces/agentic/langgraph`

```json
{
  "question": "Deep research on AI safety",
  "api_key": "optional-key"
}
```

### Agentic RAG - OpenAI Assistants

Uses OpenAI Assistants API for research.

**Start:** `POST /api/hf-spaces/agentic/openai`

```json
{
  "question": "Research topic",
  "api_key": "required-openai-key"
}
```

**Note:** OpenAI API key is required for this endpoint.

## Object Detection

Detect objects in images with bounding boxes.

**Endpoint:** `POST /api/multimodal/object-detection`

**Request (URL):**

```json
{
  "image_url": "https://example.com/image.jpg",
  "model": "facebook/detr-resnet-50",
  "min_score": 0.5
}
```

**Request (Base64):**

```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
  "min_score": 0.5
}
```

**Request (Upload):**

```
POST /api/multimodal/object-detection/upload
Content-Type: multipart/form-data

file: [image file]
min_score: 0.5
```

**Response:**

```json
{
  "detections": [
    {
      "label": "sports ball",
      "score": 0.99,
      "box": {
        "xmin": 95,
        "ymin": 444,
        "xmax": 172,
        "ymax": 515
      }
    }
  ],
  "model": "facebook/detr-resnet-50",
  "count": 1
}
```

**Supported Models:**

- `facebook/detr-resnet-50`

## Rate Limits and Error Handling

### Rate Limits

HuggingFace API includes rate limit headers:

- `x-ratelimit-limit-requests-day`: Daily request limit
- `x-ratelimit-remaining-requests-day`: Remaining requests
- `x-ratelimit-limit-tokens-minute`: Token limit per minute
- `x-ratelimit-remaining-tokens-minute`: Remaining tokens

### Model Loading (503 Errors)

When a model is loading, the API returns 503 with `estimated_time`. The client automatically:

- Waits for the estimated time
- Retries up to 3 times
- Uses exponential backoff

### Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad request (missing parameters, invalid input)
- `401`: Unauthorized (invalid API key)
- `429`: Rate limit exceeded
- `503`: Model loading (auto-retried)
- `500`: Server error

## Model Selection Guide

### For Speed

- **Groq**: Fastest inference, good for real-time applications
- **Fireworks AI**: Fast with good quality
- **FLUX.1-schnell**: Fast image generation

### For Quality

- **Cerebras**: High-quality models, good reasoning
- **Together AI**: Large models, excellent quality
- **FLUX.1-dev**: Best image quality

### For Cost

- **HuggingFace Native**: Free tier available
- **Groq**: Cost-effective for high volume
- **Together AI**: Competitive pricing

### For Specific Tasks

**Reasoning:**

- `deepseek-ai/DeepSeek-R1`
- `meta-llama/Llama-4-Scout-17B-16E-Instruct`

**Coding:**

- `qwen-2.5-coder-32b` (via Groq)

**Vision:**

- `llama-3.2-11b-vision-preview` (via Groq)

**Multilingual:**

- `moonshotai/kimi-k2-instruct`
- `Qwen/Qwen2.5-72B-Instruct`

## Configuration

Add to `config/config.json`:

```json
{
  "llm": {
    "providers": {
      "huggingface": {
        "api_key": "your_hf_token",
        "model": "mistralai/Mistral-7B-Instruct-v0.2",
        "inference_provider": "hf",
        "object_detection_model": "facebook/detr-resnet-50",
        "gradio_spaces": {
          "naive_rag": "https://bstraehle-rag.hf.space",
          "advanced_rag": "https://bstraehle-advanced-rag.hf.space",
          "agentic_crewai": "https://bstraehle-multi-agent-crewai.hf.space",
          "agentic_langgraph": "https://bstraehle-multi-agent-langgraph.hf.space"
        }
      }
    }
  }
}
```

## Examples

### Complete Chat Workflow

```python
from app.services.llm.huggingface import HuggingFaceProvider
from app.services.llm.base import LLMConfig

provider = HuggingFaceProvider(provider="groq")

response = await provider.generate(
    prompt="Explain quantum computing",
    config=LLMConfig(
        model="moonshotai/kimi-k2-instruct",
        max_tokens=1000,
        temperature=0.7
    )
)

print(response.text)
```

### Object Detection

```python
from app.services.multimodal.object_detection import ObjectDetectionService

service = ObjectDetectionService()

detections = await service.detect_from_url(
    "https://example.com/image.jpg"
)

for obj in detections:
    print(f"{obj['label']}: {obj['score']:.2f}")
```

### Gradio Spaces RAG

```python
from app.services.huggingface.spaces import RAGService

rag = RAGService()

# Async workflow
response = await rag.naive_rag_predict("What is AI?")
event_id = response["event_id"]
result = await rag.naive_rag_poll(event_id)

# Or complete workflow
result = await rag.naive_rag("What is AI?")
```
