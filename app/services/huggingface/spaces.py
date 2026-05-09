"""
Gradio Spaces Service
Handles async interactions with HuggingFace Gradio Spaces for RAG and Agentic AI
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.llm.hf_client import HuggingFaceClient

logger = logging.getLogger(__name__)


class GradioSpacesClient:
    """
    Base client for interacting with HuggingFace Gradio Spaces.
    Handles async prediction and polling patterns.
    """

    def __init__(self, api_key: Optional[str] = None, timeout: float = 300.0):
        """
        Initialize Gradio Spaces client.

        Args:
            api_key: Optional API key for authenticated spaces
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.client = HuggingFaceClient(api_key=api_key, timeout=timeout)

    async def predict(
        self, space_url: str, data: List[Any], api_key: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Send prediction request to Gradio Space.

        Args:
            space_url: Base URL of the Gradio Space
            data: List of input data matching the Space's interface
            api_key: Optional API key (overrides instance key)

        Returns:
            Dictionary with event_id for polling
        """
        key = api_key or self.api_key
        return await self.client.gradio_predict(space_url, data, key)

    async def poll(
        self,
        space_url: str,
        event_id: str,
        api_key: Optional[str] = None,
        max_attempts: int = 30,
        initial_delay: float = 0.5,
    ) -> Any:
        """
        Poll Gradio Space for prediction results.

        Args:
            space_url: Base URL of the Gradio Space
            event_id: Event ID from predict response
            api_key: Optional API key
            max_attempts: Maximum polling attempts
            initial_delay: Initial delay between polls

        Returns:
            Parsed result from the Gradio Space
        """
        key = api_key or self.api_key
        return await self.client.gradio_poll(
            space_url, event_id, key, max_attempts, initial_delay
        )

    async def predict_and_wait(
        self,
        space_url: str,
        data: List[Any],
        api_key: Optional[str] = None,
        max_attempts: int = 30,
        initial_delay: float = 0.5,
    ) -> Any:
        """
        Send prediction and wait for result (convenience method).

        Args:
            space_url: Base URL of the Gradio Space
            data: List of input data
            api_key: Optional API key
            max_attempts: Maximum polling attempts
            initial_delay: Initial delay between polls

        Returns:
            Final result from the Gradio Space
        """
        response = await self.predict(space_url, data, api_key)
        event_id = response.get("event_id")
        if not event_id:
            raise ValueError("No event_id in predict response")

        return await self.poll(
            space_url, event_id, api_key, max_attempts, initial_delay
        )


class RAGService:
    """
    Service for RAG (Retrieval-Augmented Generation) Gradio Spaces.
    Supports naive, advanced, and agentic RAG patterns.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        naive_rag_url: Optional[str] = None,
        advanced_rag_url: Optional[str] = None,
        timeout: float = 300.0,
    ):
        """
        Initialize RAG service.

        Args:
            api_key: Optional API key (for OpenAI-based spaces)
            naive_rag_url: URL for naive RAG space
            advanced_rag_url: URL for advanced RAG space
            timeout: Request timeout
        """
        self.api_key = api_key
        self.naive_rag_url = naive_rag_url or settings.hf_spaces_naive_rag
        self.advanced_rag_url = advanced_rag_url or settings.hf_spaces_advanced_rag
        self.client = GradioSpacesClient(api_key=api_key, timeout=timeout)

    async def naive_rag_predict(
        self, question: str, framework: str = "LangChain", api_key: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Send question to naive RAG space.

        Args:
            question: Question to answer
            framework: Framework to use (e.g., "LangChain")
            api_key: Optional API key (for OpenAI-based spaces)

        Returns:
            Dictionary with event_id
        """
        data = [api_key or self.api_key or "", question, framework]
        return await self.client.predict(self.naive_rag_url, data, api_key)

    async def naive_rag_poll(self, event_id: str, api_key: Optional[str] = None) -> str:
        """
        Poll naive RAG space for results.

        Args:
            event_id: Event ID from predict
            api_key: Optional API key

        Returns:
            Answer text
        """
        result = await self.client.poll(self.naive_rag_url, event_id, api_key)
        # Result is typically a JSON string in a list
        if isinstance(result, list) and len(result) > 0:
            result_str = result[0]
            if isinstance(result_str, str):
                try:
                    # Try to parse as JSON
                    parsed = json.loads(result_str)
                    if isinstance(parsed, dict):
                        return json.dumps(parsed, indent=2)
                    return str(parsed)
                except Exception:
                    return result_str
            return str(result_str)
        return str(result)

    async def naive_rag(
        self, question: str, framework: str = "LangChain", api_key: Optional[str] = None
    ) -> str:
        """
        Complete naive RAG workflow (predict + poll).

        Args:
            question: Question to answer
            framework: Framework to use
            api_key: Optional API key

        Returns:
            Answer text
        """
        response = await self.naive_rag_predict(question, framework, api_key)
        event_id = response.get("event_id")
        if not event_id:
            raise ValueError("No event_id in response")
        return await self.naive_rag_poll(event_id, api_key)

    async def advanced_rag_predict(
        self,
        question: str,
        num_results: int = 2,
        rerank: int = 1,
        rag_type: str = "Advanced RAG",
        api_key: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Send question to advanced RAG space (recommendation system).

        Args:
            question: Question or recommendation request
            num_results: Number of results to return
            rerank: Reranking parameter
            rag_type: Type of RAG ("Advanced RAG")
            api_key: Optional API key

        Returns:
            Dictionary with event_id
        """
        data = [api_key or self.api_key or "", question, num_results, rerank, rag_type]
        return await self.client.predict(self.advanced_rag_url, data, api_key)

    async def advanced_rag_poll(
        self, event_id: str, api_key: Optional[str] = None
    ) -> Any:
        """
        Poll advanced RAG space for results.

        Args:
            event_id: Event ID from predict
            api_key: Optional API key

        Returns:
            Recommendation results
        """
        return await self.client.poll(self.advanced_rag_url, event_id, api_key)

    async def advanced_rag(
        self,
        question: str,
        num_results: int = 2,
        rerank: int = 1,
        rag_type: str = "Advanced RAG",
        api_key: Optional[str] = None,
    ) -> Any:
        """
        Complete advanced RAG workflow (predict + poll).

        Args:
            question: Question or recommendation request
            num_results: Number of results
            rerank: Reranking parameter
            rag_type: Type of RAG
            api_key: Optional API key

        Returns:
            Recommendation results
        """
        response = await self.advanced_rag_predict(
            question, num_results, rerank, rag_type, api_key
        )
        event_id = response.get("event_id")
        if not event_id:
            raise ValueError("No event_id in response")
        return await self.advanced_rag_poll(event_id, api_key)


class AgenticAIService:
    """
    Service for Agentic AI Gradio Spaces.
    Supports crewAI, LangGraph, and OpenAI Assistants API patterns.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        crewai_url: Optional[str] = None,
        langgraph_url: Optional[str] = None,
        openai_url: Optional[str] = None,
        timeout: float = 600.0,
    ):
        """
        Initialize Agentic AI service.

        Args:
            api_key: Optional API key (for OpenAI-based spaces)
            crewai_url: URL for crewAI space
            langgraph_url: URL for LangGraph space
            openai_url: URL for OpenAI Assistants space
            timeout: Request timeout (longer for agentic tasks)
        """
        self.api_key = api_key
        self.crewai_url = crewai_url or settings.hf_spaces_agentic_crewai
        self.langgraph_url = langgraph_url or settings.hf_spaces_agentic_langgraph
        self.openai_url = openai_url or settings.hf_spaces_agentic_openai
        self.client = GradioSpacesClient(api_key=api_key, timeout=timeout)

    async def agentic_rag_crewai_predict(
        self, question: str, api_key: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Send question to crewAI agentic RAG space.

        Args:
            question: Research question
            api_key: Optional API key

        Returns:
            Dictionary with event_id
        """
        if not self.crewai_url:
            raise ValueError("crewAI URL not configured")

        data = [api_key or self.api_key or "", question]
        return await self.client.predict(self.crewai_url, data, api_key)

    async def agentic_rag_crewai(
        self, question: str, api_key: Optional[str] = None
    ) -> Any:
        """
        Complete crewAI agentic RAG workflow.

        Args:
            question: Research question
            api_key: Optional API key

        Returns:
            Research results
        """
        response = await self.agentic_rag_crewai_predict(question, api_key)
        event_id = response.get("event_id")
        if not event_id:
            raise ValueError("No event_id in response")
        return await self.client.poll(
            self.crewai_url, event_id, api_key, max_attempts=60
        )

    async def agentic_rag_langgraph_predict(
        self, question: str, api_key: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Send question to LangGraph agentic RAG space.

        Args:
            question: Research question
            api_key: Optional API key

        Returns:
            Dictionary with event_id
        """
        if not self.langgraph_url:
            raise ValueError("LangGraph URL not configured")

        data = [api_key or self.api_key or "", question]
        return await self.client.predict(self.langgraph_url, data, api_key)

    async def agentic_rag_langgraph(
        self, question: str, api_key: Optional[str] = None
    ) -> Any:
        """
        Complete LangGraph agentic RAG workflow.

        Args:
            question: Research question
            api_key: Optional API key

        Returns:
            Research results
        """
        response = await self.agentic_rag_langgraph_predict(question, api_key)
        event_id = response.get("event_id")
        if not event_id:
            raise ValueError("No event_id in response")
        return await self.client.poll(
            self.langgraph_url, event_id, api_key, max_attempts=60
        )

    async def agentic_rag_openai_predict(
        self, question: str, api_key: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Send question to OpenAI Assistants agentic RAG space.

        Args:
            question: Research question
            api_key: OpenAI API key (required)

        Returns:
            Dictionary with event_id
        """
        if not self.openai_url:
            raise ValueError("OpenAI Assistants URL not configured")

        if not api_key and not self.api_key:
            raise ValueError("OpenAI API key required")

        data = [api_key or self.api_key, question]
        return await self.client.predict(self.openai_url, data, api_key)

    async def agentic_rag_openai(
        self, question: str, api_key: Optional[str] = None
    ) -> Any:
        """
        Complete OpenAI Assistants agentic RAG workflow.

        Args:
            question: Research question
            api_key: OpenAI API key (required)

        Returns:
            Research results
        """
        response = await self.agentic_rag_openai_predict(question, api_key)
        event_id = response.get("event_id")
        if not event_id:
            raise ValueError("No event_id in response")
        return await self.client.poll(
            self.openai_url, event_id, api_key, max_attempts=60
        )

    async def multi_agent_crewai(self, task: str, api_key: Optional[str] = None) -> Any:
        """
        Multi-agent crewAI system (deep research).

        Args:
            task: Research task
            api_key: Optional API key

        Returns:
            Research results
        """
        return await self.agentic_rag_crewai(task, api_key)

    async def multi_agent_langgraph(
        self, task: str, api_key: Optional[str] = None
    ) -> Any:
        """
        Multi-agent LangGraph system (deep research or chess).

        Args:
            task: Task description
            api_key: Optional API key

        Returns:
            Task results
        """
        return await self.agentic_rag_langgraph(task, api_key)
