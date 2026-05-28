# WebSocket API Documentation

## Overview

The DurgasAI Backend uses a **WebSocket-only architecture** with **JSON-RPC 2.0** protocol. All operations are performed through a single WebSocket endpoint using standardized JSON-RPC messages.

## Connection

### Endpoint

```
ws://localhost:8000/ws/gateway
```

### Authentication Options

**Option 1: Query Parameters (Connection-level)**

```
ws://localhost:8000/ws/gateway?token=YOUR_JWT_TOKEN
ws://localhost:8000/ws/gateway?api_key=YOUR_API_KEY
```

**Option 2: Per-Message Authentication**
Include `auth` field in each JSON-RPC request (see Authentication section).

### Connection Confirmation

Upon successful connection, you'll receive:

```json
{
  "jsonrpc": "2.0",
  "id": null,
  "result": {
    "type": "connected",
    "connection_id": "ws-abc123",
    "timestamp": "2024-01-01T00:00:00.000Z",
    "authenticated": true
  }
}
```

## JSON-RPC 2.0 Protocol

### Request Format

```json
{
  "jsonrpc": "2.0",
  "id": "request-id-123",
  "method": "method.name",
  "params": {
    "param1": "value1",
    "param2": "value2"
  },
  "auth": {
    "type": "jwt",
    "token": "your-jwt-token"
  }
}
```

### Response Format (Success)

```json
{
  "jsonrpc": "2.0",
  "id": "request-id-123",
  "result": {
    "data": "response data"
  }
}
```

### Response Format (Error)

```json
{
  "jsonrpc": "2.0",
  "id": "request-id-123",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "field": "message",
      "error": "Missing required parameter"
    }
  }
}
```

### Error Codes

| Code   | Name                 | Description                                 |
| ------ | -------------------- | ------------------------------------------- |
| -32700 | Parse error          | Invalid JSON was received                   |
| -32600 | Invalid Request      | The JSON sent is not a valid Request object |
| -32601 | Method not found     | The method does not exist                   |
| -32602 | Invalid params       | Invalid method parameter(s)                 |
| -32603 | Internal error       | Internal JSON-RPC error                     |
| -32001 | Authentication error | Authentication failed                       |
| -32002 | Authorization error  | Insufficient permissions                    |
| -32005 | Provider error       | AI provider error                           |
| -32006 | Service unavailable  | Service temporarily unavailable             |

## Authentication

### Connection-Level Authentication

Authenticate once per connection:

```json
{
  "jsonrpc": "2.0",
  "id": "auth-1",
  "method": "auth.connect",
  "params": {
    "token": "your-jwt-token"
  }
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": "auth-1",
  "result": {
    "status": "authenticated",
    "user": "user-id"
  }
}
```

### Per-Message Authentication

Include `auth` in each request:

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "chat.completions",
  "params": {...},
  "auth": {
    "type": "jwt",
    "token": "your-jwt-token"
  }
}
```

Or with API key:

```json
{
  "auth": {
    "type": "api_key",
    "api_key": "your-api-key"
  }
}
```

## Streaming Responses

For methods that support streaming, set `stream: true` in params. You'll receive multiple responses with the same `id`:

**Start Message:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "type": "start",
    "provider": "groq",
    "model": "llama-3.1-70b"
  }
}
```

**Chunk Messages:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "type": "chunk",
    "content": "Hello"
  }
}
```

**Completion Message:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "type": "done",
    "full_response": "Hello! How can I help?",
    "usage": {
      "tokens": 25
    }
  }
}
```

## File Uploads

All file uploads use **base64 encoding**. Files are sent as part of the JSON-RPC params:

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "vision.analyze",
  "params": {
    "image": {
      "data": "iVBORw0KGgoAAAANS...",
      "mime_type": "image/png"
    },
    "prompt": "What's in this image?"
  }
}
```

**Data URL Format (also supported):**

```json
{
  "image": {
    "data": "data:image/png;base64,iVBORw0KGgoAAAANS...",
    "mime_type": "image/png"
  }
}
```

## API Methods

### System Methods

#### `system.health`

Get system health status.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "system.health",
  "params": {}
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "status": "healthy",
    "version": "1.0.0",
    "environment": "development",
    "services": [
      {
        "name": "chromadb",
        "status": "healthy",
        "latency_ms": 12.5
      }
    ],
    "timestamp": "2024-01-01T00:00:00.000Z"
  }
}
```

