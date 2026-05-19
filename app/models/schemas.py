"""
Pydantic schemas for API requests and responses
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.utils.helpers import utc_now


# ===================
# Enums
# ===================


class CouncilPolicy(str, Enum):
    """
    Council v2 policy (mirrors app.services.council.policy.CouncilPolicy string values).
    Use options.council_policy on agents.analyze (council) or council.run params.
    """

    OPEN = "open"
    GROUNDED = "grounded"
    VERIFIED = "verified"


class AgentType(str, Enum):
    """Available agent types"""

    PAGE_ANALYZER = "page_analyzer"
    CONTENT_EXTRACTOR = "content_extractor"
    SEO = "seo"
    IMAGE_ANALYZER = "image_analyzer"
    RESEARCH = "research"
    COUNCIL = "council"
    WEBSITE_SCRAPER = "website_scraper"


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    GEMINI = "gemini"
    AI21 = "ai21"
    CEREBRAS = "cerebras"
    GROQ = "groq"
    NVIDIA = "nvidia"
    OPENROUTER = "openrouter"
    FIREWORKS = "fireworks"
    DEEPINFRA = "deepinfra"
    ANYSCALE = "anyscale"
    COHERE = "cohere"
    REKA = "reka"


class MessageRole(str, Enum):
    """Chat message roles"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ===================
# Chat Schemas
# ===================


class ChatMessage(BaseModel):
    """Single chat message"""

    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request for chat completion"""

    message: str = Field(..., min_length=1, max_length=10000)
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    context: Optional[str] = Field(None, max_length=50000)
    provider: Optional[LLMProvider] = None
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    stream: bool = False


class ChatResponse(BaseModel):
    """Response from chat completion"""

    message: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)


# ===================
# Agent Schemas
# ===================


class PageData(BaseModel):
    """Page data from extension"""

    url: str
    title: Optional[str] = None
    domain: Optional[str] = None
    protocol: Optional[str] = None
    pathname: Optional[str] = None
    html: Optional[str] = Field(None, max_length=5000000)  # 5MB max
    body_html: Optional[str] = Field(None, max_length=5000000)
    head_html: Optional[str] = Field(None, max_length=500000)
    meta: Optional[List[Dict[str, str]]] = None
    structure: Optional[Dict[str, Any]] = None
    images: Optional[List[Dict[str, Any]]] = None
    videos: Optional[List[Dict[str, Any]]] = None
    semantic: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class AgentRequest(BaseModel):
    """Request for agent analysis"""

    agent_type: AgentType
    page_data: PageData
    query: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Response from agent analysis"""

    agent_type: str
    analysis: Dict[str, Any]
    summary: str
    recommendations: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=utc_now)


# ===================
# RAG Schemas
# ===================


class RAGIngestRequest(BaseModel):
    """Request to ingest page into vector store"""

    page_data: PageData
    metadata: Optional[Dict[str, Any]] = None
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)


class RAGIngestResponse(BaseModel):
    """Response from RAG ingestion"""

    success: bool
    document_id: str
    chunks_created: int
    message: str


class RAGSearchRequest(BaseModel):
    """Request to search vector store"""

    query: str = Field(..., min_length=1, max_length=1000)
    k: int = Field(default=5, ge=1, le=20)
    filter: Optional[Dict[str, Any]] = None
    include_metadata: bool = True


class RAGSearchResult(BaseModel):
    """Single search result"""

    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class RAGSearchResponse(BaseModel):
    """Response from RAG search"""

    results: List[RAGSearchResult]
    total_results: int
    query: str


# ===================
# Auth Schemas
# ===================


class TokenRequest(BaseModel):
    """Request for authentication token"""

    api_key: str


class TokenResponse(BaseModel):
    """Response with authentication token"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """User information from token"""

    sub: str
    exp: datetime


# ===================
# Health Schemas
# ===================


class ServiceStatus(BaseModel):
    """Status of a service"""

    name: str
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    environment: str
    services: List[ServiceStatus]
    timestamp: datetime = Field(default_factory=utc_now)


# ===================
# WebSocket Schemas
# ===================


class WSMessage(BaseModel):
    """WebSocket message"""

    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=utc_now)


class WSChatMessage(BaseModel):
    """WebSocket chat message"""

    message: str
    context: Optional[str] = None
    conversation_id: Optional[str] = None


# ===================
# Analysis Schemas
# ===================


class SEOAnalysis(BaseModel):
    """SEO analysis results"""

    title_analysis: Dict[str, Any]
    meta_analysis: Dict[str, Any]
    heading_structure: Dict[str, Any]
    keyword_density: Dict[str, float]
    issues: List[str]
    score: float


class ContentAnalysis(BaseModel):
    """Content analysis results"""

    word_count: int
    reading_time_minutes: float
    readability_score: float
    topics: List[str]
    entities: List[Dict[str, str]]
    sentiment: Dict[str, float]


class ImageAnalysis(BaseModel):
    """Image analysis results"""

    total_images: int
    images_with_alt: int
    images_without_alt: int
    large_images: List[Dict[str, Any]]
    optimization_suggestions: List[str]


# ===================
# HuggingFace API Schemas
# ===================


class ChatCompletionMessage(BaseModel):
    """Chat completion message"""

    role: str
    content: str


class ChatCompletionChoice(BaseModel):
    """Chat completion choice"""

    index: int
    message: ChatCompletionMessage
    finish_reason: Optional[str] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionUsage(BaseModel):
    """Token usage information"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[ChatCompletionUsage] = None
    system_fingerprint: Optional[str] = None


class EmbeddingResponse(BaseModel):
    """Embedding response"""

    embedding: List[float]
    model: str
    usage: Optional[Dict[str, int]] = None


