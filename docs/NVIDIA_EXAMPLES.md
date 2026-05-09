# NVIDIA AI API Examples

Complete examples for using NVIDIA AI API endpoints.

## Chat Completions

### Basic Chat

```bash
curl -X POST "http://localhost:8000/api/v1/nvidia/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is artificial intelligence?"}
    ],
    "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
    "temperature": 0.7,
    "max_tokens": 1024
  }'
```

### Streaming Chat

```bash
curl -X POST "http://localhost:8000/api/v1/nvidia/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ],
    "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
    "stream": true
  }'
```

### Python Example

```python
import httpx
import asyncio

async def chat_example():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/nvidia/chat/completions",
            json={
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Explain quantum computing"}
                ],
                "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
                "temperature": 0.7,
                "max_tokens": 500
            }
        )
        data = response.json()
        print(data["choices"][0]["message"]["content"])

asyncio.run(chat_example())
```

### Reasoning Model

```python
response = await client.post(
    "http://localhost:8000/api/v1/nvidia/chat/completions",
    json={
        "messages": [
            {"role": "user", "content": "If I dry one shirt in the sun, it takes 1 hour. How long do 3 shirts take?"}
        ],
        "model": "deepseek-ai/deepseek-r1",
        "temperature": 0.5
    }
)
```

## Embeddings

### Single Text Embedding

```bash
curl -X POST "http://localhost:8000/api/v1/nvidia/embeddings" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What is machine learning?",
    "model": "nvidia/nv-embedqa-e5-v5",
    "input_type": "query"
  }'
```

### Batch Embeddings

```bash
curl -X POST "http://localhost:8000/api/v1/nvidia/embeddings/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Machine learning is a subset of AI",
      "Deep learning uses neural networks",
      "Natural language processing enables text understanding"
    ],
    "model": "nvidia/nv-embedqa-e5-v5",
    "input_type": "passage"
  }'
```

### Python RAG Example

```python
async def rag_example():
    async with httpx.AsyncClient() as client:
        # Embed query
        query_response = await client.post(
            "http://localhost:8000/api/v1/nvidia/embeddings",
            json={
                "input": "What is AI?",
                "model": "nvidia/nv-embedqa-e5-v5",
                "input_type": "query"
            }
        )
        query_embedding = query_response.json()["data"][0]["embedding"]

        # Embed documents
        docs_response = await client.post(
            "http://localhost:8000/api/v1/nvidia/embeddings/batch",
            json={
                "texts": ["Document 1", "Document 2", "Document 3"],
                "model": "nvidia/nv-embedqa-e5-v5",
                "input_type": "passage"
            }
        )
        doc_embeddings = [item["embedding"] for item in docs_response.json()["data"]]

        # Find most similar (simplified - use proper vector DB in production)
        # ... similarity search logic ...
```

## Vision Analysis

### Image URL Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/nvidia/vision/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is in this image? Describe it in detail.",
    "image_url": "https://example.com/image.jpg",
    "model": "meta/llama-3.2-90b-vision-instruct"
  }'
```

### Base64 Image Analysis

```python
import base64

# Read and encode image
with open("image.jpg", "rb") as f:
    image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

response = await client.post(
    "http://localhost:8000/api/v1/nvidia/vision/analyze",
    json={
        "prompt": "Analyze this image",
        "image": image_b64,
        "model": "meta/llama-3.2-90b-vision-instruct"
    }
)
```

### Multi-Image Analysis

```python
response = await client.post(
    "http://localhost:8000/api/v1/nvidia/vision/multimodal",
    json={
        "prompt": "Compare these two images. What are the differences?",
        "image_urls": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ],
        "model": "meta/llama-3.2-90b-vision-instruct"
    }
)
```

### Video Frame Analysis

```python
# Extract frames from video (using opencv or similar)
frames_base64 = [frame1_b64, frame2_b64, frame3_b64]

response = await client.post(
    "http://localhost:8000/api/v1/nvidia/vision/video-frames",
    json={
        "prompt": "What happens in this video?",
        "frames": frames_base64,
        "model": "meta/llama-3.2-90b-vision-instruct"
    }
)
```

## NIM (Self-Hosted)

### Health Check

```bash
curl "http://localhost:8000/api/v1/nvidia/nim/health"
```

### List Deployed Models

```bash
curl "http://localhost:8000/api/v1/nvidia/nim/models"
```

### Run Inference

```bash
curl -X POST "http://localhost:8000/api/v1/nvidia/nim/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "my-deployed-model",
    "messages": [
      {"role": "user", "content": "Hello"}
    ],
    "temperature": 0.7
  }'
```

## Image Generation

```bash
curl -X POST "http://localhost:8000/api/v1/nvidia/image/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "model": "stabilityai/sdxl-turbo",
    "steps": 4,
    "width": 1024,
    "height": 1024
  }'
```

## Video Generation

```python
# First generate or get an image
image_b64 = "..."  # Your base64 image

response = await client.post(
    "http://localhost:8000/api/v1/nvidia/video/generate",
    json={
        "image": image_b64,
        "model": "stabilityai/stable-video-diffusion",
        "motion_bucket_id": 127
    }
)
```

## Integrated Routes

### Using NVIDIA through Unified Chat Route

```python
response = await client.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "Hello",
        "provider": "nvidia",
        "model": "nvidia/llama-3.3-nemotron-super-49b-v1"
    }
)
```

### Using NVIDIA Embeddings

```python
response = await client.post(
    "http://localhost:8000/api/v1/embeddings/nvidia",
    json={
        "input": "Hello world",
        "model": "nvidia/nv-embedqa-e5-v5"
    }
)
```

## Error Handling

```python
try:
    response = await client.post(
        "http://localhost:8000/api/v1/nvidia/chat/completions",
        json={"messages": [{"role": "user", "content": "Hello"}]}
    )
    response.raise_for_status()
    data = response.json()

    # Check NVIDIA-specific headers
    nvcf_reqid = response.headers.get("Nvcf-Reqid")
    nvcf_status = response.headers.get("Nvcf-Status")

    print(f"Request ID: {nvcf_reqid}")
    print(f"Status: {nvcf_status}")

except httpx.HTTPStatusError as e:
    error_data = e.response.json()
    print(f"Error: {error_data}")
```

## Advanced Patterns

### Function Calling

```python
response = await client.post(
    "http://localhost:8000/api/v1/nvidia/chat/completions",
    json={
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?"}
        ],
        "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        }
                    }
                }
            }
        ]
    }
)
```

### Structured Output (JSON Mode)

```python
response = await client.post(
    "http://localhost:8000/api/v1/nvidia/vision/analyze",
    json={
        "prompt": "Extract all text from this image and return as JSON",
        "image_url": "https://example.com/document.jpg",
        "response_format": "json_object"
    }
)
```
