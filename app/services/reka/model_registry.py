"""
Reka AI Model Registry
Intelligent model management and caching
"""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class RekaModelRegistry:
    """
    Registry for managing Reka AI models with caching.
    Caches model information and provides model selection.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize model registry.

        Args:
            api_key: Reka AI API key
            base_url: Reka AI API base URL
        """
        self.api_key = api_key or settings.reka_api_key
        self.base_url = base_url or settings.reka_base_url

        # Cache for model list
        self._models: List[Dict[str, Any]] = []
        self._cache_time: float = 0
        self._cache_ttl: float = 3600  # 1 hour cache

        # Model categorization by type
        self._model_categories: Dict[str, List[str]] = {
            "core": [
                "reka-core",
                "reka-core-20240415",
                "reka-core-20240501",
                "reka-core-20240722",
                "reka-core-20240904",
            ],
            "flash": [
                "reka-flash",
                "reka-flash-20240226",
                "reka-flash-20240722",
                "reka-flash-preview-20240611",
                "reka-flash-20240904",
                "reka-flash-3",
            ],
            "edge": ["reka-edge", "reka-edge-20240208"],
        }

        # Model capabilities mapping
        self._capability_map: Dict[str, List[str]] = {
            "chat": ["reka-core", "reka-flash", "reka-flash-3", "reka-edge"],
            "reasoning": ["reka-flash-3"],  # flash-3 includes reasoning tags
            "fast": ["reka-edge", "reka-flash"],
            "balanced": ["reka-flash", "reka-flash-3"],
            "powerful": ["reka-core"],
        }

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        return headers

    async def fetch_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch model list from Reka AI API.

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
            logger.warning("Reka AI API key not configured, using default models")
            return self._get_default_models()

        try:
            url = f"{self.base_url}/models"
            headers = self._build_headers()

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Reka API returns array of objects with "id" field
                # Convert to our format
                models = []
                for item in data:
                    model_id = item.get("id", "")
                    models.append(
                        {
                            "id": model_id,
                            "name": model_id,
                            "description": self._get_model_description(model_id),
                            "capabilities": self._get_model_capabilities(model_id),
                            "category": self._get_model_category(model_id),
                        }
                    )

                # Cache the models
                self._models = models
                self._cache_time = current_time

                logger.info(f"Fetched {len(self._models)} models from Reka AI")
                return self._models

        except Exception as e:
            logger.error(f"Failed to fetch Reka AI models: {e}")
            if self._models:
                # Return cached models if available
                logger.warning("Using cached model list")
                return self._models
            return self._get_default_models()

    def _get_default_models(self) -> List[Dict[str, Any]]:
        """Get default model list when API is unavailable"""
        return [
            {
                "id": "reka-core",
                "name": "Reka Core",
                "description": "Reka's most capable model for complex tasks",
                "capabilities": ["chat", "powerful"],
                "category": "core",
            },
            {
                "id": "reka-flash-3",
                "name": "Reka Flash 3",
                "description": "Fast model with reasoning capabilities",
                "capabilities": ["chat", "reasoning", "balanced"],
                "category": "flash",
            },
            {
                "id": "reka-flash",
                "name": "Reka Flash",
                "description": "Balanced performance model",
                "capabilities": ["chat", "fast", "balanced"],
                "category": "flash",
            },
            {
                "id": "reka-edge",
                "name": "Reka Edge",
                "description": "Fastest model for quick responses",
                "capabilities": ["chat", "fast"],
                "category": "edge",
            },
        ]

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model"""
        if "core" in model_id:
            return "Reka's most capable model for complex tasks"
        elif "flash-3" in model_id:
            return "Fast model with reasoning capabilities"
        elif "flash" in model_id:
            return "Balanced performance model"
        elif "edge" in model_id:
            return "Fastest model for quick responses"
        return "Reka AI model"

    def _get_model_capabilities(self, model_id: str) -> List[str]:
        """Get capabilities for a model"""
        capabilities = []
        for cap, models in self._capability_map.items():
            if any(m in model_id for m in models):
                capabilities.append(cap)
        if not capabilities:
            capabilities = ["chat"]
        return capabilities

    def _get_model_category(self, model_id: str) -> str:
        """Get category for a model"""
        for category, models in self._model_categories.items():
            if any(m in model_id for m in models):
                return category
        return "unknown"

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

    def get_models_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all models for a specific category.

        Args:
            category: Category name (core, flash, edge)

        Returns:
            List of models for the category
        """
        models = self._models if self._models else self._get_default_models()
        category_models = self._model_categories.get(category.lower(), [])

        result = []
        for model in models:
            model_id = model.get("id", "")
            if model_id in category_models:
                result.append(model)

        return result

    def get_models_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Get all models with a specific capability.

        Args:
            capability: Capability name (chat, reasoning, fast, balanced, powerful)

        Returns:
            List of models with the capability
        """
        models = self._models if self._models else self._get_default_models()
        capability_models = self._capability_map.get(capability.lower(), [])

        result = []
        for model in models:
            model_id = model.get("id", "")
            if any(m in model_id for m in capability_models):
                result.append(model)

        return result

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
            "fast": [],
            "balanced": [],
            "powerful": [],
        }

        for model in models:
            capabilities = model.get("capabilities", [])
            for cap in capabilities:
                if cap in categories:
                    categories[cap].append(model)

        return categories

    def categorize_by_type(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize models by type.

        Returns:
            Dictionary mapping type to list of models
        """
        models = self._models if self._models else self._get_default_models()
        categories: Dict[str, List[Dict[str, Any]]] = {
            "core": [],
            "flash": [],
            "edge": [],
        }

        for model in models:
            category = model.get("category", "unknown")
            if category in categories:
                categories[category].append(model)

        return categories
