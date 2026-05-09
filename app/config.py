"""
Configuration management for DurgasAI Backend
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


def flatten_config(
    data: Dict[str, Any], parent_key: str = "", sep: str = "_"
) -> Dict[str, Any]:
    """
    Flatten nested dictionary structure to flat key-value pairs.
    Handles special mappings for provider-specific settings.
    """
    items: List[tuple] = []

    # Handle server section
    if "server" in data:
        server = data["server"]
        items.append(("host", server.get("host", "0.0.0.0")))
        items.append(("port", server.get("port", 8000)))
        items.append(("debug", server.get("debug", False)))
        items.append(("environment", server.get("environment", "development")))

    # Handle LLM section
    if "llm" in data:
        llm = data["llm"]
        items.append(("default_llm_provider", llm.get("default_provider", "ollama")))
        items.append(("default_model", llm.get("default_model", "llama3")))

        # Handle providers
        if "providers" in llm:
            providers = llm["providers"]

            # Ollama
            if "ollama" in providers:
                ollama = providers["ollama"]
                items.append(
                    (
                        "ollama_base_url",
                        ollama.get("base_url", "http://localhost:11434/api"),
                    )
                )
                items.append(
                    (
                        "ollama_cloud_url",
                        ollama.get("cloud_url", "https://ollama.com/api"),
                    )
                )
                items.append(("ollama_api_key", ollama.get("api_key")))
                items.append(("ollama_mode", ollama.get("mode", "localhost")))
                items.append(("ollama_model", ollama.get("model", "llama3")))

            # HuggingFace
            if "huggingface" in providers:
                hf = providers["huggingface"]
                items.append(("huggingface_api_key", hf.get("api_key")))
                items.append(
                    (
                        "huggingface_model",
                        hf.get("model", "mistralai/Mistral-7B-Instruct-v0.2"),
                    )
                )
                items.append(
                    (
                        "huggingface_inference_provider",
                        hf.get("inference_provider", "hf"),
                    )
                )
                items.append(
                    (
                        "hf_router_base_url",
                        hf.get("router_base_url", "https://router.huggingface.co"),
                    )
                )
                items.append(
                    (
                        "hf_inference_base_url",
                        hf.get(
                            "inference_base_url", "https://api-inference.huggingface.co"
                        ),
                    )
                )
                items.append(
                    (
                        "hf_text_to_image_model",
                        hf.get(
                            "text_to_image_model", "black-forest-labs/FLUX.1-schnell"
                        ),
                    )
                )
                items.append(
                    (
                        "hf_image_to_text_model",
                        hf.get(
                            "image_to_text_model",
                            "Salesforce/blip-image-captioning-large",
                        ),
                    )
                )
                items.append(
                    (
                        "hf_speech_to_text_model",
                        hf.get("speech_to_text_model", "openai/whisper-large-v3-turbo"),
                    )
                )
                items.append(
                    (
                        "hf_text_to_speech_model",
                        hf.get(
                            "text_to_speech_model", "facebook/fastspeech2-en-ljspeech"
                        ),
                    )
                )
                items.append(
                    (
                        "hf_text_to_audio_model",
                        hf.get("text_to_audio_model", "facebook/musicgen-small"),
                    )
                )
                items.append(
                    (
                        "hf_summarization_model",
                        hf.get("summarization_model", "facebook/bart-large-cnn"),
                    )
                )
                items.append(
                    (
                        "hf_embedding_model",
                        hf.get("embedding_model", "Qwen/Qwen3-Embedding-8B"),
                    )
                )
                items.append(
                    (
                        "hf_object_detection_model",
                        hf.get("object_detection_model", "facebook/detr-resnet-50"),
                    )
                )

                # Gradio Spaces URLs
                if "gradio_spaces" in hf:
                    spaces = hf["gradio_spaces"]
                    items.append(
                        (
                            "hf_spaces_naive_rag",
                            spaces.get("naive_rag", "https://bstraehle-rag.hf.space"),
                        )
                    )
                    items.append(
                        (
                            "hf_spaces_advanced_rag",
                            spaces.get(
                                "advanced_rag",
                                "https://bstraehle-advanced-rag.hf.space",
                            ),
                        )
                    )
                    items.append(
                        ("hf_spaces_agentic_crewai", spaces.get("agentic_crewai", ""))
                    )
                    items.append(
                        (
                            "hf_spaces_agentic_langgraph",
                            spaces.get("agentic_langgraph", ""),
                        )
                    )
                    items.append(
                        ("hf_spaces_agentic_openai", spaces.get("agentic_openai", ""))
                    )
                else:
                    items.append(
                        ("hf_spaces_naive_rag", "https://bstraehle-rag.hf.space")
                    )
                    items.append(
                        (
                            "hf_spaces_advanced_rag",
                            "https://bstraehle-advanced-rag.hf.space",
                        )
                    )
                    items.append(("hf_spaces_agentic_crewai", ""))
                    items.append(("hf_spaces_agentic_langgraph", ""))
                    items.append(("hf_spaces_agentic_openai", ""))

            # Gemini
            if "gemini" in providers:
                gemini = providers["gemini"]
                items.append(("gemini_api_key", gemini.get("api_key")))
                items.append(("gemini_model", gemini.get("model", "gemini-2.5-flash")))
                items.append(
                    (
                        "gemini_embedding_model",
                        gemini.get("embedding_model", "gemini-embedding-001"),
                    )
                )
                items.append(
                    (
                        "gemini_vision_model",
                        gemini.get("vision_model", "gemini-2.5-flash"),
                    )
                )
                items.append(
                    (
                        "gemini_base_url",
                        gemini.get(
                            "base_url",
                            "https://generativelanguage.googleapis.com/v1beta",
                        ),
                    )
                )
                items.append(
                    (
                        "gemini_imagen_model",
                        gemini.get("imagen_model", "imagen-4.0-generate-001"),
                    )
                )
                items.append(
                    (
                        "gemini_veo_model",
                        gemini.get("veo_model", "veo-3.0-fast-generate-001"),
                    )
                )

            # AI21
            if "ai21" in providers:
                ai21 = providers["ai21"]
                items.append(("ai21_api_key", ai21.get("api_key")))
                items.append(("ai21_model", ai21.get("model", "jamba-large-1.7")))
                items.append(
                    (
                        "ai21_base_url",
                        ai21.get("base_url", "https://api.ai21.com/studio/v1"),
                    )
                )

            # Cerebras
            if "cerebras" in providers:
                cerebras = providers["cerebras"]
                items.append(("cerebras_api_key", cerebras.get("api_key")))
                items.append(
                    (
                        "cerebras_base_url",
                        cerebras.get("base_url", "https://api.cerebras.ai/v1"),
                    )
                )
                items.append(("cerebras_model", cerebras.get("model", "llama-3.3-70b")))

            # Groq
            if "groq" in providers:
                groq = providers["groq"]
                items.append(("groq_api_key", groq.get("api_key")))
                items.append(
                    (
                        "groq_base_url",
                        groq.get("base_url", "https://api.groq.com/openai/v1"),
                    )
                )
                items.append(
                    ("groq_model", groq.get("model", "llama-3.3-70b-versatile"))
                )
                items.append(
                    (
                        "groq_vision_model",
                        groq.get("vision_model", "llama-3.2-11b-vision-preview"),
                    )
                )
                items.append(
                    (
                        "groq_safety_model",
                        groq.get("safety_model", "meta-llama/llama-guard-4-12b"),
                    )
                )
                items.append(
                    (
                        "groq_prompt_guard_model",
                        groq.get(
                            "prompt_guard_model", "meta-llama/llama-prompt-guard-2-86m"
                        ),
                    )
                )
                items.append(
                    (
                        "groq_reasoning_model",
                        groq.get("reasoning_model", "deepseek-r1-distill-llama-70b"),
                    )
                )
                items.append(
                    (
                        "groq_coding_model",
                        groq.get("coding_model", "qwen-2.5-coder-32b"),
                    )
                )
                items.append(
                    (
                        "groq_enable_auto_model_selection",
                        groq.get("enable_auto_model_selection", True),
                    )
                )

            # NVIDIA
            if "nvidia" in providers:
                nvidia = providers["nvidia"]
                items.append(("nvidia_api_key", nvidia.get("api_key")))
                items.append(
                    (
                        "nvidia_base_url",
                        nvidia.get("base_url", "https://integrate.api.nvidia.com/v1"),
                    )
                )
                items.append(
                    (
                        "nvidia_genai_base_url",
                        nvidia.get("genai_base_url", "https://ai.api.nvidia.com/v1"),
                    )
                )
                items.append(("nvidia_nim_base_url", nvidia.get("nim_base_url", "")))
                items.append(
                    (
                        "nvidia_model",
                        nvidia.get("model", "nvidia/llama-3.3-nemotron-super-49b-v1"),
                    )
                )
                items.append(
                    (
                        "nvidia_chat_model",
                        nvidia.get(
                            "chat_model",
                            nvidia.get(
                                "model", "nvidia/llama-3.3-nemotron-super-49b-v1"
                            ),
                        ),
                    )
                )
                items.append(
                    (
                        "nvidia_embedding_model",
                        nvidia.get("embedding_model", "nvidia/nv-embedqa-e5-v5"),
                    )
                )
                items.append(
                    (
                        "nvidia_vision_model",
                        nvidia.get(
                            "vision_model", "meta/llama-3.2-90b-vision-instruct"
                        ),
                    )
                )
                items.append(("nvidia_timeout", nvidia.get("timeout", 120.0)))
                items.append(("nvidia_chat_timeout", nvidia.get("chat_timeout", 120.0)))
                items.append(
                    ("nvidia_embedding_timeout", nvidia.get("embedding_timeout", 60.0))
                )
                items.append(
                    ("nvidia_vision_timeout", nvidia.get("vision_timeout", 180.0))
                )
                items.append(("nvidia_nim_timeout", nvidia.get("nim_timeout", 300.0)))

            # OpenRouter
            if "openrouter" in providers:
                openrouter = providers["openrouter"]
                items.append(("openrouter_api_key", openrouter.get("api_key")))
                items.append(
                    (
                        "openrouter_base_url",
                        openrouter.get("base_url", "https://openrouter.ai/api/v1"),
                    )
                )
                items.append(
                    ("openrouter_model", openrouter.get("model", "openrouter/auto"))
                )
                items.append(("openrouter_site_url", openrouter.get("site_url", "")))
                items.append(
                    ("openrouter_app_name", openrouter.get("app_name", "DurgasAI"))
                )
                items.append(
                    (
                        "openrouter_enable_auto_routing",
                        openrouter.get("enable_auto_routing", True),
                    )
                )
                items.append(
                    (
                        "openrouter_fallback_models",
                        openrouter.get("fallback_models", []),
                    )
                )

            # Fireworks AI
            if "fireworks" in providers:
                fireworks = providers["fireworks"]
                items.append(("fireworks_api_key", fireworks.get("api_key")))
                items.append(
                    (
                        "fireworks_base_url",
                        fireworks.get(
                            "base_url", "https://api.fireworks.ai/inference/v1"
                        ),
                    )
                )
                items.append(
                    (
                        "fireworks_model",
                        fireworks.get(
                            "model", "accounts/fireworks/models/llama-v3-70b-instruct"
                        ),
                    )
                )

            # Deep Infra
            if "deepinfra" in providers:
                deepinfra = providers["deepinfra"]
                items.append(("deepinfra_api_key", deepinfra.get("api_key")))
                items.append(
                    (
                        "deepinfra_base_url",
                        deepinfra.get(
                            "base_url", "https://api.deepinfra.com/v1/openai"
                        ),
                    )
                )
                items.append(
                    (
                        "deepinfra_inference_base_url",
                        deepinfra.get(
                            "inference_base_url", "https://api.deepinfra.com/v1"
                        ),
                    )
                )
                items.append(
                    ("deepinfra_model", deepinfra.get("model", "google/gemma-7b-it"))
                )
                items.append(
                    (
                        "deepinfra_embedding_model",
                        deepinfra.get("embedding_model", "thenlper/gte-large"),
                    )
                )
                items.append(
                    (
                        "deepinfra_image_model",
                        deepinfra.get(
                            "image_model", "black-forest-labs/FLUX-1-schnell"
                        ),
                    )
                )

            # Anyscale
            if "anyscale" in providers:
                anyscale = providers["anyscale"]
                items.append(("anyscale_api_key", anyscale.get("api_key")))
                items.append(
                    (
                        "anyscale_base_url",
                        anyscale.get(
                            "base_url", "https://api.endpoints.anyscale.com/v1"
                        ),
                    )
                )
                items.append(
                    (
                        "anyscale_model",
                        anyscale.get("model", "meta-llama/Llama-3-70b-chat-hf"),
                    )
                )

            # fal.ai
            if "fal" in providers:
                fal = providers["fal"]
                items.append(("fal_api_key", fal.get("api_key")))
                items.append(
                    (
                        "fal_base_url",
                        fal.get("base_url", "https://queue.fal.run/fal-ai"),
                    )
                )
                items.append(("fal_default_timeout", fal.get("default_timeout", 600.0)))
                items.append(("fal_polling_interval", fal.get("polling_interval", 2.0)))
                items.append(
                    ("fal_max_polling_attempts", fal.get("max_polling_attempts", 150))
                )

            # Hyperbolic
            if "hyperbolic" in providers:
                hyperbolic = providers["hyperbolic"]
                items.append(("hyperbolic_api_key", hyperbolic.get("api_key")))
                items.append(
                    (
                        "hyperbolic_base_url",
                        hyperbolic.get("base_url", "https://api.hyperbolic.xyz/v1"),
                    )
                )
                items.append(
                    (
                        "hyperbolic_default_text_model",
                        hyperbolic.get(
                            "default_text_model",
                            "meta-llama/Meta-Llama-3.1-70B-Instruct",
                        ),
                    )
                )
                items.append(
                    (
                        "hyperbolic_default_vision_model",
                        hyperbolic.get(
                            "default_vision_model",
                            "meta-llama/Llama-3.2-90B-Vision-Instruct",
                        ),
                    )
                )
                items.append(
                    (
                        "hyperbolic_default_image_model",
                        hyperbolic.get("default_image_model", "FLUX.1-dev"),
                    )
                )
                items.append(("hyperbolic_timeout", hyperbolic.get("timeout", 120.0)))

            # Cohere
            if "cohere" in providers:
                cohere = providers["cohere"]
                items.append(("cohere_api_key", cohere.get("api_key")))
                items.append(
                    (
                        "cohere_base_url",
                        cohere.get("base_url", "https://api.cohere.ai/v1"),
                    )
                )
                items.append(("cohere_model", cohere.get("model", "command-r-plus")))
                items.append(
                    (
                        "cohere_embed_model",
                        cohere.get("embed_model", "embed-english-v3.0"),
                    )
                )
                items.append(
                    (
                        "cohere_rerank_model",
                        cohere.get("rerank_model", "rerank-english-v3.0"),
                    )
                )
                items.append(
                    (
                        "cohere_classify_model",
                        cohere.get("classify_model", "embed-english-v3.0"),
                    )
                )

    # Handle embeddings
    if "embeddings" in data:
        embeddings = data["embeddings"]
        items.append(("embedding_provider", embeddings.get("provider", "local")))
        items.append(("embedding_model", embeddings.get("model", "all-MiniLM-L6-v2")))

    # Handle database
    if "database" in data:
        database = data["database"]
        items.append(
            (
                "database_url",
                database.get("url", "sqlite+aiosqlite:///./data/durgasai.db"),
            )
        )
        items.append(
            ("chroma_persist_dir", database.get("chroma_persist_dir", "./data/chroma"))
        )
        items.append(
            (
                "chroma_collection_name",
                database.get("chroma_collection_name", "durgasai_pages"),
            )
        )

    # Handle redis
    if "redis" in data:
        redis = data["redis"]
        items.append(("redis_url", redis.get("url", "redis://localhost:6379")))
        items.append(("use_redis", redis.get("use_redis", False)))

    # Handle security
    if "security" in data:
        security = data["security"]
        items.append(
            (
                "jwt_secret_key",
                security.get(
                    "jwt_secret_key", "your-super-secret-jwt-key-change-in-production"
                ),
            )
        )
        items.append(("jwt_algorithm", security.get("jwt_algorithm", "HS256")))
        items.append(
            (
                "jwt_access_token_expire_minutes",
                security.get("jwt_access_token_expire_minutes", 30),
            )
        )
        items.append(("api_key", security.get("api_key", "your-api-key-for-extension")))

    # Handle rate limiting
    if "rate_limiting" in data:
        rate_limiting = data["rate_limiting"]
        items.append(("rate_limit_per_minute", rate_limiting.get("per_minute", 100)))
        items.append(("rate_limit_burst", rate_limiting.get("burst", 20)))

    # Handle CORS
    if "cors" in data:
        cors = data["cors"]
        items.append(
            (
                "cors_origins",
                cors.get("origins", "chrome-extension://,http://localhost:3000"),
            )
        )

    # Handle logging
    if "logging" in data:
        logging = data["logging"]
        items.append(("log_level", logging.get("level", "INFO")))
        items.append(("log_format", logging.get("format", "json")))

    # Handle websocket
    if "websocket" in data:
        ws = data["websocket"]
        items.append(("ws_max_connections", ws.get("max_connections", 1000)))
        items.append(("ws_heartbeat_interval", ws.get("heartbeat_interval", 30)))
        items.append(("ws_heartbeat_timeout", ws.get("heartbeat_timeout", 300)))
        items.append(("ws_message_timeout", ws.get("message_timeout", 60)))
        items.append(("ws_enable_cleanup", ws.get("enable_cleanup", True)))
        items.append(("ws_cleanup_interval", ws.get("cleanup_interval", 60)))

    # Handle streaming
    if "streaming" in data:
        streaming = data["streaming"]
        items.append(("streaming_chunk_size", streaming.get("chunk_size", 50)))
        items.append(("streaming_buffer_time", streaming.get("buffer_time", 0.1)))
        items.append(
            ("streaming_max_buffer_size", streaming.get("max_buffer_size", 1000))
        )
        items.append(("streaming_timeout", streaming.get("timeout", 60)))
        items.append(("streaming_max_retries", streaming.get("max_retries", 3)))
        items.append(("streaming_retry_delay", streaming.get("retry_delay", 1.0)))
        items.append(
            (
                "streaming_enable_exponential_backoff",
                streaming.get("enable_exponential_backoff", True),
            )
        )

    # Handle RAG
    if "rag" in data:
        rag = data["rag"]
        items.append(("rag_chunk_size", rag.get("chunk_size", 1000)))
        items.append(("rag_chunk_overlap", rag.get("chunk_overlap", 200)))
        items.append(("rag_max_chunks", rag.get("max_chunks", 10)))
        items.append(("rag_similarity_threshold", rag.get("similarity_threshold", 0.7)))
        items.append(
            ("rag_enable_hybrid_search", rag.get("enable_hybrid_search", True))
        )
        items.append(("rag_enable_reranking", rag.get("enable_reranking", False)))
        items.append(("rag_rerank_top_k", rag.get("rerank_top_k", 5)))
        items.append(("rag_context_max_length", rag.get("context_max_length", 4000)))

    # Handle PostgreSQL
    if "postgresql" in data:
        pg = data["postgresql"]
        items.append(("postgresql_url", pg.get("url")))
        items.append(("postgresql_pool_size", pg.get("pool_size", 20)))
        items.append(("postgresql_max_overflow", pg.get("max_overflow", 10)))
        items.append(("postgresql_pool_recycle", pg.get("pool_recycle", 3600)))

    # Handle council
    if "council" in data:
        council = data["council"]
        items.append(("council_min_models", council.get("min_models", 3)))
        items.append(("council_max_models", council.get("max_models", 5)))
        items.append(
            (
                "council_enable_auto_selection",
                council.get("enable_auto_selection", True),
            )
        )
        items.append(("council_timeout_seconds", council.get("timeout_seconds", 120)))
        items.append(
            ("council_preferred_chairman", council.get("preferred_chairman", "gemini"))
        )

    # Handle Deepgram
    if "deepgram" in data:
        deepgram = data["deepgram"]
        items.append(("deepgram_api_key", deepgram.get("api_key", "")))
        items.append(
            (
                "deepgram_base_url",
                deepgram.get("base_url", "https://api.deepgram.com/v1"),
            )
        )
        items.append(
            ("deepgram_default_stt_model", deepgram.get("default_stt_model", "nova-2"))
        )
        items.append(
            (
                "deepgram_default_tts_model",
                deepgram.get("default_tts_model", "aura-asteria-en"),
            )
        )
        items.append(("deepgram_timeout", deepgram.get("timeout", 120.0)))

    # Handle ElevenLabs
    if "elevenlabs" in data:
        elevenlabs = data["elevenlabs"]
        items.append(("elevenlabs_api_key", elevenlabs.get("api_key", "")))
        items.append(
            (
                "elevenlabs_base_url",
                elevenlabs.get("base_url", "https://api.elevenlabs.io/v1"),
            )
        )
        items.append(
            (
                "elevenlabs_default_voice_id",
                elevenlabs.get("default_voice_id", "pMsXgVXv3BLzUgSXRplE"),
            )
        )
        items.append(
            (
                "elevenlabs_default_model_id",
                elevenlabs.get("default_model_id", "eleven_multilingual_v2"),
            )
        )
        items.append(("elevenlabs_timeout", elevenlabs.get("timeout", 120.0)))
        items.append(("elevenlabs_cache_ttl", elevenlabs.get("cache_ttl", 3600)))

    # Handle Supabase
    if "supabase" in data:
        supabase = data["supabase"]
        items.append(("supabase_url", supabase.get("url", "")))
        items.append(("supabase_anon_key", supabase.get("anon_key", "")))
        items.append(("supabase_service_role_key", supabase.get("service_role_key")))
        items.append(("supabase_jwt_secret", supabase.get("jwt_secret")))
        if "storage_buckets" in supabase:
            buckets = supabase["storage_buckets"]
            items.append(
                ("supabase_bucket_uploads", buckets.get("uploads", "user-uploads"))
            )
            items.append(
                ("supabase_bucket_avatars", buckets.get("avatars", "user-avatars"))
            )
            items.append(
                ("supabase_bucket_documents", buckets.get("documents", "rag-documents"))
            )
        items.append(("supabase_db_url", supabase.get("db_url")))
        items.append(("supabase_studio_url", supabase.get("studio_url")))
        items.append(
            ("supabase_enable_realtime", supabase.get("enable_realtime", True))
        )

    return dict(items)


def apply_environment_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Overlay OS environment variables onto flattened config (Docker / CI).
    Values from config.json remain defaults when env vars are unset or empty.
    """
    mapping = [
        ("DATABASE_URL", "database_url"),
        ("POSTGRESQL_URL", "postgresql_url"),
        ("SUPABASE_URL", "supabase_url"),
        ("SUPABASE_ANON_KEY", "supabase_anon_key"),
        ("SUPABASE_SERVICE_ROLE_KEY", "supabase_service_role_key"),
        ("SUPABASE_JWT_SECRET", "supabase_jwt_secret"),
        ("SUPABASE_DB_URL", "supabase_db_url"),
        ("SUPABASE_STUDIO_URL", "supabase_studio_url"),
    ]
    out = dict(config)
    for env_key, cfg_key in mapping:
        val = os.getenv(env_key)
        if val is not None and str(val).strip() != "":
            out[cfg_key] = val
    er = os.getenv("SUPABASE_ENABLE_REALTIME")
    if er is not None and str(er).strip() != "":
        out["supabase_enable_realtime"] = er.strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    return out