#### `system.ready`

Simple readiness check.

#### `system.live`

Simple liveness check.

---

### Chat Methods

#### `chat.completions`

Generate chat completions using any LLM provider.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "chat.completions",
  "params": {
    "message": "Hello, how are you?",
    "provider": "groq",
    "model": "llama-3.1-70b",
    "temperature": 0.7,
    "max_tokens": 2048,
    "context": "Optional context",
    "conversation_id": "conv-123",
    "use_rag": false,
    "stream": false
  }
}
```

**Response (non-streaming):**

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "message": "Hello! I'm doing well, thank you for asking.",
    "provider": "groq",
    "model": "llama-3.1-70b",
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 15,
      "total_tokens": 25
    },
    "finish_reason": "stop"
  }
}
```

**Parameters:**

- `message` (required): User message
- `provider` (optional): LLM provider name (groq, nvidia, ollama, etc.)
- `model` (optional): Specific model name
- `temperature` (optional, default: 0.7): Sampling temperature
- `max_tokens` (optional, default: 2048): Maximum tokens to generate
- `context` (optional): Additional context
- `conversation_id` (optional): Conversation ID for history
- `use_rag` (optional, default: false): Enable RAG context retrieval
- `stream` (optional, default: false): Enable streaming response

#### `chat.providers`

List all available LLM providers.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-2",
  "method": "chat.providers",
  "params": {}
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-2",
  "result": {
    "providers": [
      {
        "name": "groq",
        "status": "available",
        "models": ["llama-3.1-70b", "mixtral-8x7b"]
      },
      {
        "name": "nvidia",
        "status": "available",
        "models": ["meta/llama-3-70b-instruct"]
      }
    ]
  }
}
```

#### `chat.providers.models`

List models for a specific provider.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-3",
  "method": "chat.providers.models",
  "params": {
    "provider_name": "groq"
  }
}
```

#### `chat.conversations.list`

List recent conversations.

#### `chat.conversations.get`

Get a specific conversation.

#### `chat.conversations.delete`

Delete a conversation.

---

### Agent Methods

#### `agents.list`

List all available agents.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-4",
  "method": "agents.list",
  "params": {}
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-4",
  "result": {
    "agents": [
      {
        "type": "page_analyzer",
        "description": "Deep page structure and organization analysis"
      },
      {
        "type": "seo",
        "description": "SEO analysis and optimization recommendations"
      }
    ]
  }
}
```

#### `agents.analyze`

Analyze a page using a specific agent.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-5",
  "method": "agents.analyze",
  "params": {
    "agent_type": "seo",
    "page_data": {
      "url": "https://example.com",
      "title": "Example Page",
      "html": "<html>...</html>",
      "meta": []
    },
    "query": "Analyze SEO",
    "options": {
      "target_keyword": "example"
    }
  }
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-5",
  "result": {
    "agent_type": "seo",
    "analysis": "Detailed analysis...",
    "summary": "SEO score: 85/100",
    "recommendations": ["Add meta description", "Improve heading structure"],
    "metadata": {
      "seo_score": 85,
      "title_score": 90
    },
    "timestamp": "2024-01-01T00:00:00.000Z"
  }
}
```

**Available Agent Types:**

- `page_analyzer`: Deep page structure analysis
- `content_extractor`: Extract structured data
- `seo`: SEO analysis and recommendations
- `image_analyzer`: Image optimization analysis
- `research`: Content summarization and research
- `council`: Multi-model deliberation
- `website_scraper`: Comprehensive website analysis

#### `agents.auto_analyze`

