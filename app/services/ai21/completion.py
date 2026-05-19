"""
AI21 Labs Text Completion Service
Provides text completion functionality with support for j2-ultra, j2-mid, j2-light models
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AI21CompletionService:
    """Service for AI21 Labs Text Completion features"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize AI21 Completion service.

        Args:
            api_key: AI21 API key
            base_url: Base URL for AI21 API
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.ai21_api_key
        self.base_url = base_url or settings.ai21_base_url
        self.timeout = timeout

        if not self.api_key:
            logger.warning("AI21 API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def complete(
        self,
        prompt: str,
        model: str = "j2-mid",
        num_results: int = 1,
        max_tokens: int = 16,
        min_tokens: int = 0,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop_sequences: Optional[List[str]] = None,
        top_k_return: int = 0,
        epoch: Optional[int] = None,
        frequency_penalty: Optional[Dict] = None,
        presence_penalty: Optional[Dict] = None,
        count_penalty: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate text completion using AI21 Labs API.

        Args:
            prompt: The prompt to complete
            model: Model to use (j2-ultra, j2-mid, j2-light)
            num_results: Number of completions to generate
            max_tokens: Maximum tokens to generate
            min_tokens: Minimum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            stop_sequences: List of stop sequences
            top_k_return: Top-k sampling
            epoch: Epoch number for custom models
            frequency_penalty: Frequency penalty configuration
            presence_penalty: Presence penalty configuration
            count_penalty: Count penalty configuration

        Returns:
            Dictionary with completions and metadata
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        # Build URL based on model type
        if model.startswith("j2-"):
            url = f"{self.base_url}/{model}/complete"
        else:
            # Default to j2-mid if model format is unexpected
            url = f"{self.base_url}/j2-mid/complete"

        payload: dict[str, Any] = {
            "prompt": prompt,
            "numResults": num_results,
            "maxTokens": max_tokens,
            "minTokens": min_tokens,
            "temperature": temperature,
            "topP": top_p,
        }

        if stop_sequences:
            payload["stopSequences"] = stop_sequences

        if top_k_return > 0:
            payload["topKReturn"] = top_k_return

        if epoch is not None:
            payload["epoch"] = epoch

        # Add penalty configurations
        if frequency_penalty:
            payload["frequencyPenalty"] = frequency_penalty

        if presence_penalty:
            payload["presencePenalty"] = presence_penalty

        if count_penalty:
            payload["countPenalty"] = count_penalty

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "id": data.get("id"),
                    "completions": data.get("completions", []),
                    "prompt": data.get("prompt", {}),
                    "usage": data.get("usage", {}),
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 completion error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 completion error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 completion error: {str(e)}")
