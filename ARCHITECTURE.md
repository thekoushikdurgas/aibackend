# DurgasAI Backend Architecture

## High-level

- Framework: FastAPI
- Primary API surface: WebSocket JSON-RPC 2.0 (`/ws/gateway`)
- Method handlers: `app/api/ws_methods/*`
- Core services: LLM providers, Council orchestration, RAG pipeline, memory, storage

## Runtime flow

1. Client connects to `/ws/gateway`
2. Gateway validates JSON-RPC request and auth data
3. Method dispatch routes to handler from `ws_methods`
4. Handler calls service layer (`app/services/*`)
5. Response is returned as JSON-RPC result or stream chunks

## Data stores

- SQLAlchemy DB:
  - Development default: SQLite
  - Production preferred: PostgreSQL via `effective_database_url`
- Vector store:
  - ChromaDB persisted under `./data/chroma`
- Object/file storage:
  - Local filesystem + HMAC-signed URLs (`StorageService` → `local_storage_service`)
  - Optional AWS integration hook: `S3StorageAdapter` stub

## Config notes

- Main settings: `app/config.py` (`Settings` as **pydantic-settings** `BaseSettings`)
- Values from **environment variables** and optional **`.env`** in the `ai.backend` root; see **`.env.example`** and **`config/README.md`**
- WebSocket module registry:
  - `app/api/ws_methods/registry.py`