Automatically select the best agent based on query.

#### `agents.batch_analyze`

Run multiple agents on the same page.

#### `agents.quick_seo`

Quick SEO analysis with simplified output.

#### `agents.summarize`

Get a quick summary of page content.

---

### Vision Methods

#### `vision.analyze`

Analyze an image with a text prompt.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-6",
  "method": "vision.analyze",
  "params": {
    "image": {
      "data": "iVBORw0KGgoAAAANS...",
      "mime_type": "image/png"
    },
    "prompt": "What's in this image?",
    "config": {
      "model": "gemini-pro-vision"
    }
  }
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-6",
  "result": {
    "text": "This image shows a cat sitting on a windowsill.",
    "model": "gemini-pro-vision",
    "usage": {
      "tokens": 150
    }
  }
}
```

#### `vision.nvidia`

Analyze image using NVIDIA vision models.

---

### Multimodal Methods

#### `multimodal.text_to_image`

Generate an image from text prompt.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-7",
  "method": "multimodal.text_to_image",
  "params": {
    "prompt": "A beautiful sunset over mountains",
    "model": "flux-1",
    "negative_prompt": "blurry, low quality",
    "num_inference_steps": 50,
    "guidance_scale": 7.5
  }
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-7",
  "result": {
    "image_base64": "iVBORw0KGgoAAAANS...",
    "image_url": "https://...",
    "model": "flux-1",
    "prompt": "A beautiful sunset over mountains"
  }
}
```

#### `multimodal.image_to_text`

Extract text from an image.

#### `multimodal.speech_to_text`

Transcribe audio to text.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-8",
  "method": "multimodal.speech_to_text",
  "params": {
    "audio": {
      "data": "UklGRiQAAABXQVZF...",
      "mime_type": "audio/wav"
    },
    "language": "en"
  }
}
```

#### `multimodal.text_to_speech`

Convert text to speech.

#### `multimodal.object_detection`

Detect objects in an image.

---

### Provider-Specific Methods

#### Groq Methods

##### `groq.chat.completions`

Groq chat completions (OpenAI-compatible).

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-9",
  "method": "groq.chat.completions",
  "params": {
    "messages": [{ "role": "user", "content": "Hello" }],
    "model": "llama-3.1-70b",
    "temperature": 0.7,
    "max_tokens": 2048,
    "stream": false
  }
}
```

##### `groq.vision.analyze`

Analyze images using Groq vision models.

##### `groq.transcribe`

Transcribe audio using Groq.

##### `groq.models.list`

List available Groq models.

#### NVIDIA Methods

##### `nvidia.chat.completions`

NVIDIA chat completions.

##### `nvidia.vision.analyze`

NVIDIA vision analysis.

##### `nvidia.embeddings`

Generate embeddings using NVIDIA models.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-10",
  "method": "nvidia.embeddings",
  "params": {
    "text": "Hello world",
    "model": "nvidia/nv-embedqa-e5-v5"
  }
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-10",
  "result": {
    "embedding": [0.123, -0.456, ...],
    "model": "nvidia/nv-embedqa-e5-v5"
  }
}
```

##### `nvidia.models.list`

List available NVIDIA models.

#### Ollama Methods

##### `ollama.generate`

Generate text using Ollama.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-11",
  "method": "ollama.generate",
  "params": {
    "model": "llama2",
    "prompt": "Tell me a joke",
    "stream": false,
    "temperature": 0.7,
    "max_tokens": 100
  }
}
```

##### `ollama.chat`

Chat with Ollama models.

##### `ollama.models.list`

List available Ollama models.

##### `ollama.models.pull`

Pull/download an Ollama model.

---

### RAG Methods

#### `rag.query`

Query RAG system for relevant context.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-12",
  "method": "rag.query",
  "params": {
    "query": "What is machine learning?",
    "k": 5,
    "max_context_length": 4000
  }
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-12",
  "result": {
    "query": "What is machine learning?",
    "context": "Relevant context from documents...",
    "k": 5
  }
}
```

#### `rag.ingest`

Ingest a document into the RAG system.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-13",
  "method": "rag.ingest",
  "params": {
    "text": "Document content here...",
    "document_id": "doc-123",
    "metadata": {
      "title": "Document Title",
      "source": "https://example.com"
    }
  }
}
```