class TextToImageResponse(BaseModel):
    """Text-to-image response"""

    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    model: str
    prompt: str


class ImageToTextResponse(BaseModel):
    """Image-to-text response"""

    text: str
    model: str
    confidence: Optional[float] = None


class SpeechToTextResponse(BaseModel):
    """Speech-to-text response"""

    text: str
    model: str
    language: Optional[str] = None
    duration: Optional[float] = None


class TextToSpeechResponse(BaseModel):
    """Text-to-speech response"""

    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    model: str
    text: str


class TextToAudioResponse(BaseModel):
    """Text-to-audio (music) response"""

    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    model: str
    prompt: str


# ===================
# Object Detection Schemas
# ===================


class ObjectDetectionRequest(BaseModel):
    """Object detection request"""

    image_url: Optional[str] = Field(
        None, description="URL of the image to detect objects in"
    )
    image_base64: Optional[str] = Field(None, description="Base64-encoded image")
    model: Optional[str] = Field(None, description="Model to use (overrides default)")
    min_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum confidence score"
    )


class BoundingBox(BaseModel):
    """Bounding box coordinates"""

    xmin: int
    ymin: int
    xmax: int
    ymax: int


class DetectedObject(BaseModel):
    """Detected object information"""

    label: str
    score: float
    box: BoundingBox


class ObjectDetectionResponse(BaseModel):
    """Object detection response"""

    detections: List[DetectedObject]
    model: str
    count: int


# ===================
# Gradio Spaces Schemas
# ===================


class GradioSpacesRequest(BaseModel):
    """Gradio Spaces request"""

    api_key: Optional[str] = Field(
        None, description="API key (for OpenAI-based spaces)"
    )
    question: str = Field(..., min_length=1, description="Question or task")
    framework: Optional[str] = Field(
        default="LangChain", description="Framework to use"
    )


class GradioSpacesResponse(BaseModel):
    """Gradio Spaces initial response"""

    event_id: str
    status: str = "processing"
    message: Optional[str] = None


class GradioSpacesResult(BaseModel):
    """Gradio Spaces result"""

    result: Any
    status: str = "completed"
    event_id: Optional[str] = None


class RAGRequest(BaseModel):
    """RAG request"""

    api_key: Optional[str] = Field(
        None, description="API key (for OpenAI-based spaces)"
    )
    question: str = Field(..., min_length=1, description="Question to answer")
    framework: Optional[str] = Field(
        default="LangChain", description="Framework to use (for naive RAG)"
    )
    num_results: Optional[int] = Field(
        default=2, ge=1, le=10, description="Number of results (for advanced RAG)"
    )
    rerank: Optional[int] = Field(
        default=1, ge=0, description="Reranking parameter (for advanced RAG)"
    )


class AgenticAIRequest(BaseModel):
    """Agentic AI request"""

    api_key: Optional[str] = Field(
        None, description="API key (required for OpenAI-based spaces)"
    )
    question: str = Field(..., min_length=1, description="Research question or task")
    agent_type: Optional[str] = Field(
        default="crewai", description="Agent type: crewai, langgraph, or openai"
    )


class SummarizationResponse(BaseModel):
    """Summarization response"""

    summary: str
    model: str
    original_length: Optional[int] = None
    summary_length: Optional[int] = None


# ===================
# Multimodal Request Schemas
# ===================


class TextToImageRequest(BaseModel):
    """Text-to-image request"""

    prompt: str = Field(..., min_length=1, max_length=1000)
    model: Optional[str] = None
    negative_prompt: Optional[str] = None
    num_inference_steps: int = Field(default=50, ge=1, le=100)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)


class ImageToTextRequest(BaseModel):
    """Image-to-text request"""

    image: str = Field(..., description="Image URL or base64-encoded image")
    model: Optional[str] = None
    prompt: Optional[str] = Field(
        None, description="Optional prompt/question about the image"
    )


class SpeechToTextRequest(BaseModel):
    """Speech-to-text request"""

    audio: str = Field(..., description="Audio URL, base64-encoded audio, or file path")
    model: Optional[str] = None
    language: Optional[str] = None
    return_timestamps: bool = False


class TextToSpeechRequest(BaseModel):
    """Text-to-speech request"""

    text: str = Field(..., min_length=1, max_length=5000)
    model: Optional[str] = None
    provider: Optional[str] = Field(
        None, description="TTS provider: huggingface, deepgram, or elevenlabs"
    )
    voice_id: Optional[str] = Field(None, description="Voice ID (for ElevenLabs)")
    voice_settings: Optional[Dict[str, Any]] = Field(
        None, description="Voice settings (for ElevenLabs)"
    )


class TextToAudioRequest(BaseModel):
    """Text-to-audio request"""

    prompt: str = Field(..., min_length=1, max_length=500)
    model: Optional[str] = None
    duration: float = Field(default=5.0, ge=1.0, le=30.0)


# ===================
# Deepgram Schemas
# ===================


class DeepgramSpeechToTextRequest(BaseModel):
    """Deepgram speech-to-text request"""

    audio: str = Field(..., description="Audio URL, base64-encoded audio, or file path")
    model: Optional[str] = Field(
        None,
        description="Model to use (nova-3, nova-2, nova-2-phonecall, enhanced, base, whisper, etc.)",
    )
    language: Optional[str] = Field(
        None,
        description="Language code (e.g., 'en', 'es') - auto-detected if not provided",
    )
    punctuate: bool = Field(
        default=True, description="Add punctuation and capitalization"
    )
    diarize: bool = Field(default=False, description="Identify speakers in the audio")
    smart_format: bool = Field(
        default=True, description="Apply smart formatting (numbers, dates, etc.)"
    )
    detect_language: bool = Field(
        default=False, description="Automatically detect language"
    )
    return_timestamps: bool = Field(
        default=False, description="Return word-level timestamps"
    )


