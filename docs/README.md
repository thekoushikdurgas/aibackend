# DurgasAI Backend Documentation

## WebSocket API Documentation

This backend uses a **WebSocket-only architecture** with **JSON-RPC 2.0** protocol. All operations are performed through a single WebSocket endpoint.

### Quick Start

1. **Connect to WebSocket:**

   ```
   ws://localhost:8000/ws/gateway
   ```

2. **Send JSON-RPC Request:**

   ```json
   {
     "jsonrpc": "2.0",
     "id": "req-1",
     "method": "system.health",
     "params": {}
   }
   ```

3. **Receive Response:**

   ```json
   {
     "jsonrpc": "2.0",
     "id": "req-1",
     "result": {
       "status": "healthy"
     }
   }
   ```

### Documentation Files

- **[WEBSOCKET_API.md](WEBSOCKET_API.md)** - Complete API reference

  - Connection details
  - JSON-RPC 2.0 protocol
  - All available methods
  - Request/response examples
  - Authentication
  - Streaming
  - File uploads

- **[API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md)** - Quick reference guide

  - Method index
  - Common parameters
  - Error codes
  - Streaming types

- **[EXAMPLES.md](EXAMPLES.md)** - Code examples
  - JavaScript/TypeScript examples
  - Python examples
  - Complete chat application
  - Error handling patterns
  - Retry logic

### Key Features

- **Single Endpoint**: All operations through `/ws/gateway`
- **JSON-RPC 2.0**: Standard RPC protocol
- **Real-time Streaming**: All operations support streaming
- **Base64 File Uploads**: Unified file handling
- **Connection-level Auth**: Authenticate once per connection
- **50+ Methods**: Chat, Agents, Vision, Multimodal, RAG, and more

### Method Categories

1. **System** - Health checks and status
2. **Chat** - LLM completions and conversations
3. **Agents** - Page analysis and SEO
4. **Vision** - Image analysis
5. **Multimodal** - Text-to-image, speech-to-text, etc.
6. **Providers** - Groq, NVIDIA, Ollama, etc.
7. **RAG** - Retrieval-Augmented Generation
8. **Metrics** - Usage and performance metrics

### Getting Started

1. Read [WEBSOCKET_API.md](WEBSOCKET_API.md) for complete documentation
2. Check [EXAMPLES.md](EXAMPLES.md) for code samples
3. Use [API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md) as a cheat sheet

### Support

For issues or questions:

- Check error messages in responses
- Review method parameter requirements
- Verify authentication tokens/keys
- Ensure WebSocket connection is stable
