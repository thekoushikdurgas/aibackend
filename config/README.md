# Backend config

Runtime configuration for the FastAPI backend lives on the **`Settings`** model in [`app/config.py`](../app/config.py), loaded from **environment variables** and **`ai.backend/.env`**. See [`.env.example`](../.env.example).

## Provider manifest

[`provider_manifest.json`](provider_manifest.json) catalogs every Postman collection under `docs/ai_provider/`:

- Provider `id` used by `LLMProviderFactory` and `chat.providers`
- `implementation`: `openai_compat`, `native`, `ws_only`, `benchmark`, `disabled`
- Env var names (`api_key_env`, `base_url_env`, `model_env`)

Regenerate after adding Postman files:

```bash
python scripts/postman_to_manifest.py --write
```

Root `config.json` is **legacy reference only** and is not read by the API.