class DeepgramSpeechToTextResponse(BaseModel):
    """Deepgram speech-to-text response"""

    model_config = ConfigDict(protected_namespaces=())

    transcript: str
    confidence: Optional[float] = None
    words: Optional[List[Dict[str, Any]]] = None
    model: str
    model_info: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None
    channels: Optional[int] = None
    language: Optional[str] = None
    request_id: Optional[str] = None


class DeepgramTextToSpeechRequest(BaseModel):
    """Deepgram text-to-speech request"""

    text: str = Field(
        ..., min_length=1, max_length=5000, description="Text to convert to speech"
    )
    model: Optional[str] = Field(
        None, description="Voice model (aura-asteria-en, aura-luna-en, etc.)"
    )
    encoding: Optional[str] = Field(
        default="mp3", description="Audio encoding format (mp3, wav, opus, flac)"
    )
    sample_rate: Optional[int] = Field(default=24000, description="Sample rate in Hz")
    container: Optional[str] = Field(None, description="Container format")


class DeepgramTextToSpeechResponse(BaseModel):
    """Deepgram text-to-speech response"""

    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    model: str
    duration_ms: Optional[int] = None
    content_type: Optional[str] = None
    text: str


class DeepgramSummarizationRequest(BaseModel):
    """Deepgram text summarization request"""

    text: str = Field(
        ..., min_length=1, max_length=50000, description="Text to summarize"
    )
    language: str = Field(default="en", description="Language code")
    max_length: Optional[int] = Field(
        None, ge=1, le=1000, description="Maximum length of summary"
    )


class DeepgramSummarizationResponse(BaseModel):
    """Deepgram text summarization response"""

    summary: str
    original_text: str
    model: Optional[str] = None
    language: str
    original_length: Optional[int] = None
    summary_length: Optional[int] = None


# ===================
# ElevenLabs Schemas
# ===================


class ElevenLabsVoiceSettings(BaseModel):
    """ElevenLabs voice settings for TTS generation"""

    stability: float = Field(
        0.5, ge=0.0, le=1.0, description="Voice stability (0.0-1.0)"
    )
    similarity_boost: float = Field(
        0.75, ge=0.0, le=1.0, description="Similarity boost (0.0-1.0)"
    )
    style: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Style setting (0.0-1.0), only for models that support it",
    )
    use_speaker_boost: bool = Field(True, description="Enable speaker boost")


class ElevenLabsTTSRequest(BaseModel):
    """ElevenLabs text-to-speech request"""

    model_config = ConfigDict(protected_namespaces=())

    text: str = Field(
        ..., min_length=1, max_length=10000, description="Text to convert to speech"
    )
    voice_id: Optional[str] = Field(None, description="Voice ID (overrides default)")
    model_id: Optional[str] = Field(None, description="Model ID (overrides default)")
    voice_settings: Optional[ElevenLabsVoiceSettings] = Field(
        None, description="Voice customization settings"
    )
    return_base64: bool = Field(
        True, description="Return audio as base64 encoded string"
    )
    optimize_streaming_latency: Optional[int] = Field(
        None, ge=0, le=4, description="Optimize for streaming latency (0-4)"
    )


class ElevenLabsTTSResponse(BaseModel):
    """ElevenLabs text-to-speech response"""

    model_config = ConfigDict(protected_namespaces=())

    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio data")
    audio_url: Optional[str] = Field(
        None, description="URL to audio file (if applicable)"
    )
    voice_id: str
    model_id: str
    text: str
    content_type: str = Field(default="audio/mpeg", description="Audio content type")
    duration_ms: Optional[int] = Field(
        None, description="Estimated audio duration in milliseconds"
    )


class ElevenLabsVoiceResponse(BaseModel):
    """ElevenLabs voice information response"""

    voice_id: str
    name: str
    category: str
    labels: Dict[str, str] = Field(
        default_factory=dict, description="Voice labels (gender, accent, age, use_case)"
    )
    preview_url: Optional[str] = None
    fine_tuning_state: Dict[str, str] = Field(
        default_factory=dict, description="Fine-tuning state per model"
    )
    high_quality_base_model_ids: List[str] = Field(
        default_factory=list, description="Supported high-quality models"
    )
    is_owner: bool = False
    is_legacy: bool = False
    is_mixed: bool = False


class ElevenLabsVoicesResponse(BaseModel):
    """ElevenLabs voices list response"""

    voices: List[ElevenLabsVoiceResponse]


class ElevenLabsModelResponse(BaseModel):
    """ElevenLabs model information response"""

    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    name: str
    description: str
    can_be_finetuned: bool
    can_do_text_to_speech: bool
    can_do_voice_conversion: bool
    can_use_style: bool
    can_use_speaker_boost: bool
    languages: List[Dict[str, str]] = Field(
        default_factory=list, description="Supported languages"
    )
    max_characters_request: int = Field(description="Maximum characters per request")
    token_cost_factor: float = Field(description="Token cost multiplier")
    concurrency_group: str = Field(description="Concurrency group (standard/turbo)")


class ElevenLabsModelsResponse(BaseModel):
    """ElevenLabs models list response"""

    models: List[ElevenLabsModelResponse]


# ===================
# Gemini Schemas
# ===================


class GeminiEmbeddingRequest(BaseModel):
    """Gemini embedding request"""

    text: str = Field(..., min_length=1)
    model: Optional[str] = None


