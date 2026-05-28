# Documentation Index

## Getting Started

1. **[README.md](../README.md)** - Main project README with quick start guide
2. **[MIGRATION_NOTES.md](../MIGRATION_NOTES.md)** - Guide for migrating from REST to WebSocket

## API Documentation

### Core Documentation

- **[WEBSOCKET_API.md](WEBSOCKET_API.md)** ⭐ **START HERE**

  - Complete API reference
  - JSON-RPC 2.0 protocol details
  - All available methods
  - Request/response formats
  - Authentication
  - Streaming
  - File uploads

- **[API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md)**

  - Quick method index
  - Common parameters
  - Error codes
  - Streaming types

- **[EXAMPLES.md](EXAMPLES.md)**
  - JavaScript/TypeScript examples
  - Python examples
  - Complete chat application
  - Error handling patterns
  - Retry logic

## Provider-Specific Documentation

- **[GROQ_INTEGRATION.md](GROQ_INTEGRATION.md)** - Groq API integration
- **[NVIDIA_API_GUIDE.md](NVIDIA_API_GUIDE.md)** - NVIDIA AI integration
- **[OPENROUTER_API.md](OPENROUTER_API.md)** - OpenRouter integration
- **[DEEPINFRA_GUIDE.md](DEEPINFRA_GUIDE.md)** - DeepInfra integration
- **[HUGGINGFACE_API.md](HUGGINGFACE_API.md)** - HuggingFace integration
- **[HYPERBOLIC_API.md](HYPERBOLIC_API.md)** - Hyperbolic API

## Implementation Details

- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical implementation details
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

## Testing & Development

- **[API_BENCHMARK.md](API_BENCHMARK.md)** - Performance benchmarks
- Test files in `../tests/test_ws_*.py`

## Postman Collections

Postman collections for various providers are available in this directory (`.postman_collection.json` files).

## Quick Links

- **WebSocket Endpoint**: `ws://localhost:8000/ws/gateway`
- **Protocol**: JSON-RPC 2.0
- **Health Check**: `GET /health` (HTTP) or `system.health` (WebSocket)
- **Status**: `GET /ws/status` (HTTP)

## Need Help?

1. Check [WEBSOCKET_API.md](WEBSOCKET_API.md) for complete API reference
2. Review [EXAMPLES.md](EXAMPLES.md) for code samples
3. See [MIGRATION_NOTES.md](../MIGRATION_NOTES.md) for migration help
