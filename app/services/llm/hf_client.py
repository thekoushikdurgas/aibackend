"""
HuggingFace API Client
Base HTTP client wrapper for all HuggingFace APIs
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from enum import Enum

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class HFInferenceProvider(str, Enum):
    """Supported HuggingFace inference providers"""

    HF = "hf"  # HuggingFace native
    CEREBRAS = "cerebras"
    FIREWORKS = "fireworks"
    GROQ = "groq"
    NEBIUS = "nebius"
    NOVITA = "novita"
    SAMBANOVA = "sambanova"
    SCALEWAY = "scaleway"
    TOGETHER = "together"


class HuggingFaceClient:
    """
    Base HTTP client for HuggingFace APIs.
    Supports multiple router endpoints, retry logic, and rate limiting.
    """

    # Provider to router URL mapping
    PROVIDER_ROUTER_MAP = {
        HFInferenceProvider.HF: "hf-inference",
        HFInferenceProvider.CEREBRAS: "cerebras/v1",
        HFInferenceProvider.FIREWORKS: "fireworks-ai/v1",
        HFInferenceProvider.GROQ: "groq/openai/v1",
        HFInferenceProvider.NEBIUS: "nebius/v1",
        HFInferenceProvider.NOVITA: "novita/v3/openai",
        HFInferenceProvider.SAMBANOVA: "sambanova/v1",
        HFInferenceProvider.SCALEWAY: "scaleway/v1",
        HFInferenceProvider.TOGETHER: "together/v1",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize HuggingFace client.

        Args:
            api_key: HuggingFace API key
            base_url: Base URL (defaults to router base URL)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for 503 errors
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.api_key = api_key or settings.huggingface_api_key
        self.base_url = base_url or settings.hf_router_base_url
        self.inference_base_url = settings.hf_inference_base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if not self.api_key:
            logger.warning("HuggingFace API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authorization"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_provider_url(self, provider: Union[str, HFInferenceProvider]) -> str:
        """
        Get router URL for a specific provider.

        Args:
            provider: Provider name or enum

        Returns:
            Provider router path
        """
        if isinstance(provider, str):
            provider = HFInferenceProvider(provider.lower())

        router_path = self.PROVIDER_ROUTER_MAP.get(provider)
        if not router_path:
            raise ValueError(f"Unknown provider: {provider}")

        return f"{self.base_url}/{router_path}"

    async def _handle_model_loading(
        self, response: httpx.Response, retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Handle 503 model loading response with retry logic.

        Args:
            response: HTTP response
            retry_count: Current retry attempt

        Returns:
            Response data if successful, None if should retry
        """
        if response.status_code == 503:
            try:
                data = response.json()
                estimated_time = data.get("estimated_time", 60)

                if retry_count < self.max_retries:
                    wait_time = min(estimated_time, self.retry_delay * (2**retry_count))
                    logger.info(
                        f"Model loading, waiting {wait_time:.1f}s (attempt {retry_count + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    return None  # Signal to retry
                else:
                    raise Exception(
                        f"Model loading timeout after {self.max_retries} retries"
                    )
            except Exception as e:
                raise Exception(f"Model loading error: {str(e)}")

        response.raise_for_status()
        return response.json()

    async def chat_completions(
        self,
        messages: List[Dict[str, str]],
        model: str,
        provider: Union[str, HFInferenceProvider] = HFInferenceProvider.HF,
        max_tokens: int = 500,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Any], httpx.Response]:
        """
        Send chat completion request using OpenAI-compatible format.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B")
            provider: Inference provider
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response
            **kwargs: Additional parameters

        Returns:
            Response dict or streaming response
        """
        provider_url = self._get_provider_url(provider)

        # Build URL based on provider
        if provider == HFInferenceProvider.HF:
            # HF native uses: /models/{model_provider}/{model_id}/v1/chat/completions
            # Model format is typically "provider/model-name", split it
            if "/" in model:
                model_parts = model.split("/", 1)
                model_provider = model_parts[0]
                model_id = model_parts[1]
                url = f"{provider_url}/models/{model_provider}/{model_id}/v1/chat/completions"
            else:
                # Fallback if model doesn't have provider prefix
                url = f"{provider_url}/models/{model}/v1/chat/completions"
        else:
            # Other providers use: /chat/completions
            url = f"{provider_url}/chat/completions"

        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
            **kwargs,
        }

        # Remove model from payload for non-HF providers (they use URL param)
        if provider != HFInferenceProvider.HF:
            payload.pop("model", None)
            if "model" in kwargs:
                payload["model"] = kwargs["model"]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    if stream:
                        response = await client.post(
                            url, json=payload, headers=self._get_headers()
                        )
                        # For streaming, return the response object
                        if response.status_code == 503:
                            data = await self._handle_model_loading(response, attempt)
                            if data is None:
                                continue
                        response.raise_for_status()
                        return response
                    else:
                        response = await client.post(
                            url, json=payload, headers=self._get_headers()
                        )
                        data = await self._handle_model_loading(response, attempt)
                        if data is None:
                            continue
                        return data

                except httpx.HTTPError as e:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2**attempt)
                        logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

    async def inference_api(
        self,
        model: str,
        inputs: Any,
        parameters: Optional[Dict[str, Any]] = None,
        use_router: bool = False,
    ) -> Dict[str, Any]:
        """
        Send request to legacy Inference API.

        Args:
            model: Model identifier
            inputs: Input data (text, image URL, etc.)
            parameters: Generation parameters
            use_router: Whether to use router endpoint

        Returns:
            Response data
        """
        if use_router:
            url = f"{self.base_url}/hf-inference/models/{model}"
        else:
            url = f"{self.inference_base_url}/models/{model}"

        payload = {"inputs": inputs}
        if parameters:
            payload["parameters"] = parameters

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(
                        url, json=payload, headers=self._get_headers()
                    )
                    data = await self._handle_model_loading(response, attempt)
                    if data is None:
                        continue
                    return data

                except httpx.HTTPError as e:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2**attempt)
                        logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

    async def inference_api_binary(
        self,
        model: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        use_router: bool = False,
    ) -> bytes:
        """
        Send binary data to Inference API (for audio/image processing).

        Args:
            model: Model identifier
            data: Binary data
            content_type: Content type header
            use_router: Whether to use router endpoint

        Returns:
            Binary response data
        """
        if use_router:
            url = f"{self.base_url}/hf-inference/models/{model}"
        else:
            url = f"{self.inference_base_url}/models/{model}"

        headers = self._get_headers()
        headers["Content-Type"] = content_type

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(url, content=data, headers=headers)
                    if response.status_code == 503:
                        data_json = response.json()
                        estimated_time = data_json.get("estimated_time", 60)
                        if attempt < self.max_retries:
                            wait_time = min(
                                estimated_time, self.retry_delay * (2**attempt)
                            )
                            logger.info(f"Model loading, waiting {wait_time:.1f}s")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise Exception("Model loading timeout")

                    response.raise_for_status()
                    return response.content

                except httpx.HTTPError as e:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2**attempt)
                        logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

    async def inference_api_formdata(
        self, model: str, files: Dict[str, Any], use_router: bool = False
    ) -> Dict[str, Any]:
        """
        Send form-data to Inference API (for file uploads).

        Args:
            model: Model identifier
            files: Dictionary of file data
            use_router: Whether to use router endpoint

        Returns:
            Response data
        """
        if use_router:
            url = f"{self.base_url}/hf-inference/models/{model}"
        else:
            url = f"{self.inference_base_url}/models/{model}"

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(url, files=files, headers=headers)
                    data = await self._handle_model_loading(response, attempt)
                    if data is None:
                        continue
                    return data

                except httpx.HTTPError as e:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2**attempt)
                        logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

    async def inference_api_file(
        self,
        model: str,
        file_data: bytes,
        filename: str = "image.jpg",
        content_type: str = "image/jpeg",
        use_router: bool = False,
    ) -> Dict[str, Any]:
        """
        Upload a file (image/binary) to Inference API for processing.
        Used for object detection and other file-based tasks.

        Args:
            model: Model identifier
            file_data: Binary file data
            filename: Name of the file
            content_type: MIME type of the file
            use_router: Whether to use router endpoint

        Returns:
            Response data (typically detection results)
        """
        if use_router:
            url = f"{self.base_url}/hf-inference/models/{model}"
        else:
            url = f"{self.inference_base_url}/models/{model}"

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Create file upload
        files = {"data-binary": (filename, file_data, content_type)}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(url, files=files, headers=headers)
                    data = await self._handle_model_loading(response, attempt)
                    if data is None:
                        continue
                    return data

                except httpx.HTTPError as e:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2**attempt)
                        logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

    async def gradio_predict(
        self, space_url: str, data: List[Any], api_key: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Send prediction request to Gradio Space.

        Args:
            space_url: Base URL of the Gradio Space (e.g., "https://bstraehle-rag.hf.space")
            data: List of input data matching the Space's input interface
            api_key: Optional API key (for spaces that require auth)

        Returns:
            Dictionary with event_id for polling
        """
        url = f"{space_url}/gradio_api/call/predict"

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {"data": data}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Gradio predict request failed: {e}")
                raise

    async def gradio_poll(
        self,
        space_url: str,
        event_id: str,
        api_key: Optional[str] = None,
        max_attempts: int = 30,
        initial_delay: float = 0.5,
    ) -> Any:
        """
        Poll Gradio Space for prediction results.
        Uses exponential backoff polling.

        Args:
            space_url: Base URL of the Gradio Space
            event_id: Event ID from gradio_predict response
            api_key: Optional API key
            max_attempts: Maximum polling attempts
            initial_delay: Initial delay between polls (exponential backoff)

        Returns:
            Parsed result from the Gradio Space
        """
        url = f"{space_url}/gradio_api/call/predict/{event_id}"

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            delay = initial_delay
            for attempt in range(max_attempts):
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()

                    # Parse SSE stream
                    content_type = response.headers.get("Content-Type", "")
                    if "text/event-stream" in content_type:
                        result = await self._parse_gradio_stream(response)
                        if result is not None:
                            return result

                    # If not SSE, might be JSON
                    try:
                        return response.json()
                    except Exception:
                        pass

                    # Wait before next poll
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 4.0)  # Cap at 4 seconds

                except httpx.HTTPError as e:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, 4.0)
                        continue
                    logger.error(
                        f"Gradio poll failed after {max_attempts} attempts: {e}"
                    )
                    raise

        raise TimeoutError(f"Gradio polling timeout after {max_attempts} attempts")

    async def _parse_gradio_stream(self, response: httpx.Response) -> Optional[Any]:
        """
        Parse Server-Sent Events (SSE) stream from Gradio Space.

        Args:
            response: HTTP response with SSE stream

        Returns:
            Parsed result or None if not complete
        """
        import json

        event_type = None
        event_data = None

        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:].strip()
                try:
                    # Gradio returns data as JSON array string
                    if data_str.startswith("[") and data_str.endswith("]"):
                        event_data = json.loads(data_str)
                    else:
                        event_data = json.loads(data_str)
                except json.JSONDecodeError:
                    # Try to parse as plain string
                    event_data = data_str

            # Check if we have a complete event
            if event_type == "complete" and event_data is not None:
                # Extract result from data array
                if isinstance(event_data, list) and len(event_data) > 0:
                    return event_data[0]  # First element is usually the result
                return event_data

        return None