class GeminiEmbeddingResponse(BaseModel):
    """Gemini embedding response"""

    embedding: List[float]
    model: str
    usage: Optional[Dict[str, int]] = None


# ===================
# Deep Infra Schemas
# ===================


class DeepInfraCompletionRequest(BaseModel):
    """Deep Infra text completion request"""

    prompt: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = None
    max_tokens: int = Field(default=250, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: Optional[float] = Field(None, ge=0, le=1)
    stop: Optional[List[str]] = None


class DeepInfraCompletionResponse(BaseModel):
    """Deep Infra text completion response"""

    text: str
    model: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None


class DeepInfraEmbeddingRequest(BaseModel):
    """Deep Infra embedding request"""

    input: Union[str, List[str]] = Field(
        ..., description="Text or list of texts to embed"
    )
    model: Optional[str] = Field(None, description="Embedding model to use")


class DeepInfraEmbeddingResponse(BaseModel):
    """Deep Infra embedding response"""

    embeddings: List[List[float]] = Field(..., description="List of embedding vectors")
    model: str
    usage: Dict[str, int]


class DeepInfraInferenceRequest(BaseModel):
    """Deep Infra direct inference request"""

    model_config = ConfigDict(protected_namespaces=())

    model_path: str = Field(
        ..., description="Model path in format 'organization/model-name'"
    )
    input: Dict[str, Any] = Field(..., description="Input data for the model")


class DeepInfraInferenceResponse(BaseModel):
    """Deep Infra direct inference response"""

    data: Optional[Dict[str, Any]] = None
    image: Optional[str] = Field(
        None, description="Base64-encoded image if model generates images"
    )
    content_type: Optional[str] = None
    model: str


class DeepInfraImageGenerationRequest(BaseModel):
    """Deep Infra image generation request"""

    prompt: str = Field(..., min_length=1, max_length=1000)
    model: Optional[str] = Field(
        None,
        description="Image generation model (FLUX-1-dev, FLUX-1-schnell, sdxl-turbo)",
    )
    negative_prompt: Optional[str] = Field(None, max_length=1000)
    num_inference_steps: Optional[int] = Field(None, ge=1, le=100)
    guidance_scale: Optional[float] = Field(None, ge=0, le=20)
    seed: Optional[int] = None


class DeepInfraImageGenerationResponse(BaseModel):
    """Deep Infra image generation response"""

    image: str = Field(..., description="Base64-encoded image")
    model: str
    content_type: str = "image/png"
    format: str = "base64"


class BatchRequestItem(BaseModel):
    """Single batch request item"""

    request: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class BatchCreateRequest(BaseModel):
    """Create batch request"""

    requests: List[BatchRequestItem] = Field(..., min_length=1)
    display_name: Optional[str] = None
    model: Optional[str] = None


class BatchCreateResponse(BaseModel):
    """Batch creation response"""

    name: str
    metadata: Optional[Dict[str, Any]] = None


class BatchStatusResponse(BaseModel):
    """Batch status response"""

    name: str
    state: str
    metadata: Optional[Dict[str, Any]] = None
    done: bool = False
    response: Optional[Dict[str, Any]] = None


class VisionAnalyzeRequest(BaseModel):
    """Vision analysis request"""

    image: str = Field(..., description="Image URL or base64-encoded image")
    prompt: str = Field(..., min_length=1)
    model: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class VisionAnalyzeResponse(BaseModel):
    """Vision analysis response"""

    text: str
    model: str
    usage: Optional[Dict[str, Any]] = None


class ImagenGenerateRequest(BaseModel):
    """Imagen image generation request"""

    prompt: str = Field(..., min_length=1, max_length=2000)
    aspect_ratio: Optional[str] = None
    number_of_images: int = Field(default=1, ge=1, le=4)
    safety_filter_level: Optional[str] = None
    person_generation: Optional[str] = None
    seed: Optional[int] = None
    model: Optional[str] = None


class ImagenImage(BaseModel):
    """Generated image"""

    base64: Optional[str] = None
    uri: Optional[str] = None
    mimeType: str = "image/png"


class ImagenGenerateResponse(BaseModel):
    """Imagen generation response"""

    images: List[ImagenImage]
    model: str
    prompt: str


class VeoGenerateRequest(BaseModel):
    """Veo video generation request"""

    prompt: str = Field(..., min_length=1, max_length=2000)
    aspect_ratio: Optional[str] = None
    duration: Optional[str] = None
    model: Optional[str] = None


class VeoGenerateResponse(BaseModel):
    """Veo generation response"""

    operation_name: str
    model: str
    prompt: str


class VeoStatusResponse(BaseModel):
    """Veo operation status response"""

    status: str
    operation_name: str
    videos: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class FunctionDeclaration(BaseModel):
    """Function declaration for function calling"""

    name: str
    description: str
    parameters: Dict[str, Any]


class FunctionCall(BaseModel):
    """Function call from model"""

    name: str
    arguments: Dict[str, Any]


class FunctionResponse(BaseModel):
    """Function call response"""

    name: str
    response: Any


class OpenAIChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""

    model: str
    messages: List[Dict[str, str]]
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192)
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None


class OpenAIModelInfo(BaseModel):
    """OpenAI model information"""

    id: str
    object: str = "model"
    created: int
    owned_by: str = "google"


# ===================
# OpenRouter Schemas
# ===================


