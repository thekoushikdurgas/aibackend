# WebSocket API Quick Reference

## Connection

```
ws://localhost:8000/ws/gateway
```

## Request Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-id",
  "method": "method.name",
  "params": {},
  "auth": { "type": "jwt", "token": "..." }
}
```

## Method Index

### System

- `system.health` - System health check
- `system.ready` - Readiness probe
- `system.live` - Liveness probe

### Chat

- `chat.completions` - Generate chat response
- `chat.providers` - List providers
- `chat.providers.models` - List provider models
- `chat.conversations.list` - List conversations
- `chat.conversations.get` - Get conversation
- `chat.conversations.delete` - Delete conversation

### Agents

- `agents.list` - List agents
- `agents.analyze` - Analyze with agent
- `agents.auto_analyze` - Auto-select agent
- `agents.batch_analyze` - Batch analysis
- `agents.quick_seo` - Quick SEO check
- `agents.summarize` - Summarize page

### Vision

- `vision.analyze` - Analyze image
- `vision.nvidia` - NVIDIA vision

### Multimodal

- `multimodal.text_to_image` - Generate image
- `multimodal.image_to_text` - Extract text from image
- `multimodal.speech_to_text` - Transcribe audio
- `multimodal.text_to_speech` - Text to speech
- `multimodal.object_detection` - Detect objects

### Groq

- `groq.chat.completions` - Chat completions
- `groq.vision.analyze` - Vision analysis
- `groq.transcribe` - Audio transcription
- `groq.models.list` - List models

### NVIDIA

- `nvidia.chat.completions` - Chat completions
- `nvidia.vision.analyze` - Vision analysis
- `nvidia.embeddings` - Generate embeddings
- `nvidia.models.list` - List models

### Ollama

- `ollama.generate` - Text generation
- `ollama.chat` - Chat completion
- `ollama.models.list` - List models
- `ollama.models.pull` - Pull model

### RAG

- `rag.query` - Query RAG system
- `rag.ingest` - Ingest document
- `rag.delete` - Delete document
- `rag.list` - List documents

### Metrics

- `metrics.summary` - Get summary
- `metrics.providers` - Provider metrics

### Authentication

- `auth.connect` - Authenticate connection

## Common Parameters

### Chat Completions

```json
{
  "message": "string (required)",
  "provider": "string (optional)",
  "model": "string (optional)",
  "temperature": "number (0-2, default: 0.7)",
  "max_tokens": "number (default: 2048)",
  "stream": "boolean (default: false)",
  "use_rag": "boolean (default: false)",
  "conversation_id": "string (optional)"
}
```

### File Upload

```json
{
  "file": {
    "data": "base64-string (required)",
    "mime_type": "string (required)"
  }
}
```

## Streaming Response Types

- `start` - Streaming started
- `chunk` - Content chunk
- `done` - Streaming complete
- `error` - Streaming error

## Error Codes

- `-32700` - Parse error
- `-32600` - Invalid request
- `-32601` - Method not found
- `-32602` - Invalid params
- `-32603` - Internal error
- `-32001` - Authentication error
- `-32005` - Provider error