class Settings(BaseModel):
    """Application settings loaded from config.json"""

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    environment: str = "development"

    # AI Provider Settings
    default_llm_provider: str = "ollama"
    default_model: str = "llama3"

    # HuggingFace Configuration
    huggingface_api_key: Optional[str] = None
    huggingface_model: str = "mistralai/Mistral-7B-Instruct-v0.2"
    huggingface_inference_provider: str = (
        "hf"  # hf, cerebras, groq, fireworks, together, etc.
    )

    # HuggingFace Router URLs
    hf_router_base_url: str = "https://router.huggingface.co"
    hf_inference_base_url: str = "https://api-inference.huggingface.co"

    # Multimodal Model Settings
    hf_text_to_image_model: str = "black-forest-labs/FLUX.1-schnell"
    hf_image_to_text_model: str = "Salesforce/blip-image-captioning-large"
    hf_speech_to_text_model: str = "openai/whisper-large-v3-turbo"
    hf_text_to_speech_model: str = "facebook/fastspeech2-en-ljspeech"
    hf_text_to_audio_model: str = "facebook/musicgen-small"

    # NLP Task Models
    hf_summarization_model: str = "facebook/bart-large-cnn"
    hf_embedding_model: str = "Qwen/Qwen3-Embedding-8B"

    # Object Detection
    hf_object_detection_model: str = "facebook/detr-resnet-50"

    # Gradio Spaces URLs
    hf_spaces_naive_rag: str = "https://bstraehle-rag.hf.space"
    hf_spaces_advanced_rag: str = "https://bstraehle-advanced-rag.hf.space"
    hf_spaces_agentic_crewai: str = ""
    hf_spaces_agentic_langgraph: str = ""
    hf_spaces_agentic_openai: str = ""

    # Gemini API Configuration
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_vision_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # AI21 Labs Configuration
    ai21_api_key: Optional[str] = None
    ai21_model: str = "jamba-large-1.7"
    ai21_base_url: str = "https://api.ai21.com/studio/v1"

    # Imagen/Veo Configuration
    gemini_imagen_model: str = "imagen-4.0-generate-001"
    gemini_veo_model: str = "veo-3.0-fast-generate-001"

    # Cerebras API Configuration
    cerebras_api_key: Optional[str] = None
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    cerebras_model: str = "llama-3.3-70b"

    # Groq Configuration
    groq_api_key: Optional[str] = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    groq_vision_model: str = "llama-3.2-11b-vision-preview"
    groq_safety_model: str = "meta-llama/llama-guard-4-12b"
    groq_prompt_guard_model: str = "meta-llama/llama-prompt-guard-2-86m"
    groq_reasoning_model: str = "deepseek-r1-distill-llama-70b"
    groq_coding_model: str = "qwen-2.5-coder-32b"
    groq_enable_auto_model_selection: bool = True

    # NVIDIA AI Configuration
    nvidia_api_key: Optional[str] = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_genai_base_url: str = "https://ai.api.nvidia.com/v1"
    nvidia_nim_base_url: str = ""
    nvidia_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1"
    nvidia_chat_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1"
    nvidia_embedding_model: str = "nvidia/nv-embedqa-e5-v5"
    nvidia_vision_model: str = "meta/llama-3.2-90b-vision-instruct"
    nvidia_timeout: float = 120.0
    nvidia_chat_timeout: float = 120.0
    nvidia_embedding_timeout: float = 60.0
    nvidia_vision_timeout: float = 180.0
    nvidia_nim_timeout: float = 300.0

    # OpenRouter Configuration
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openrouter/auto"
    openrouter_site_url: str = ""
    openrouter_app_name: str = "DurgasAI"
    openrouter_enable_auto_routing: bool = True
    openrouter_fallback_models: List[str] = []

    # Fireworks AI Configuration
    fireworks_api_key: Optional[str] = None
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"
    fireworks_model: str = "accounts/fireworks/models/llama-v3-70b-instruct"

    # Deep Infra Configuration
    deepinfra_api_key: Optional[str] = None
    deepinfra_base_url: str = "https://api.deepinfra.com/v1/openai"
    deepinfra_inference_base_url: str = "https://api.deepinfra.com/v1"
    deepinfra_model: str = "google/gemma-7b-it"
    deepinfra_embedding_model: str = "thenlper/gte-large"
    deepinfra_image_model: str = "black-forest-labs/FLUX-1-schnell"

    # Anyscale Configuration
    anyscale_api_key: Optional[str] = None
    anyscale_base_url: str = "https://api.endpoints.anyscale.com/v1"
    anyscale_model: str = "meta-llama/Llama-3-70b-chat-hf"

    # fal.ai Configuration
    fal_api_key: Optional[str] = None
    fal_base_url: str = "https://queue.fal.run/fal-ai"
    fal_default_timeout: float = 600.0
    fal_polling_interval: float = 2.0
    fal_max_polling_attempts: int = 150

    # Hyperbolic Configuration
    hyperbolic_api_key: Optional[str] = None
    hyperbolic_base_url: str = "https://api.hyperbolic.xyz/v1"
    hyperbolic_default_text_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"
    hyperbolic_default_vision_model: str = "meta-llama/Llama-3.2-90B-Vision-Instruct"
    hyperbolic_default_image_model: str = "FLUX.1-dev"
    hyperbolic_timeout: float = 120.0

    # Reka AI Configuration
    reka_api_key: Optional[str] = None
    reka_base_url: str = "https://api.reka.ai/v1"
    reka_model: str = "reka-flash-3"
    reka_timeout: float = 120.0

    # Cohere Configuration
    cohere_api_key: Optional[str] = None
    cohere_base_url: str = "https://api.cohere.ai/v1"
    cohere_model: str = "command-r-plus"
    cohere_embed_model: str = "embed-english-v3.0"
    cohere_rerank_model: str = "rerank-english-v3.0"
    cohere_classify_model: str = "embed-english-v3.0"

    # Embeddings Configuration
    embedding_provider: str = "local"
    embedding_model: str = "all-MiniLM-L6-v2"

    # ChromaDB Configuration
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "durgasai_pages"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/durgasai.db"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    use_redis: bool = False

    # Security
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    api_key: str = "your-api-key-for-extension"

    # Rate Limiting
    rate_limit_per_minute: int = 100
    rate_limit_burst: int = 20

    # CORS
    cors_origins: str = "chrome-extension://,http://localhost:3000"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434/api"
    ollama_cloud_url: str = "https://ollama.com/api"
    ollama_api_key: Optional[str] = None
    ollama_mode: str = "localhost"  # "localhost" or "cloud"
    ollama_model: str = "llama3"

    # Council Configuration
    council_min_models: int = 3
    council_max_models: int = 5
    council_enable_auto_selection: bool = True
    council_timeout_seconds: int = 120
    council_preferred_chairman: str = "gemini"  # or "groq" for speed
    # Council v2 (anti-hallucination): open | grounded | verified
    council_default_policy: str = "open"
    council_enable_web_verifier: bool = False
    council_grounded_temperature: float = 0.2
    council_open_temperature: float = 0.7
    council_ranking_temperature: float = 0.4
    council_chairman_open_temp: float = 0.7
    council_chairman_grounded_temp: float = 0.3
    council_rag_retrieve_k: int = 12
    council_rag_mmr_k: int = 6
    council_abstain_coverage_floor: float = 0.15  # below this in verified -> abstain
    council_web_search_url: str = "https://html.duckduckgo.com/html"  # POST q=
    council_web_search_timeout: float = 20.0

    # Claude Code agent (workspace tools + harness)
    claude_code_workspace_root: Optional[str] = None  # None = process cwd
    claude_code_bash_read_only: bool = True
    claude_code_bash_timeout_seconds: int = 60
    claude_code_max_file_bytes: int = 512_000

    # Deepgram Configuration
    deepgram_api_key: Optional[str] = None
    deepgram_base_url: str = "https://api.deepgram.com/v1"
    deepgram_default_stt_model: str = "nova-2"
    deepgram_default_tts_model: str = "aura-asteria-en"
    deepgram_timeout: float = 120.0

    # ElevenLabs Configuration
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"
    elevenlabs_default_voice_id: str = "pMsXgVXv3BLzUgSXRplE"  # Rachel
    elevenlabs_default_model_id: str = "eleven_multilingual_v2"
    elevenlabs_timeout: float = 120.0
    elevenlabs_cache_ttl: int = 3600  # 1 hour cache

    # Supabase Configuration
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_jwt_secret: Optional[str] = None
    supabase_db_url: Optional[str] = None
    supabase_studio_url: Optional[str] = None
    supabase_enable_realtime: bool = True
    supabase_bucket_uploads: str = "user-uploads"
    supabase_bucket_avatars: str = "user-avatars"
    supabase_bucket_documents: str = "rag-documents"

    # AWS S3 (optional; S3StorageAdapter and direct tooling)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_s3_bucket: Optional[str] = None
    aws_region: str = "us-east-1"

    # WebSocket Configuration
    ws_max_connections: int = 1000
    ws_heartbeat_interval: int = 30  # seconds
    ws_heartbeat_timeout: int = 300  # seconds (5 minutes)
    ws_message_timeout: int = 60  # seconds
    ws_enable_cleanup: bool = True
    ws_cleanup_interval: int = 60  # seconds

    # Streaming Configuration
    streaming_chunk_size: int = 50  # characters
    streaming_buffer_time: float = 0.1  # seconds
    streaming_max_buffer_size: int = 1000  # characters
    streaming_timeout: int = 60  # seconds
    streaming_max_retries: int = 3
    streaming_retry_delay: float = 1.0  # seconds
    streaming_enable_exponential_backoff: bool = True

    # RAG Configuration
    rag_chunk_size: int = 1000  # characters per chunk
    rag_chunk_overlap: int = 200  # characters overlap between chunks
    rag_max_chunks: int = 10  # maximum chunks to retrieve
    rag_similarity_threshold: float = 0.7  # minimum similarity score
    rag_enable_hybrid_search: bool = True  # vector + keyword search
    rag_enable_reranking: bool = False  # requires Cohere API
    rag_rerank_top_k: int = 5  # top K results to rerank
    rag_context_max_length: int = 4000  # max context length in characters

    # PostgreSQL Configuration (for production)
    postgresql_url: Optional[str] = (
        None  # e.g., "postgresql+asyncpg://user:pass@localhost/db"
    )
    postgresql_pool_size: int = 20
    postgresql_max_overflow: int = 10
    postgresql_pool_recycle: int = 3600
    database_prefer_postgresql_in_production: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() == "production"

    @property
    def effective_database_url(self) -> str:
        """
        Return the database URL to use at runtime.

        In production, prefer postgresql_url when available.
        """
        if (
            self.database_prefer_postgresql_in_production
            and self.is_production
            and self.postgresql_url
        ):
            return self.postgresql_url
        return self.database_url


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance loaded from config.json"""
    # Determine config file path
    config_dir = Path(__file__).parent.parent / "config"

    # Check for environment-specific config first
    environment = os.getenv("ENVIRONMENT", "development").lower()
    env_config_path = config_dir / f"config.{environment}.json"
    default_config_path = config_dir / "config.json"

    # Use environment-specific config if it exists, otherwise use default
    config_path = env_config_path if env_config_path.exists() else default_config_path

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}. "
            f"Please copy config/config.example.json to config/config.json and configure it."
        )

    # Load and parse JSON config
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    # Flatten nested structure to match Settings field names
    flat_config = apply_environment_overrides(flatten_config(config_data))

    return Settings(**flat_config)


# Global settings instance
settings = get_settings()