class OpenRouterModel(BaseModel):
    """OpenRouter model information"""

    id: str = Field(..., description="Model identifier (e.g., 'openai/gpt-4o')")
    name: Optional[str] = Field(None, description="Human-readable model name")
    description: Optional[str] = Field(None, description="Model description")
    pricing: Optional[Dict[str, str]] = Field(
        None, description="Pricing per 1M tokens (prompt/completion)"
    )
    context_length: Optional[int] = Field(
        None, ge=0, description="Maximum context length in tokens"
    )
    architecture: Optional[Dict[str, Any]] = Field(
        None, description="Model architecture details"
    )
    capabilities: List[str] = Field(
        default_factory=list,
        description="Model capabilities (chat, vision, code, etc.)",
    )
    top_provider: Optional[Dict[str, Any]] = Field(
        None, description="Primary provider information"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "description": "OpenAI's most advanced model",
                "context_length": 128000,
                "pricing": {"prompt": "0.0025", "completion": "0.01"},
                "capabilities": ["chat", "vision"],
                "top_provider": {"name": "OpenAI"},
            }
        }
    )


class OpenRouterAutoRouteRequest(BaseModel):
    """Request for auto-routing"""

    query: str = Field(
        ..., min_length=1, max_length=10000, description="User query to route"
    )
    requirements: Optional[Dict[str, Any]] = Field(
        None, description="Optional requirements (context_length, capabilities, etc.)"
    )
    prefer_speed: bool = Field(False, description="Prefer faster models over quality")
    max_cost: Optional[float] = Field(
        None, ge=0, description="Maximum cost per 1M tokens"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Explain quantum computing",
                "requirements": {"context_length": 10000},
                "prefer_speed": False,
                "max_cost": 0.01,
            }
        }
    )


class OpenRouterAutoRouteResponse(BaseModel):
    """Auto-routing result"""

    selected_model: str = Field(..., description="Selected model identifier")
    reasoning: str = Field(..., description="Reasoning for model selection")
    alternatives: List[str] = Field(
        default_factory=list, description="Alternative model options"
    )
    estimated_cost: Optional[float] = Field(
        None, ge=0, description="Estimated cost per 1M tokens"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "selected_model": "openai/gpt-4o",
                "reasoning": "High quality, good at code",
                "alternatives": [
                    "anthropic/claude-3.5-sonnet",
                    "google/gemini-2.0-flash-001",
                ],
                "estimated_cost": 0.0125,
            }
        }
    )


class OpenRouterEmbeddingRequest(BaseModel):
    """OpenRouter embedding request"""

    text: Optional[str] = Field(
        None, min_length=1, max_length=100000, description="Single text to embed"
    )
    texts: Optional[List[str]] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Multiple texts to embed (batch)",
    )
    model: Optional[str] = Field(
        default="openai/text-embedding-3-small", description="Embedding model to use"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"text": "Hello world", "model": "openai/text-embedding-3-small"}
        }
    )

    @classmethod
    def model_validate(cls, values):
        """Validate that either text or texts is provided"""
        if isinstance(values, dict):
            if not values.get("text") and not values.get("texts"):
                raise ValueError("Either 'text' or 'texts' must be provided")
        return values


class OpenRouterEmbeddingResponse(BaseModel):
    """OpenRouter embedding response"""

    embedding: Optional[List[float]] = Field(
        None, description="Single embedding vector"
    )
    embeddings: Optional[List[List[float]]] = Field(
        None, description="Multiple embedding vectors"
    )
    model: str = Field(..., description="Model used for embedding")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage information")
    cost: Optional[float] = Field(None, ge=0, description="Estimated cost in USD")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "embedding": [0.1, 0.2, 0.3],
                "model": "openai/text-embedding-3-small",
                "usage": {"total_tokens": 10},
                "cost": 0.000002,
            }
        }
    )


# ===================
# Benchmark Schemas
# ===================


class BenchmarkRequest(BaseModel):
    """Request for single provider benchmark"""

    provider: LLMProvider
    model: str
    prompt: str = Field(
        default="Explain the importance of low latency LLMs",
        min_length=1,
        max_length=10000,
    )
    temperature: float = Field(default=0.5, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    streaming: bool = False
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    stop_sequences: Optional[List[str]] = None


class BenchmarkResult(BaseModel):
    """Result from a single benchmark"""

    run_id: Optional[str] = None
    provider: str
    model: str
    ttft: Optional[float] = None  # Time to first token (seconds)
    total_time: float  # Total response time (seconds)
    tokens_generated: int
    prompt_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: Optional[float] = None
    success: bool
    error: Optional[str] = None
    error_type: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    response_preview: Optional[str] = None  # First 200 chars of response


class CompareBenchmarkRequest(BaseModel):
    """Request to compare multiple providers"""

    providers: List[LLMProvider] = Field(..., min_length=1, max_length=10)
    prompt: str = Field(
        default="Explain the importance of low latency LLMs",
        min_length=1,
        max_length=10000,
    )
    model: Optional[str] = None  # If specified, use same model for all providers
    temperature: float = Field(default=0.5, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    streaming: bool = False
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)


class ComparativeBenchmarkResult(BaseModel):
    """Results from comparing multiple providers"""

    run_id: str
    prompt: str
    results: List[BenchmarkResult]
    fastest_provider: Optional[str] = None
    highest_throughput: Optional[str] = None
    rankings: Dict[str, int] = Field(default_factory=dict)  # Provider -> rank
    timestamp: datetime = Field(default_factory=utc_now)


class StressTestRequest(BaseModel):
    """Request for stress testing a provider"""

    provider: LLMProvider
    model: str
    prompt: str = Field(
        default="Explain the importance of low latency LLMs",
        min_length=1,
        max_length=10000,
    )
    concurrent_requests: int = Field(default=5, ge=1, le=50)
    duration_seconds: int = Field(default=60, ge=10, le=300)
    temperature: float = Field(default=0.5, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=8192)


class StressTestResult(BaseModel):
    """Results from stress test"""

    run_id: str
    provider: str
    model: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    error_rate: float  # Percentage
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class BenchmarkHistoryItem(BaseModel):
    """Single benchmark run in history"""

    id: str
    run_type: str
    prompt: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result_count: int = 0


class ProviderStats(BaseModel):
    """Provider statistics"""

    provider: str
    model: Optional[str] = None
    total_runs: int
    success_rate: float
    avg_ttft: Optional[float] = None
    min_ttft: Optional[float] = None
    max_ttft: Optional[float] = None
    avg_total_time: Optional[float] = None
    min_total_time: Optional[float] = None
    max_total_time: Optional[float] = None
    avg_tokens_per_second: Optional[float] = None
    min_tokens_per_second: Optional[float] = None
    max_tokens_per_second: Optional[float] = None
    total_tokens: int
    period_days: int


class ModelComparison(BaseModel):
    """Model comparison across providers"""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    providers: List[ProviderStats]
    best_provider: Optional[str] = None
    fastest_provider: Optional[str] = None


class PerformanceTrend(BaseModel):
    """Performance trend data point"""

    date: str
    avg: float
    min: float
    max: float
    count: int


class LeaderboardEntry(BaseModel):
    """Leaderboard entry"""

    provider: str
    model: str
    metric_value: float
    rank: int
    total_runs: int


# ===================
# Groq API Schemas
# ===================


class GroqVisionRequest(BaseModel):
    """Groq vision analysis request"""

    image: str = Field(..., description="Image URL or base64-encoded image")
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text prompt describing what to analyze",
    )
    model: Optional[str] = Field(
        default="llama-3.2-11b-vision-preview", description="Vision model to use"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)


