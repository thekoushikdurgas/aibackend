"""
OpenRouter Model Registry
Intelligent model management and auto-routing
"""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OpenRouterModelRegistry:
    """
    Registry for managing OpenRouter models with intelligent auto-routing.
    Caches model information and provides smart model selection.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
    ):
        """
        Initialize model registry.

        Args:
            api_key: OpenRouter API key
            base_url: OpenRouter API base URL
            site_url: Site URL for tracking
            app_name: App name for tracking
        """
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = base_url or settings.openrouter_base_url
        self.site_url = site_url or settings.openrouter_site_url
        self.app_name = app_name or settings.openrouter_app_name

        # Cache for model list
        self._models: List[Dict[str, Any]] = []
        self._cache_time: float = 0
        self._cache_ttl: float = 3600  # 1 hour cache

        # Model categorization by provider (from Postman collection)
        self._provider_categories: Dict[str, List[str]] = {
            "claude": [
                "anthropic/claude-opus-4.1",
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3.5-haiku",
                "anthropic/claude-3-opus",
                "anthropic/claude-3-sonnet",
                "anthropic/claude-3-haiku",
            ],
            "gpt": [
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "openai/o3-mini",
                "openai/o3-mini-high",
                "openai/o1",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "openai/chatgpt-4o-latest",
                "openai/gpt-4-turbo-preview",
                "openai/gpt-3.5-turbo",
            ],
            "gemini": [
                "google/gemini-3-pro-preview",
                "google/gemini-2.0-flash-001",
                "google/gemini-pro-1.5",
                "google/gemini-flash-1.5",
                "google/gemini-pro",
                "google/gemma-2-27b-it",
                "google/gemma-2-9b-it",
            ],
            "llama": [
                "meta-llama/llama-3.3-70b-instruct",
                "meta-llama/llama-3.2-90b-vision-instruct",
                "meta-llama/llama-3.2-11b-vision-instruct",
                "meta-llama/llama-3.2-3b-instruct",
                "meta-llama/llama-3.2-1b-instruct",
                "meta-llama/llama-3.1-405b-instruct",
            ],
            "mistral": [
                "mistralai/mistral-large",
                "mistralai/mistral-small",
                "mistralai/mistral-tiny",
                "mistralai/mixtral-8x7b-instruct",
                "mistralai/codestral",
                "mistralai/mistral-nemo",
            ],
            "cohere": ["cohere/command-r-plus", "cohere/command-r", "cohere/command"],
            "deepseek": ["deepseek/deepseek-r1", "deepseek/deepseek-chat"],
            "grok": ["x-ai/grok-2"],
            "nova": ["amazon/nova-pro-v1", "amazon/nova-lite-v1"],
            "router": ["openrouter/auto"],
        }

        # Model categorization by capability
        self._capability_map: Dict[str, List[str]] = {
            "chat": [
                "openai/gpt-4o",
                "anthropic/claude-3.5-sonnet",
                "google/gemini-2.0-flash-001",
            ],
            "reasoning": ["openai/o1", "openai/o3-mini", "deepseek/deepseek-r1"],
            "vision": [
                "openai/gpt-4o",
                "google/gemini-2.0-flash-001",
                "anthropic/claude-3.5-sonnet",
            ],
            "code": [
                "openai/gpt-4o",
                "anthropic/claude-3.5-sonnet",
                "mistralai/codestral",
            ],
            "fast": [
                "openai/gpt-4o-mini",
                "google/gemini-2.0-flash-001",
                "anthropic/claude-3.5-haiku",
            ],
            "long_context": [
                "anthropic/claude-3.5-sonnet",
                "google/gemini-pro-1.5",
                "openai/gpt-4-turbo-preview",
            ],
        }

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name
        return headers

    async def fetch_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch model list from OpenRouter API.

        Args:
            force_refresh: Force refresh even if cache is valid

        Returns:
            List of model dictionaries
        """
        current_time = time.time()

        # Use cache if valid and not forcing refresh
        if (
            not force_refresh
            and self._models
            and (current_time - self._cache_time) < self._cache_ttl
        ):
            return self._models

        if not self.api_key:
            logger.warning("OpenRouter API key not configured, using default models")
            return self._get_default_models()

        try:
            url = f"{self.base_url}/models"
            headers = self._build_headers()

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Cache the models
                self._models = data.get("data", [])
                self._cache_time = current_time

                logger.info(f"Fetched {len(self._models)} models from OpenRouter")
                return self._models

        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            if self._models:
                # Return cached models if available
                logger.warning("Using cached model list")
                return self._models
            return self._get_default_models()

    def _get_default_models(self) -> List[Dict[str, Any]]:
        """Get default model list when API is unavailable - includes all models from Postman collection"""
        return [
            # Router
            {
                "id": "openrouter/auto",
                "name": "OpenRouter Auto",
                "description": "Automatic model selection",
                "context_length": 200000,
                "pricing": {"prompt": "0", "completion": "0"},
                "architecture": {},
                "top_provider": {"name": "OpenRouter"},
                "capabilities": ["chat", "auto-routing"],
            },
            # Claude Models
            {
                "id": "anthropic/claude-opus-4.1",
                "name": "Claude Opus 4.1",
                "description": "Anthropic's most capable model",
                "context_length": 200000,
                "pricing": {"prompt": "0.015", "completion": "0.075"},
                "top_provider": {"name": "Anthropic"},
                "capabilities": ["chat", "reasoning", "long_context"],
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "description": "Anthropic's balanced model",
                "context_length": 200000,
                "pricing": {"prompt": "0.003", "completion": "0.015"},
                "top_provider": {"name": "Anthropic"},
                "capabilities": ["chat", "vision", "long_context"],
            },
            {
                "id": "anthropic/claude-3.5-haiku",
                "name": "Claude 3.5 Haiku",
                "description": "Anthropic's fast model",
                "context_length": 200000,
                "pricing": {"prompt": "0.00025", "completion": "0.00125"},
                "top_provider": {"name": "Anthropic"},
                "capabilities": ["chat", "fast"],
            },
            {
                "id": "anthropic/claude-3-opus",
                "name": "Claude 3 Opus",
                "description": "Anthropic's powerful model",
                "context_length": 200000,
                "pricing": {"prompt": "0.015", "completion": "0.075"},
                "top_provider": {"name": "Anthropic"},
                "capabilities": ["chat", "reasoning"],
            },
            {
                "id": "anthropic/claude-3-sonnet",
                "name": "Claude 3 Sonnet",
                "description": "Anthropic's balanced model",
                "context_length": 200000,
                "pricing": {"prompt": "0.003", "completion": "0.015"},
                "top_provider": {"name": "Anthropic"},
                "capabilities": ["chat", "vision"],
            },
            {
                "id": "anthropic/claude-3-haiku",
                "name": "Claude 3 Haiku",
                "description": "Anthropic's fast model",
                "context_length": 200000,
                "pricing": {"prompt": "0.00025", "completion": "0.00125"},
                "top_provider": {"name": "Anthropic"},
                "capabilities": ["chat", "fast"],
            },
            # GPT Models
            {
                "id": "openai/gpt-oss-120b",
                "name": "GPT-OSS 120B",
                "description": "OpenAI's open-source 120B model",
                "context_length": 128000,
                "pricing": {"prompt": "0.002", "completion": "0.002"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat"],
            },
            {
                "id": "openai/gpt-oss-20b",
                "name": "GPT-OSS 20B",
                "description": "OpenAI's open-source 20B model",
                "context_length": 128000,
                "pricing": {"prompt": "0.0005", "completion": "0.0005"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat"],
            },
            {
                "id": "openai/o3-mini",
                "name": "O3 Mini",
                "description": "OpenAI's reasoning model (mini)",
                "context_length": 128000,
                "pricing": {"prompt": "0.15", "completion": "0.6"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat", "reasoning"],
            },
            {
                "id": "openai/o3-mini-high",
                "name": "O3 Mini High",
                "description": "OpenAI's reasoning model (mini, high)",
                "context_length": 128000,
                "pricing": {"prompt": "0.15", "completion": "0.6"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat", "reasoning"],
            },
            {
                "id": "openai/o1",
                "name": "O1",
                "description": "OpenAI's reasoning model",
                "context_length": 200000,
                "pricing": {"prompt": "0.15", "completion": "0.6"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat", "reasoning"],
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "description": "OpenAI's most advanced model",
                "context_length": 128000,
                "pricing": {"prompt": "0.0025", "completion": "0.01"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat", "vision"],
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "description": "OpenAI's fast model",
                "context_length": 128000,
                "pricing": {"prompt": "0.00015", "completion": "0.0006"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat", "fast"],
            },
            {
                "id": "openai/chatgpt-4o-latest",
                "name": "ChatGPT-4o Latest",
                "description": "Latest ChatGPT-4o model",
                "context_length": 128000,
                "pricing": {"prompt": "0.0025", "completion": "0.01"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat"],
            },
            {
                "id": "openai/gpt-4-turbo-preview",
                "name": "GPT-4 Turbo Preview",
                "description": "OpenAI's turbo preview model",
                "context_length": 128000,
                "pricing": {"prompt": "0.01", "completion": "0.03"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat", "long_context"],
            },
            {
                "id": "openai/gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "description": "OpenAI's efficient model",
                "context_length": 16385,
                "pricing": {"prompt": "0.0005", "completion": "0.0015"},
                "top_provider": {"name": "OpenAI"},
                "capabilities": ["chat", "fast"],
            },
            # Gemini Models
            {
                "id": "google/gemini-3-pro-preview",
                "name": "Gemini 3 Pro Preview",
                "description": "Google's latest preview model",
                "context_length": 1000000,
                "pricing": {"prompt": "0.00125", "completion": "0.005"},
                "top_provider": {"name": "Google"},
                "capabilities": ["chat", "vision", "long_context"],
            },
            {
                "id": "google/gemini-2.0-flash-001",
                "name": "Gemini 2.0 Flash",
                "description": "Google's fast model",
                "context_length": 1000000,
                "pricing": {"prompt": "0.075", "completion": "0.3"},
                "top_provider": {"name": "Google"},
                "capabilities": ["chat", "vision", "fast", "long_context"],
            },
            {
                "id": "google/gemini-pro-1.5",
                "name": "Gemini Pro 1.5",
                "description": "Google's pro model",
                "context_length": 1000000,
                "pricing": {"prompt": "0.125", "completion": "0.5"},
                "top_provider": {"name": "Google"},
                "capabilities": ["chat", "vision", "long_context"],
            },
            {
                "id": "google/gemini-flash-1.5",
                "name": "Gemini Flash 1.5",
                "description": "Google's flash model",
                "context_length": 1000000,
                "pricing": {"prompt": "0.075", "completion": "0.3"},
                "top_provider": {"name": "Google"},
                "capabilities": ["chat", "vision", "fast", "long_context"],
            },
            {
                "id": "google/gemini-pro",
                "name": "Gemini Pro",
                "description": "Google's pro model",
                "context_length": 32768,
                "pricing": {"prompt": "0.0005", "completion": "0.0015"},
                "top_provider": {"name": "Google"},
                "capabilities": ["chat", "vision"],
            },
            {
                "id": "google/gemma-2-27b-it",
                "name": "Gemma 2 27B Instruct",
                "description": "Google's Gemma 2 27B model",
                "context_length": 8192,
                "pricing": {"prompt": "0.0001", "completion": "0.0001"},
                "top_provider": {"name": "Google"},
                "capabilities": ["chat"],
            },
            {
                "id": "google/gemma-2-9b-it",
                "name": "Gemma 2 9B Instruct",
                "description": "Google's Gemma 2 9B model",
                "context_length": 8192,
                "pricing": {"prompt": "0.00005", "completion": "0.00005"},
                "top_provider": {"name": "Google"},
                "capabilities": ["chat"],
            },
            # Llama Models
            {
                "id": "meta-llama/llama-3.3-70b-instruct",
                "name": "Llama 3.3 70B Instruct",
                "description": "Meta's 70B model",
                "context_length": 131072,
                "pricing": {"prompt": "0.00059", "completion": "0.00079"},
                "top_provider": {"name": "Meta"},
                "capabilities": ["chat"],
            },
            {
                "id": "meta-llama/llama-3.2-90b-vision-instruct",
                "name": "Llama 3.2 90B Vision Instruct",
                "description": "Meta's 90B vision model",
                "context_length": 131072,
                "pricing": {"prompt": "0.001", "completion": "0.001"},
                "top_provider": {"name": "Meta"},
                "capabilities": ["chat", "vision"],
            },
            {
                "id": "meta-llama/llama-3.2-11b-vision-instruct",
                "name": "Llama 3.2 11B Vision Instruct",
                "description": "Meta's 11B vision model",
                "context_length": 131072,
                "pricing": {"prompt": "0.0001", "completion": "0.0001"},
                "top_provider": {"name": "Meta"},
                "capabilities": ["chat", "vision"],
            },
            {
                "id": "meta-llama/llama-3.2-3b-instruct",
                "name": "Llama 3.2 3B Instruct",
                "description": "Meta's 3B model",
                "context_length": 131072,
                "pricing": {"prompt": "0.00005", "completion": "0.00005"},
                "top_provider": {"name": "Meta"},
                "capabilities": ["chat", "fast"],
            },
            {
                "id": "meta-llama/llama-3.2-1b-instruct",
                "name": "Llama 3.2 1B Instruct",
                "description": "Meta's 1B model",
                "context_length": 131072,
                "pricing": {"prompt": "0.00002", "completion": "0.00002"},
                "top_provider": {"name": "Meta"},
                "capabilities": ["chat", "fast"],
            },
            {
                "id": "meta-llama/llama-3.1-405b-instruct",
                "name": "Llama 3.1 405B Instruct",
                "description": "Meta's 405B model",
                "context_length": 131072,
                "pricing": {"prompt": "0.0027", "completion": "0.0027"},
                "top_provider": {"name": "Meta"},
                "capabilities": ["chat"],
            },
            # Mistral Models
            {
                "id": "mistralai/mistral-large",
                "name": "Mistral Large",
                "description": "Mistral's large model",
                "context_length": 128000,
                "pricing": {"prompt": "0.0027", "completion": "0.0081"},
                "top_provider": {"name": "Mistral"},
                "capabilities": ["chat"],
            },
            {
                "id": "mistralai/mistral-small",
                "name": "Mistral Small",
                "description": "Mistral's small model",
                "context_length": 128000,
                "pricing": {"prompt": "0.0002", "completion": "0.0006"},
                "top_provider": {"name": "Mistral"},
                "capabilities": ["chat", "fast"],
            },
            {
                "id": "mistralai/mistral-tiny",
                "name": "Mistral Tiny",
                "description": "Mistral's tiny model",
                "context_length": 128000,
                "pricing": {"prompt": "0.0001", "completion": "0.0003"},
                "top_provider": {"name": "Mistral"},
                "capabilities": ["chat", "fast"],
            },
            {
                "id": "mistralai/mixtral-8x7b-instruct",
                "name": "Mixtral 8x7B Instruct",
                "description": "Mistral's Mixtral model",
                "context_length": 32768,
                "pricing": {"prompt": "0.00027", "completion": "0.00027"},
                "top_provider": {"name": "Mistral"},
                "capabilities": ["chat"],
            },
            {
                "id": "mistralai/codestral",
                "name": "Codestral",
                "description": "Mistral's code model",
                "context_length": 32768,
                "pricing": {"prompt": "0.0002", "completion": "0.0002"},
                "top_provider": {"name": "Mistral"},
                "capabilities": ["chat", "code"],
            },
            {
                "id": "mistralai/mistral-nemo",
                "name": "Mistral Nemo",
                "description": "Mistral's Nemo model",
                "context_length": 128000,
                "pricing": {"prompt": "0.0001", "completion": "0.0001"},
                "top_provider": {"name": "Mistral"},
                "capabilities": ["chat", "fast"],
            },
            # Cohere Models
            {
                "id": "cohere/command-r-plus",
                "name": "Command R Plus",
                "description": "Cohere's plus model",
                "context_length": 128000,
                "pricing": {"prompt": "0.003", "completion": "0.015"},
                "top_provider": {"name": "Cohere"},
                "capabilities": ["chat"],
            },
            {
                "id": "cohere/command-r",
                "name": "Command R",
                "description": "Cohere's R model",
                "context_length": 128000,
                "pricing": {"prompt": "0.0005", "completion": "0.0015"},
                "top_provider": {"name": "Cohere"},
                "capabilities": ["chat"],
            },
            {
                "id": "cohere/command",
                "name": "Command",
                "description": "Cohere's command model",
                "context_length": 4096,
                "pricing": {"prompt": "0.00015", "completion": "0.0006"},
                "top_provider": {"name": "Cohere"},
                "capabilities": ["chat", "fast"],
            },
            # DeepSeek Models
            {
                "id": "deepseek/deepseek-r1",
                "name": "DeepSeek R1",
                "description": "DeepSeek's reasoning model",
                "context_length": 64000,
                "pricing": {"prompt": "0.00055", "completion": "0.002"},
                "top_provider": {"name": "DeepSeek"},
                "capabilities": ["chat", "reasoning"],
            },
            {
                "id": "deepseek/deepseek-chat",
                "name": "DeepSeek Chat",
                "description": "DeepSeek's chat model",
                "context_length": 64000,
                "pricing": {"prompt": "0.00014", "completion": "0.00028"},
                "top_provider": {"name": "DeepSeek"},
                "capabilities": ["chat"],
            },
            # Grok Models
            {
                "id": "x-ai/grok-2",
                "name": "Grok 2",
                "description": "xAI's Grok model",
                "context_length": 131072,
                "pricing": {"prompt": "0.01", "completion": "0.03"},
                "top_provider": {"name": "xAI"},
                "capabilities": ["chat"],
            },
            # Nova Models
            {
                "id": "amazon/nova-pro-v1",
                "name": "Nova Pro v1",
                "description": "Amazon's Nova Pro model",
                "context_length": 200000,
                "pricing": {"prompt": "0.003", "completion": "0.012"},
                "top_provider": {"name": "Amazon"},
                "capabilities": ["chat", "long_context"],
            },
            {
                "id": "amazon/nova-lite-v1",
                "name": "Nova Lite v1",
                "description": "Amazon's Nova Lite model",
                "context_length": 200000,
                "pricing": {"prompt": "0.0002", "completion": "0.0008"},
                "top_provider": {"name": "Amazon"},
                "capabilities": ["chat", "fast", "long_context"],
            },
        ]

    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.

        Args:
            model_id: Model identifier

        Returns:
            Model dictionary or None if not found
        """
        models = await self.fetch_models()
        for model in models:
            if model.get("id") == model_id:
                return model
        return None

    async def auto_route(
        self,
        query: str,
        requirements: Optional[Dict[str, Any]] = None,
        prefer_speed: bool = False,
        max_cost: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Intelligently select a model based on query characteristics.

        Args:
            query: User query text
            requirements: Optional requirements dict (context_length, capabilities, etc.)
            prefer_speed: Prefer faster models
            max_cost: Maximum cost per 1M tokens

        Returns:
            Dictionary with selected_model, reasoning, alternatives, estimated_cost
        """
        requirements = requirements or {}

        # Analyze query characteristics
        query_lower = query.lower()
        query_length = len(query)

        # Determine needed capabilities
        needs_reasoning = any(
            word in query_lower
            for word in [
                "reason",
                "think",
                "analyze",
                "solve",
                "logic",
                "step",
                "why",
                "how",
            ]
        )
        needs_code = any(
            word in query_lower
            for word in [
                "code",
                "program",
                "function",
                "algorithm",
                "python",
                "javascript",
                "sql",
            ]
        )
        needs_long_context = (
            query_length > 10000 or requirements.get("context_length", 0) > 50000
        )

        # Fetch available models
        models = await self.fetch_models()

        # Filter and score models
        candidates = []
        for model in models:
            model_id = model.get("id", "")
            if model_id == "openrouter/auto":
                continue  # Skip auto model itself

            score = 0
            reasoning = []

            # Check pricing
            pricing = model.get("pricing", {})
            prompt_price = float(pricing.get("prompt", "0") or "0")
            completion_price = float(pricing.get("completion", "0") or "0")
            total_price = prompt_price + completion_price

            if max_cost and total_price > max_cost:
                continue  # Skip if too expensive

            # Score based on requirements
            context_length = model.get("context_length", 0)
            if needs_long_context and context_length >= 100000:
                score += 10
                reasoning.append("high context length")
            elif not needs_long_context and context_length >= 8000:
                score += 5

            # Speed preference
            if prefer_speed:
                # Prefer cheaper/faster models
                if total_price < 0.01:
                    score += 5
                    reasoning.append("fast/cheap")
                elif "mini" in model_id or "haiku" in model_id or "flash" in model_id:
                    score += 3
                    reasoning.append("fast model")

            # Reasoning models
            if needs_reasoning:
                if "o1" in model_id or "o3" in model_id or "deepseek-r1" in model_id:
                    score += 15
                    reasoning.append("reasoning model")
                elif "sonnet" in model_id or "opus" in model_id:
                    score += 5
                    reasoning.append("capable model")

            # Code models
            if needs_code:
                if "codestral" in model_id or "coder" in model_id:
                    score += 10
                    reasoning.append("code model")
                elif "gpt-4" in model_id or "claude" in model_id:
                    score += 5
                    reasoning.append("good at code")

            # General quality boost for top models
            if "gpt-4o" in model_id or "claude-3.5" in model_id:
                score += 3
                reasoning.append("high quality")

            if score > 0:
                candidates.append(
                    {
                        "model": model,
                        "score": score,
                        "reasoning": ", ".join(reasoning),
                        "estimated_cost": total_price,
                    }
                )

        # Sort by score (descending)
        candidates.sort(key=lambda x: x["score"], reverse=True)

        if not candidates:
            # Fallback to default
            return {
                "selected_model": "openai/gpt-4o-mini",
                "reasoning": "No suitable model found, using default",
                "alternatives": [],
                "estimated_cost": 0.15,
            }

        selected = candidates[0]
        alternatives = [c["model"]["id"] for c in candidates[1:6]]  # Top 5 alternatives

        return {
            "selected_model": selected["model"]["id"],
            "reasoning": selected["reasoning"],
            "alternatives": alternatives,
            "estimated_cost": selected["estimated_cost"],
        }

    def get_models_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """
        Get all models for a specific provider.

        Args:
            provider: Provider name (claude, gpt, gemini, llama, mistral, cohere, deepseek, grok, nova, router)

        Returns:
            List of models for the provider
        """
        models = self._models if self._models else self._get_default_models()
        provider_models = self._provider_categories.get(provider.lower(), [])

        result = []
        for model in models:
            model_id = model.get("id", "")
            if model_id in provider_models:
                result.append(model)

        return result

    def get_providers(self) -> List[str]:
        """
        Get list of all available providers.

        Returns:
            List of provider names
        """
        return list(self._provider_categories.keys())

    def categorize_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize models by capability.

        Returns:
            Dictionary mapping capability to list of models
        """
        models = self._models if self._models else self._get_default_models()
        categories: Dict[str, List[Dict[str, Any]]] = {
            "chat": [],
            "reasoning": [],
            "vision": [],
            "code": [],
            "fast": [],
            "long_context": [],
        }

        for model in models:
            model_id = model.get("id", "").lower()
            capabilities = model.get("capabilities", [])

            # Use capabilities if available, otherwise infer
            if capabilities:
                for cap in capabilities:
                    if cap in categories:
                        categories[cap].append(model)
            else:
                # Fallback inference
                # Chat models (general purpose)
                if any(
                    x in model_id
                    for x in [
                        "gpt",
                        "claude",
                        "gemini",
                        "llama",
                        "mistral",
                        "cohere",
                        "deepseek",
                        "grok",
                        "nova",
                    ]
                ):
                    categories["chat"].append(model)

                # Reasoning models
                if any(x in model_id for x in ["o1", "o3", "deepseek-r1", "reasoning"]):
                    categories["reasoning"].append(model)

                # Vision models
                if any(
                    x in model_id for x in ["vision", "gpt-4", "gemini", "claude-3"]
                ):
                    categories["vision"].append(model)

                # Code models
                if any(x in model_id for x in ["code", "coder", "codestral"]):
                    categories["code"].append(model)

                # Fast models
                if any(
                    x in model_id
                    for x in ["mini", "haiku", "flash", "turbo", "tiny", "lite"]
                ):
                    categories["fast"].append(model)

                # Long context models
                context_length = model.get("context_length", 0)
                if context_length >= 100000:
                    categories["long_context"].append(model)

        return categories

    def categorize_by_provider(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize models by provider.

        Returns:
            Dictionary mapping provider to list of models
        """
        models = self._models if self._models else self._get_default_models()
        categories: Dict[str, List[Dict[str, Any]]] = {
            provider: [] for provider in self._provider_categories.keys()
        }

        for model in models:
            model_id = model.get("id", "")
            for provider, model_list in self._provider_categories.items():
                if model_id in model_list:
                    categories[provider].append(model)
                    break

        return categories
