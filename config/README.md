# Legacy `config/` directory

Runtime configuration for the FastAPI backend lives on the **`Settings`** model in [`app/config.py`](../app/config.py), loaded from **environment variables** and an optional **`.env`** file in the `ai.backend` root. See [`.env.example`](../.env.example) for all supported variables.

Older versions of this project used JSON files such as `config/config.json`. Those files are **no longer read** by the application. Migrate by copying each value into `.env` using the matching `UPPER_SNAKE_CASE` name (for example `GROQ_API_KEY`, `DATABASE_URL`).

This folder is kept so Docker builds (`COPY config/ ./config/` in `docker/Dockerfile`) and documentation links remain valid. You do not need to add JSON files here for normal operation.