class GroqVisionResponse(BaseModel):
    """Groq vision analysis response"""

    text: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class GroqVisionBatchRequest(BaseModel):
    """Groq batch vision analysis request"""

    images: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of image URLs or base64-encoded images",
    )
    prompt: str = Field(..., min_length=1, max_length=5000)
    model: Optional[str] = Field(default="llama-3.2-11b-vision-preview")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)


class GroqVisionBatchResponse(BaseModel):
    """Groq batch vision analysis response"""

    text: str
    model: str
    image_count: int
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class GroqSafetyCheckRequest(BaseModel):
    """Groq content safety check request"""

    content: str = Field(
        ..., min_length=1, max_length=50000, description="Content to check for safety"
    )
    check_type: str = Field(
        default="user",
        pattern="^(user|assistant)$",
        description="Type of content: user or assistant",
    )


class GroqSafetyCheckResponse(BaseModel):
    """Groq content safety check response"""

    safe: bool
    categories: List[str] = Field(
        default_factory=list, description="Safety violation categories (S1, S2, etc.)"
    )
    classification: str = Field(
        ..., description="Classification result: 'safe' or 'unsafe\\nS1' etc."
    )
    risk_level: str = Field(
        ..., description="Risk level: none, low, medium, high, critical"
    )
    check_type: str
    raw_response: Optional[Dict[str, Any]] = None


class GroqPromptGuardRequest(BaseModel):
    """Groq prompt injection detection request"""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Prompt to check for injection attacks",
    )
    model: str = Field(
        default="meta-llama/llama-prompt-guard-2-86m",
        description="Prompt guard model to use",
    )
    threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Risk score threshold"
    )


class GroqPromptGuardResponse(BaseModel):
    """Groq prompt injection detection response"""

    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Risk score from 0.0 to 1.0"
    )
    is_injection: bool = Field(
        ..., description="Whether prompt is classified as injection"
    )
    threshold: float = Field(..., description="Threshold used for classification")
    risk_level: str = Field(..., description="Risk level: low, medium, high, unknown")
    model: str
    raw_response: Optional[Dict[str, Any]] = None


class GroqConversationModerationRequest(BaseModel):
    """Groq conversation moderation request"""

    messages: List[Dict[str, str]] = Field(
        ...,
        min_length=1,
        description="List of messages with 'role' and 'content' keys",
    )


class GroqConversationModerationResponse(BaseModel):
    """Groq conversation moderation response"""

    safe: bool = Field(..., description="Whether entire conversation is safe")
    messages_checked: int
    violations: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of violations found"
    )
    details: List[Dict[str, Any]] = Field(
        default_factory=list, description="Detailed results for each message"
    )


class GroqModelSelectionRequest(BaseModel):
    """Groq model selection request"""

    task_type: str = Field(
        ...,
        description="Task type: speed, reasoning, vision, coding, long_context, safety",
    )
    complexity: str = Field(
        default="medium", pattern="^(low|medium|high)$", description="Task complexity"
    )
    requirements: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional requirements (e.g., needs_vision, long_context)",
    )


class GroqModelSelectionResponse(BaseModel):
    """Groq model selection response"""

    recommended_model: str
    alternatives: List[str] = Field(default_factory=list)
    reasoning: str
    capabilities: Dict[str, Any] = Field(default_factory=dict)


class GroqModelInfo(BaseModel):
    """Groq model information"""

    id: str
    category: str = Field(
        ..., description="Model category: chat, vision, safety, reasoning, coding"
    )
    context_window: int
    capabilities: List[str] = Field(default_factory=list)
    speed_tier: str = Field(..., description="Speed tier: fast, medium, slow")
    deprecated: bool = False
    use_cases: List[str] = Field(default_factory=list)


class GroqModelsListResponse(BaseModel):
    """Groq models list response"""

    models: List[GroqModelInfo]
    total: int


