# Changelog

## [2.0.0] - WebSocket-Only Architecture

### Major Changes

- **BREAKING**: Removed all REST API endpoints (244+ endpoints)
- **NEW**: Implemented WebSocket-only architecture with JSON-RPC 2.0 protocol
- **NEW**: Single WebSocket endpoint `/ws/gateway` for all operations
- **NEW**: Real-time streaming for all operations
- **NEW**: Base64 file upload system for unified file handling

### Added

- JSON-RPC 2.0 protocol implementation
- WebSocket gateway with method routing
- 50+ JSON-RPC methods covering all previous REST functionality
- Connection-level and per-message authentication
- Comprehensive test suite
- Complete API documentation

### Changed

- All operations now use WebSocket instead of HTTP
- File uploads use base64 encoding instead of multipart/form-data
- Authentication via WebSocket connection or per-message auth
- Streaming is built into all applicable methods

### Removed

- All REST API endpoints (`/api/v1/*`)
- HTTP-based file upload endpoints
- REST route handlers (53+ files)

### Migration

See [MIGRATION_NOTES.md](../MIGRATION_NOTES.md) for detailed migration guide.

### Documentation

- [WEBSOCKET_API.md](WEBSOCKET_API.md) - Complete API reference
- [API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md) - Quick reference
- [EXAMPLES.md](EXAMPLES.md) - Code examples
