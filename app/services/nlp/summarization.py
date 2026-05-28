"""
Summarization Service using HuggingFace Inference API
Supports BART, T5, and other summarization models
"""

import logging
from typing import Optional

from app.config import settings
from app.services.llm.hf_client import HuggingFaceClient

logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for text summarization"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize summarization service.

        Args:
            api_key: HuggingFace API key
            model: Model to use (defaults to config)
        """
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.hf_summarization_model
        self.client = HuggingFaceClient(api_key=self.api_key)

    async def summarize(
        self,
        text: str,
        model: Optional[str] = None,
        max_length: Optional[int] = None,
        min_length: Optional[int] = None,
        do_sample: bool = False,
    ) -> dict:
        """
        Summarize text.

        Args:
            text: Text to summarize
            model: Model to use (overrides default)
            max_length: Maximum length of summary
            min_length: Minimum length of summary
            do_sample: Whether to use sampling

        Returns:
            Dictionary with summary and metadata
        """
        model = model or self.model

        # Build parameters
        parameters = {}
        if max_length:
            parameters["max_length"] = max_length
        if min_length:
            parameters["min_length"] = min_length
        if do_sample:
            parameters["do_sample"] = do_sample

        try:
            # Call inference API
            response = await self.client.inference_api(
                model=model, inputs=text, parameters=parameters if parameters else None
            )

            # Parse response
            summary = ""
            if isinstance(response, list):
                if len(response) > 0:
                    item = response[0]
                    if isinstance(item, dict):
                        summary = item.get("summary_text", "")
                    elif isinstance(item, str):
                        summary = item
            elif isinstance(response, dict):
                summary = response.get("summary_text", response.get("summary", ""))
            elif isinstance(response, str):
                summary = response

            summary_str = summary if isinstance(summary, str) else str(summary or "")

            return {
                "summary": summary_str,
                "model": model,
                "original_length": len(text),
                "summary_length": len(summary_str),
            }

        except Exception as e:
            logger.error(f"Summarization error: {e}")
            raise Exception(f"Failed to summarize text: {str(e)}")