class GroqTranscribeRequest(BaseModel):
    """Groq speech-to-text transcription request"""

    audio: str = Field(..., description="Audio URL, base64-encoded audio, or file path")
    model: Optional[str] = Field(
        default="whisper-large-v3-turbo", description="Whisper model to use"
    )
    language: Optional[str] = Field(
        default=None,
        description="Language code (e.g., 'en', 'es') - auto-detected if not provided",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0 for deterministic)",
    )
    response_format: str = Field(
        default="json", pattern="^(json|text|srt|vtt|verbose_json)$"
    )


class GroqTranscribeResponse(BaseModel):
    """Groq speech-to-text transcription response"""

    text: str
    model: str
    language: Optional[str] = None
    duration: Optional[float] = None
    words: Optional[List[Dict[str, Any]]] = None
    segments: Optional[List[Dict[str, Any]]] = None
    raw_response: Optional[Dict[str, Any]] = None


# ===================
# Cohere API Schemas
# ===================


class CohereChatMessage(BaseModel):
    """Cohere chat message"""

    role: str  # USER, CHATBOT, SYSTEM, TOOL
    message: str


class CohereConnector(BaseModel):
    """Cohere connector configuration"""

    id: str  # web-search or custom connector ID
    options: Optional[Dict[str, Any]] = None


class CohereChatRequest(BaseModel):
    """Cohere chat request"""

    message: str
    model: Optional[str] = None
    chat_history: List[CohereChatMessage] = Field(default_factory=list)
    connectors: Optional[List[CohereConnector]] = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    stream: bool = False


class CohereCitation(BaseModel):
    """Cohere citation"""

    start: int
    end: int
    text: str
    document_ids: List[str]


class CohereDocument(BaseModel):
    """Cohere document"""

    id: str
    snippet: str
    title: Optional[str] = None
    url: Optional[str] = None
    timestamp: Optional[str] = None


class CohereChatResponse(BaseModel):
    """Cohere chat response"""

    text: str
    chat_history: List[CohereChatMessage]
    citations: Optional[List[CohereCitation]] = None
    documents: Optional[List[CohereDocument]] = None
    search_queries: Optional[List[Dict[str, str]]] = None
    generation_id: str
    finish_reason: str
    meta: Dict[str, Any]


class CohereSummarizeRequest(BaseModel):
    """Cohere summarize request"""

    text: str = Field(..., min_length=250, max_length=100000)
    model: Optional[str] = None
    length: Optional[str] = Field(None, pattern="^(short|medium|long)$")
    format: Optional[str] = Field(None, pattern="^(paragraph|bullets)$")
    extractiveness: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    temperature: Optional[float] = Field(None, ge=0, le=5)


class CohereSummarizeResponse(BaseModel):
    """Cohere summarize response"""

    summary: str
    id: str
    meta: Dict[str, Any]


class CohereEmbedRequest(BaseModel):
    """Cohere embed request"""

    texts: List[str] = Field(..., min_length=1, max_length=96)
    model: str = "embed-english-v3.0"
    input_type: str = Field(
        ...,
        pattern="^(search_document|search_query|classification|clustering|semantic_similarity)$",
    )
    truncate: Optional[str] = Field("END", pattern="^(NONE|START|END)$")


class CohereEmbedResponse(BaseModel):
    """Cohere embed response"""

    embeddings: List[List[float]]
    id: str
    texts: List[str]
    meta: Dict[str, Any]


class CohereClassifyExample(BaseModel):
    """Cohere classification example"""

    text: str
    label: str


class CohereClassifyRequest(BaseModel):
    """Cohere classify request"""

    inputs: List[str] = Field(..., min_length=1, max_length=96)
    model: str = "embed-english-v3.0"
    examples: List[CohereClassifyExample] = Field(..., min_length=2)
    truncate: Optional[str] = Field("END", pattern="^(NONE|START|END)$")


class CohereClassification(BaseModel):
    """Cohere classification result"""

    input: str
    prediction: str
    confidence: float
    labels: Dict[str, float]


class CohereClassifyResponse(BaseModel):
    """Cohere classify response"""

    classifications: List[CohereClassification]
    id: str
    meta: Dict[str, Any]


class CohereRerankRequest(BaseModel):
    """Cohere rerank request"""

    query: str = Field(..., min_length=1)
    documents: List[str] = Field(..., min_length=1)
    model: str = "rerank-english-v3.0"
    top_n: Optional[int] = Field(None, ge=1)
    return_documents: bool = True


class CohereRerankResult(BaseModel):
    """Cohere rerank result"""

    index: int
    relevance_score: float
    document: Optional[str] = None


class CohereRerankResponse(BaseModel):
    """Cohere rerank response"""

    results: List[CohereRerankResult]
    id: str
    meta: Dict[str, Any]


class CohereConnectorCreate(BaseModel):
    """Cohere connector creation request"""

    name: str
    url: str
    description: Optional[str] = None


class CohereConnectorResponse(BaseModel):
    """Cohere connector response"""

    id: str
    name: str
    url: str
    created_at: str
    updated_at: str


class CohereDatasetCreate(BaseModel):
    """Cohere dataset creation request"""

    name: str
    type: str  # e.g., "generative-finetune-input"


class CohereDatasetResponse(BaseModel):
    """Cohere dataset response"""

    id: str
    name: str
    dataset_type: str
    validation_status: str
    created_at: str


class CohereEmbedJobRequest(BaseModel):
    """Cohere embed job request"""

    model: str = "embed-english-v3.0"
    dataset_id: str
    input_type: str = "search_document"


class CohereEmbedJobResponse(BaseModel):
    """Cohere embed job response"""

    job_id: str
    status: str  # pending, processing, complete, failed
    created_at: str
    meta: Dict[str, Any]


