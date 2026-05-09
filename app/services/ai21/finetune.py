"""
AI21 Labs Fine-Tuning Service
Provides dataset and custom model management functionality
"""

import logging
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AI21FinetuneService:
    """Service for AI21 Labs Fine-Tuning features"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize AI21 Fine-Tuning service.

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

    # ===================
    # Dataset Operations
    # ===================

    async def list_datasets(self) -> List[Dict]:
        """
        List all datasets.

        Returns:
            List of dataset metadata dictionaries
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/dataset"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()

                return data if isinstance(data, list) else data.get("datasets", [])
        except httpx.HTTPError as e:
            logger.error(f"AI21 list datasets error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 list datasets error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 list datasets error: {str(e)}")

    async def get_dataset(self, dataset_id: str) -> Dict:
        """
        Get dataset details.

        Args:
            dataset_id: ID of the dataset

        Returns:
            Dictionary with dataset metadata
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/dataset/{dataset_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"AI21 get dataset error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 get dataset error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 get dataset error: {str(e)}")

    async def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a dataset.

        Args:
            dataset_id: ID of the dataset to delete

        Returns:
            True if successful
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/dataset/{dataset_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(url, headers=self._get_headers())
                response.raise_for_status()
                return True
        except httpx.HTTPError as e:
            logger.error(f"AI21 delete dataset error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 delete dataset error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 delete dataset error: {str(e)}")

    # ===================
    # Custom Model Operations
    # ===================

    async def create_custom_model(
        self,
        model_type: str,
        dataset_id: str,
        model_name: str,
        learning_rate: float = 0.5,
        num_epochs: int = 20,
    ) -> Dict:
        """
        Create a custom model by training on a dataset.

        Args:
            model_type: Base model type (e.g., "j2-mid")
            dataset_id: ID of the training dataset
            model_name: Name for the custom model
            learning_rate: Learning rate for training
            num_epochs: Number of training epochs

        Returns:
            Dictionary with model training job information
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/custom-model"
        payload = {
            "model_type": model_type,
            "dataset_id": dataset_id,
            "model_name": model_name,
            "learning_rate": learning_rate,
            "num_epochs": num_epochs,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"AI21 create custom model error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 create custom model error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 create custom model error: {str(e)}")

    async def list_custom_models(self) -> List[Dict]:
        """
        List all custom models.

        Returns:
            List of custom model metadata dictionaries
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/custom-model"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()

                return data if isinstance(data, list) else data.get("models", [])
        except httpx.HTTPError as e:
            logger.error(f"AI21 list custom models error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 list custom models error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 list custom models error: {str(e)}")

    async def get_custom_model(self, model_id: str) -> Dict:
        """
        Get custom model details.

        Args:
            model_id: ID of the custom model

        Returns:
            Dictionary with model metadata
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/custom-model/{model_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"AI21 get custom model error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 get custom model error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 get custom model error: {str(e)}")

    async def update_default_epoch(self, model_id: str, default_epoch: int) -> Dict:
        """
        Update the default epoch for a custom model.

        Args:
            model_id: ID of the custom model
            default_epoch: Default epoch number to use

        Returns:
            Updated model information
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/custom-model/{model_id}"
        payload = {"defaultEpoch": default_epoch}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"AI21 update default epoch error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 update default epoch error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 update default epoch error: {str(e)}")

    async def custom_model_complete(
        self,
        model_id: str,
        model_type: str,
        prompt: str,
        num_results: int = 1,
        max_tokens: int = 16,
        min_tokens: int = 0,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop_sequences: Optional[List[str]] = None,
        epoch: Optional[int] = None,
    ) -> Dict:
        """
        Generate completion using a custom model.

        Args:
            model_id: ID of the custom model
            model_type: Base model type (e.g., "j2-mid")
            prompt: Prompt to complete
            num_results: Number of completions
            max_tokens: Maximum tokens
            min_tokens: Minimum tokens
            temperature: Sampling temperature
            top_p: Nucleus sampling
            stop_sequences: Stop sequences
            epoch: Specific epoch to use (optional)

        Returns:
            Dictionary with completions
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/{model_type}/{model_id}/complete"
        payload = {
            "prompt": prompt,
            "numResults": num_results,
            "maxTokens": max_tokens,
            "minTokens": min_tokens,
            "temperature": temperature,
            "topP": top_p,
        }

        if stop_sequences:
            payload["stopSequences"] = stop_sequences

        if epoch is not None:
            payload["epoch"] = epoch

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"AI21 custom model complete error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 custom model complete error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 custom model complete error: {str(e)}")
