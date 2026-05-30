"""
Configuration management for DurgasAI Backend
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load ai.backend/.env into the process environment before Settings() (uvicorn does not load .env by default).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DOTENV_PATH = _BACKEND_ROOT / ".env"
try:
    from dotenv import load_dotenv

    if _DOTENV_PATH.is_file():
        load_dotenv(_DOTENV_PATH, override=False)
except ImportError:
    pass

from app.config_runtime_overlay import SettingsOverlayProxy  # noqa: E402


class Settings(BaseSettings):
    """Application settings from environment and optional .env file."""

    model_config = SettingsConfigDict(
        env_file=_DOTENV_PATH if _DOTENV_PATH.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

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

    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # DeepSeek Configuration
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Mistral Configuration
    mistral_api_key: Optional[str] = None
    mistral_base_url: str = "https://api.mistral.ai/v1"
    mistral_model: str = "mistral-small-latest"

    # Together AI Configuration
    together_api_key: Optional[str] = None
    together_base_url: str = "https://api.together.xyz/v1"
    together_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

    # Perplexity Configuration
    perplexity_api_key: Optional[str] = None
    perplexity_base_url: str = "https://api.perplexity.ai"
    perplexity_model: str = "sonar"

    # xAI Configuration
    xai_api_key: Optional[str] = None
    xai_base_url: str = "https://api.x.ai/v1"
    xai_model: str = "grok-2-latest"

    # SambaNova Configuration
    sambanova_api_key: Optional[str] = None
    sambanova_base_url: str = "https://api.sambanova.ai/v1"
    sambanova_model: str = "Meta-Llama-3.1-70B-Instruct"

    # GitHub Models Configuration
    github_ai_api_key: Optional[str] = None
    github_ai_base_url: str = "https://models.inference.ai.azure.com"
    github_ai_model: str = "gpt-4o"

    # Docker Model Runner (local OpenAI-compatible)
    docker_model_runner_api_key: Optional[str] = None
    docker_model_runner_base_url: str = "http://localhost:12434/v1"
    docker_model_runner_model: str = "llama3.2"

    # Novita / Nebius / kluster / Lamini / Lepton
    novita_api_key: Optional[str] = None
    novita_base_url: str = "https://api.novita.ai/v3/openai"
    novita_model: str = "meta-llama/llama-3-70b-instruct"

    nebius_api_key: Optional[str] = None
    nebius_base_url: str = "https://api.studio.nebius.ai/v1"
    nebius_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"

    kluster_api_key: Optional[str] = None
    kluster_base_url: str = "https://api.kluster.ai/v1"
    kluster_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"

    lamini_api_key: Optional[str] = None
    lamini_base_url: str = "https://api.lamini.ai/v1"
    lamini_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"

    lepton_api_key: Optional[str] = None
    lepton_base_url: str = "https://api.lepton.ai/v1"
    lepton_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"

    # Google Vertex AI (in addition to Gemini API key)
    vertex_project_id: Optional[str] = None
    vertex_location: str = "us-central1"
    vertex_model: str = "gemini-2.0-flash"

    # Amazon Bedrock
    bedrock_region: str = "us-east-1"
    bedrock_model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Alibaba DashScope
    dashscope_api_key: Optional[str] = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen-plus"

    # IBM watsonx
    watsonx_api_key: Optional[str] = None
    watsonx_base_url: str = "https://us-south.ml.cloud.ibm.com"
    watsonx_project_id: Optional[str] = None
    watsonx_model: str = "ibm/granite-3-8b-instruct"

    # Stability AI
    stability_api_key: Optional[str] = None
    stability_base_url: str = "https://api.stability.ai/v2beta"

    # Replicate
    replicate_api_key: Optional[str] = None
    replicate_base_url: str = "https://api.replicate.com/v1"

    # Eden AI aggregator
    eden_api_key: Optional[str] = None
    eden_base_url: str = "https://api.edenai.run/v2"

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
    # Skip Chroma/RAG init in lifespan (Docker/EC2); services lazy-init on first use.
    skip_heavy_startup_init: bool = False

    # ChromaDB Configuration
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "durgasai_pages"

    # Runtime AI provider overrides (JSON); see SettingsOverlayProxy
    ai_provider_overrides_path: str = "./data/ai_provider_overrides.json"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/durgasai.db"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    use_redis: bool = False

    # Security
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    api_key: str = "your-api-key-for-extension"

    # Rate Limiting
    rate_limit_per_minute: int = (
        100  # legacy default; HTTP limiter uses *_anonymous below
    )
    rate_limit_burst: int = 20
    rate_limit_per_minute_anonymous: int = 60
    rate_limit_per_minute_authenticated: int = 200
    rate_limit_per_minute_api_key: int = 500

    # Kafka (optional; producer no-ops when unset)
    kafka_bootstrap_servers: Optional[str] = None

    # CORS
    cors_origins: str = "chrome-extension://,http://localhost:3000"

    # Weather (Open-Meteo; used by DurgasOS desktop widget when coords omitted)
    weather_default_latitude: float = 40.7128
    weather_default_longitude: float = -74.006
    weather_http_timeout_seconds: float = 12.0

    # Session cookies (JWT access/refresh for durgasos; shared with GraphQL when using cookies)
    session_cookie_domain: Optional[str] = None
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434/api"
    ollama_cloud_url: str = "https://ollama.com/api"
    ollama_api_key: Optional[str] = None
    ollama_mode: str = "localhost"  # "localhost" or "cloud" (not a hostname/IP)
    ollama_model: str = "llama3"

    @field_validator("ollama_mode", mode="before")
    @classmethod
    def _normalize_ollama_mode(cls, v: object) -> str:
        s = str(v or "localhost").strip().lower()
        if s in ("localhost", "cloud"):
            return s
        return "localhost"

    # Max time to wait for Ollama /api/chat (non-streaming) to finish reading the body.
    # Large prompts (e.g. resume + job description) on remote CPUs often exceed 120s; see error.txt ReadTimeout.
    ollama_completion_timeout_seconds: float = 600.0

    # Gemma Configuration
    gemma_mode: str = "simulated"  # "simulated", "local", "ollama", "api"
    gemma_model: str = "google/gemma-3-270m-it"
    gemma_checkpoint_path: Optional[str] = None

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

    # Local filesystem storage (replaces Supabase Storage)
    storage_root: str = "./data/storage"
    storage_url_prefix: str = "/files"
    storage_signed_url_secret: str = ""
    storage_signed_url_ttl: int = 3600
    storage_bucket_uploads: str = "user-uploads"
    storage_bucket_avatars: str = "user-avatars"
    storage_bucket_documents: str = "rag-documents"

    # Socket.IO (replaces Supabase Realtime for app-level push)
    socketio_cors_origins: str = "*"  # comma-separated or single "*"
    socketio_mount_path: str = "/realtime"

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
    streaming_timeout: int = (
        120  # seconds — max idle gap between chunks after first chunk
    )
    streaming_first_chunk_timeout: int = (
        600  # seconds — TTFT / cold CPU Ollama; see error.txt idle @ 120s with no first token
    )
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
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @property
    def socketio_cors_origins_list(self) -> Union[List[str], str]:
        """CORS origins for Socket.IO; '*' means allow all."""
        raw = (self.socketio_cors_origins or "*").strip()
        if raw == "*":
            return "*"
        return [p.strip() for p in raw.split(",") if p.strip()]

    @property
    def storage_hmac_secret(self) -> str:
        """Secret for signed file URLs; defaults to JWT secret."""
        return (self.storage_signed_url_secret or "").strip() or self.jwt_secret_key

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() == "production"

    @property
    def is_test(self) -> bool:
        """Check if running under pytest / CI test profile."""
        return self.environment.lower() == "test"

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
def _base_settings_singleton() -> Settings:
    """Underlying pydantic Settings (env + .env); wrapped by runtime overlay."""
    return Settings()


def clear_base_settings_cache() -> None:
    """Clear cached pydantic Settings (e.g. after changing process env in scripts)."""
    _base_settings_singleton.cache_clear()


def get_settings():
    """Process settings including runtime AI provider JSON overrides."""
    return settings


# Single stable object so imports of `settings` see overlay updates.
settings: SettingsOverlayProxy = SettingsOverlayProxy(_base_settings_singleton())