class CohereFinetunedModelResponse(BaseModel):
    """Cohere fine-tuned model response"""

    id: str
    name: str
    status: str
    settings: Dict[str, Any]
    created_at: str


# ===================
# NVIDIA AI Schemas
# ===================


class NVIDIAChatRequest(BaseModel):
    """NVIDIA chat completion request"""

    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    model: str = Field(..., description="Model identifier")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(
        None, gt=0, description="Maximum tokens to generate"
    )
    stream: bool = Field(False, description="Whether to stream the response")
    top_p: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Nucleus sampling parameter"
    )
    top_k: Optional[int] = Field(None, gt=0, description="Top-k sampling parameter")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    tools: Optional[List[Dict[str, Any]]] = Field(
        None, description="Function calling tools"
    )


class NVIDIAChatResponse(BaseModel):
    """NVIDIA chat completion response"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    nvcf_reqid: Optional[str] = None
    nvcf_status: Optional[str] = None


class NVIDIAEmbeddingRequest(BaseModel):
    """NVIDIA embedding request"""

    input: Union[str, List[str]] = Field(
        ..., description="Text(s) to embed (max 32 for batch)"
    )
    model: str = Field(..., description="Embedding model identifier")
    input_type: str = Field("query", description="Input type: 'query' or 'passage'")
    truncate: str = Field(
        "END", description="Truncation strategy: 'START', 'END', or 'NONE'"
    )
    dimensions: Optional[int] = Field(
        None, description="Embedding dimensions (256, 512, 768, 1024)"
    )


class NVIDIAEmbeddingResponse(BaseModel):
    """NVIDIA embedding response"""

    object: str = "list"
    data: List[Dict[str, Any]] = Field(..., description="Embedding data")
    model: str
    usage: Dict[str, int]


class NVIDIAVisionRequest(BaseModel):
    """NVIDIA vision analysis request"""

    prompt: str = Field(..., description="Text prompt about the image")
    image: Optional[str] = Field(None, description="Base64-encoded image")
    image_url: Optional[str] = Field(None, description="Image URL")
    model: Optional[str] = Field(None, description="Vision model identifier")
    max_tokens: Optional[int] = Field(
        None, gt=0, description="Maximum tokens in response"
    )
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    response_format: Optional[str] = Field(
        None, description="Response format (e.g., 'json_object')"
    )


class NVIDIAVisionResponse(BaseModel):
    """NVIDIA vision analysis response"""

    text: str
    model: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None
    nvcf_reqid: Optional[str] = None
    nvcf_status: Optional[str] = None


class NVIDIANIMRequest(BaseModel):
    """NVIDIA NIM inference request"""

    model_config = ConfigDict(protected_namespaces=())

    model_id: str = Field(..., description="Deployed model identifier")
    messages: List[Dict[str, Any]] = Field(..., description="Chat messages")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(
        None, gt=0, description="Maximum tokens to generate"
    )
    stream: bool = Field(False, description="Whether to stream the response")


class NVIDIANIMResponse(BaseModel):
    """NVIDIA NIM inference response"""

    id: str
    object: str = "chat.completion"
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    nvcf_reqid: Optional[str] = None
    nvcf_status: Optional[str] = None


class NVIDIAModelInfo(BaseModel):
    """NVIDIA model information"""

    id: str
    category: str
    provider: str
    capabilities: List[str]
    context_length: Optional[int] = None
    vision: bool = False
    reasoning: bool = False
    code: bool = False
    description: Optional[str] = None


# ===================
# Reka AI Schemas
# ===================


class RekaModel(BaseModel):
    """Reka AI model information"""

    id: str = Field(..., description="Model identifier (e.g., 'reka-flash-3')")
    name: Optional[str] = Field(None, description="Human-readable model name")
    description: Optional[str] = Field(None, description="Model description")
    capabilities: List[str] = Field(
        default_factory=list,
        description="Model capabilities (chat, reasoning, fast, balanced, powerful)",
    )
    category: Optional[str] = Field(
        None, description="Model category (core, flash, edge)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "reka-flash-3",
                "name": "Reka Flash 3",
                "description": "Fast model with reasoning capabilities",
                "capabilities": ["chat", "reasoning", "balanced"],
                "category": "flash",
            }
        }
    )


class RekaChatRequest(BaseModel):
    """Reka AI chat completion request"""

    messages: List[Dict[str, str]] = Field(
        ..., description="List of messages with 'role' and 'content' keys"
    )
    model: str = Field(default="reka-flash-3", description="Model identifier")
    stream: bool = Field(False, description="Whether to stream the response")
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        None, gt=0, description="Maximum tokens to generate"
    )
    top_p: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Nucleus sampling parameter"
    )
    stop: Optional[List[str]] = Field(None, description="Stop sequences")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    {"role": "user", "content": "What is the fifth prime number?"}
                ],
                "model": "reka-flash-3",
                "stream": False,
            }
        }
    )


class RekaChatResponse(BaseModel):
    """Reka AI chat completion response"""

    id: str = Field(..., description="Request ID")
    model: str = Field(..., description="Model used")
    usage: Dict[str, int] = Field(
        ..., description="Token usage (input_tokens, output_tokens)"
    )
    responses: List[Dict[str, Any]] = Field(..., description="Response messages")
    reasoning: Optional[str] = Field(
        None, description="Reasoning content (for reka-flash-3)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "71c14acb-3006-4493-a33c-b3e3cba2f43d",
                "model": "reka-flash-3",
                "usage": {"input_tokens": 14, "output_tokens": 1024},
                "responses": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "The fifth prime number is 11.",
                        }
                    }
                ],
            }
        }
    )
