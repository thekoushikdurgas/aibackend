# DurgasAI Backend

FastAPI backend with AI agents for the DurgasAI Chrome extension.

## Features

- **WebSocket-Only Architecture**: All operations via single WebSocket endpoint using JSON-RPC 2.0
- **Multi-Provider LLM Support**: Ollama, Hugging Face, Google Gemini, Groq, NVIDIA, AI21, and more
- **AI Agents**: Specialized agents for page analysis, content extraction, SEO, and more
- **RAG System**: ChromaDB-powered semantic search and retrieval
- **Real-time Streaming**: All operations support real-time streaming responses
- **Base64 File Uploads**: Unified file handling for images, audio, and documents
- **Production Ready**: JWT auth, rate limiting, Docker support

## Quick Start

### Prerequisites

- Python 3.10+
- Ollama (optional, for local models)
- Redis (optional, for caching)

### Installation

1. Clone and navigate to the backend directory:

```bash
cd backend
```

2. Create virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy and configure environment:

```bash
cp config/config.example.json config/config.json
# Edit config/config.json with your settings
```

5. Run the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Using Docker

Full reference: **[docker/README.md](./docker/README.md)**.

**Steps (short):**

1. **`cd ai.backend`**
2. **`cp .env.example .env`** and fill secrets (Compose expects `.env` here). On Linux/macOS you can use **`./scripts/docker-up.sh`** instead of manual `docker compose` — it copies env templates and runs the stack (see [docker/README.md](./docker/README.md)).
3. Ensure **`config/config.json`** exists (copy from `config/config.example.json` if your tree uses that layout).
4. **Production-style stack** (Postgres + Redis + ChromaDB + Ollama + API):

   ```bash
   docker compose up -d --build
   ```

   Same as `docker compose -f docker/docker-compose.yml up -d --build` (root [`compose.yaml`](./compose.yaml) includes `docker/docker-compose.yml`; requires **Compose v2.20+** for `include:`).

5. **Development stack** (bind-mount `app/`, `--reload`, Redis + ChromaDB + Ollama):

   ```bash
   docker compose -f compose.dev.yaml up --build
   ```

6. Check **`curl http://localhost:8000/health`**.

On **Linux/macOS**, [`scripts/docker-up.sh`](./scripts/docker-up.sh) wraps the same Compose commands as `scripts\docker-up.bat`. For a full local quality gate (same steps as [`codebase.bat`](./codebase.bat)), run **`./codebase.sh`** from `ai.backend`; use **`SKIP_DEV_SERVER=1`** in CI or SSH so the script does not prompt to start uvicorn.

**Endpoints:** HTTP GraphQL `POST http://localhost:8000/graphql`. WebSocket JSON-RPC `ws://localhost:8000/ws/gateway`.

Build context excludes `venv/` and tests via [`.dockerignore`](./.dockerignore).

### GitHub Actions

| Workflow   | File                                                             | Purpose                                                                                                                                                                                                                                                       |
| ---------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **API CI** | [`.github/workflows/api-ci.yml`](./.github/workflows/api-ci.yml) | On push/PR: **ruff**, **black**, **mypy** (non-blocking), optional `scripts/check_best_practices.py`, **pytest** + coverage with **Postgres 16** service. Installs `requirements.txt` + [`requirements-dev.txt`](./requirements-dev.txt).                     |
| **Deploy** | [`.github/workflows/deploy.yml`](./.github/workflows/deploy.yml) | On push to `main`: SSH to EC2 (secrets `EC2_*`, `ENV_FILE`), `git reset`, run [`deploy/remote-deploy.sh`](./deploy/remote-deploy.sh). Edit `APP_ROOT` in the workflow and on the server to match your clone path (monorepo: e.g. `.../durgas_ai/ai.backend`). |

## API Documentation

**Architecture**: This backend uses **100% WebSocket-only** architecture with **JSON-RPC 2.0** protocol. All operations go through a single WebSocket endpoint.

### WebSocket Endpoint

```
ws://localhost:8000/ws/gateway
```

### Documentation

- **Architecture Overview**: See [ARCHITECTURE.md](../ARCHITECTURE.md)
- **Complete API Reference**: See [API_REFERENCE.md](../API_REFERENCE.md)
- **Method Handlers**: See `app/api/ws_methods/` directory

### Quick Example

```javascript
// Connect
const ws = new WebSocket('ws://localhost:8000/ws/gateway');

// Send request
ws.send(
  JSON.stringify({
    jsonrpc: '2.0',
    id: 'req-1',
    method: 'chat.completions',
    params: {
      message: 'Hello!',
      provider: 'groq',
      stream: true,
    },
  })
);

// Receive streaming responses
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  if (response.result.type === 'chunk') {
    console.log(response.result.content);
  }
};
```

### Available Methods (50+)

**System**: `system.health`, `system.ready`, `system.live`

**Chat**: `chat.completions`, `chat.providers`, `chat.conversations.*`

**Agents**: `agents.list`, `agents.analyze`, `agents.auto_analyze`, `agents.batch_analyze`

**Vision**: `vision.analyze`, `vision.nvidia`

**Multimodal**: `multimodal.text_to_image`, `multimodal.image_to_text`, `multimodal.speech_to_text`, `multimodal.text_to_speech`

**Providers**: `groq.*`, `nvidia.*`, `ollama.*`, and more

**RAG**: `rag.query`, `rag.ingest`, `rag.delete`, `rag.list`

**Auth**: `auth.signup`, `auth.signin`, `auth.signout`, `auth.refresh`, `auth.verify`, `auth.reset_password_request`, `auth.reset_password`, `auth.update_user`, `auth.magic_link`, `auth.oauth_url`

**Storage**: `storage.upload`, `storage.download`, `storage.delete`, `storage.list`, `storage.move`, `storage.get_url`, `storage.create_signed_url`, `storage.buckets.list`

See [docs/API_QUICK_REFERENCE.md](docs/API_QUICK_REFERENCE.md) for complete method list.

## Available Agents

1. **Page Analyzer**: Deep HTML structure analysis
2. **Content Extractor**: Extract structured data
3. **SEO Agent**: SEO analysis and recommendations
4. **Image Analyzer**: Image analysis and optimization
5. **Research Agent**: Summarization and research
6. **Council Agent**: Multi-model deliberation with peer review
7. **Website Scraper**: Comprehensive website analysis with smart scraping

Use the `agents.list` method to get all available agents with descriptions.

## Configuration

See `config/config.example.json` for all configuration options. The application will automatically load environment-specific configs:

- `config/config.dev.json` when `ENVIRONMENT=development`
- `config/config.prod.json` when `ENVIRONMENT=production`
- `config/config.json` as fallback

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black app/
isort app/
```

## License

MIT