#### `rag.delete`

Delete a document from RAG system.

#### `rag.list`

List all documents in RAG system.

---

### Metrics Methods

#### `metrics.summary`

Get metrics summary.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-14",
  "method": "metrics.summary",
  "params": {}
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "req-14",
  "result": {
    "total_requests": 1000,
    "total_tokens": 50000,
    "providers": {
      "groq": { "requests": 500, "tokens": 25000 }
    }
  }
}
```

#### `metrics.providers`

Get provider-specific metrics.

---

## Client Examples

### JavaScript/TypeScript

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/gateway?token=YOUR_TOKEN');

// Handle connection
ws.onopen = () => {
  console.log('Connected');
};

// Handle messages
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);

  if (response.result) {
    if (response.result.type === 'chunk') {
      // Streaming chunk
      process.stdout.write(response.result.content);
    } else if (response.result.type === 'done') {
      // Streaming complete
      console.log('\nDone:', response.result.full_response);
    } else {
      // Regular response
      console.log('Result:', response.result);
    }
  } else if (response.error) {
    console.error('Error:', response.error);
  }
};

// Send request
function sendRequest(method, params, requestId) {
  const request = {
    jsonrpc: '2.0',
    id: requestId || `req-${Date.now()}`,
    method: method,
    params: params,
  };
  ws.send(JSON.stringify(request));
}

// Example: Chat completion
sendRequest(
  'chat.completions',
  {
    message: 'Hello!',
    provider: 'groq',
    stream: true,
  },
  'chat-1'
);
```

### Python

```python
import asyncio
import websockets
import json

async def chat_example():
    uri = "ws://localhost:8000/ws/gateway?api_key=YOUR_API_KEY"

    async with websockets.connect(uri) as websocket:
        # Receive connection confirmation
        response = await websocket.recv()
        print("Connected:", json.loads(response))

        # Send chat request
        request = {
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "chat.completions",
            "params": {
                "message": "Hello!",
                "provider": "groq",
                "stream": True
            }
        }
        await websocket.send(json.dumps(request))

        # Receive streaming responses
        while True:
            response = json.loads(await websocket.recv())
            if response.get("result", {}).get("type") == "chunk":
                print(response["result"]["content"], end="", flush=True)
            elif response.get("result", {}).get("type") == "done":
                print("\nDone!")
                break

asyncio.run(chat_example())
```

### cURL (for testing)

```bash
# Note: cURL doesn't support WebSocket natively
# Use wscat or similar tool instead

# Install wscat: npm install -g wscat

# Connect and send request
echo '{"jsonrpc":"2.0","id":"1","method":"system.health","params":{}}' | \
  wscat -c ws://localhost:8000/ws/gateway
```

## Keepalive

Send `ping` as plain text to receive `pong`:

```javascript
ws.send('ping');
// Server responds with: 'pong'
```

## Best Practices

1. **Reuse Connections**: Keep WebSocket connections open and reuse them
2. **Handle Reconnection**: Implement automatic reconnection logic
3. **Request IDs**: Use unique request IDs to match responses
4. **Error Handling**: Always check for `error` field in responses
5. **Streaming**: For long operations, use streaming to show progress
6. **File Sizes**: For large files (>1MB), consider chunked upload
7. **Rate Limiting**: Be mindful of rate limits per connection

## Rate Limits

Rate limiting is applied per connection. Check error responses for rate limit information:

```json
{
  "error": {
    "code": -32003,
    "message": "Rate limit exceeded",
    "data": {
      "retry_after": 60
    }
  }
}
```

## Support

For issues or questions:

- Check error messages for detailed information
- Verify authentication tokens/keys
- Ensure WebSocket connection is stable
- Review method parameter requirements
