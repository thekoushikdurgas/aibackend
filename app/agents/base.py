"""
Base Agent class for all AI agents
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.helpers import utc_now
from app.services.llm import BaseLLMProvider, LLMConfig, get_llm_provider
from app.models.schemas import PageData

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from an agent"""

    agent_type: str
    analysis: Dict[str, Any]
    summary: str
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)
    success: bool = True
    error: Optional[str] = None


@dataclass
class AgentConfig:
    """Configuration for agent execution"""

    llm_provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.3  # Lower temp for more consistent analysis
    max_tokens: int = 2048
    include_raw_data: bool = False
    timeout: float = 60.0


class BaseAgent(ABC):
    """
    Abstract base class for AI agents.
    All agents must implement the analyze method.
    """

    agent_type: str = "base"
    description: str = "Base agent"

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the agent.

        Args:
            config: Agent configuration
        """
        self.config = config or AgentConfig()
        self._llm_provider: Optional[BaseLLMProvider] = None

    @property
    def llm(self) -> BaseLLMProvider:
        """Get LLM provider (lazy initialization)"""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider(self.config.llm_provider)
        return self._llm_provider

    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration for this agent"""
        return LLMConfig(
            model=self.config.model or "llama3",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            system_prompt=self.get_system_prompt(),
        )

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Each agent should have a specialized prompt.
        """
        pass

    @abstractmethod
    async def analyze(
        self,
        page_data: PageData,
        query: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Analyze page data and return results.

        Args:
            page_data: Page data from the extension
            query: Optional specific query/question
            options: Additional options for analysis

        Returns:
            AgentResponse with analysis results
        """
        pass

    def _prepare_page_context(self, page_data: PageData) -> str:
        """
        Prepare page context for LLM consumption.
        Truncates and formats data appropriately.
        """
        context_parts = []

        # Basic info
        context_parts.append(f"URL: {page_data.url}")
        if page_data.title:
            context_parts.append(f"Title: {page_data.title}")
        if page_data.domain:
            context_parts.append(f"Domain: {page_data.domain}")

        # Meta tags (limited)
        if page_data.meta:
            meta_items = []
            for meta in page_data.meta[:10]:  # Limit to 10 meta tags
                if meta.get("name") and meta.get("content"):
                    meta_items.append(f"- {meta['name']}: {meta['content'][:100]}")
            if meta_items:
                context_parts.append("Meta Tags:\n" + "\n".join(meta_items))

        # Structure stats
        if page_data.structure:
            structure = page_data.structure
            stats = [
                f"Elements: {structure.get('totalElements', 'N/A')}",
                f"Links: {structure.get('links', 'N/A')}",
                f"Images: {structure.get('images', 'N/A')}",
                f"Forms: {structure.get('forms', 'N/A')}",
            ]
            context_parts.append(f"Structure: {', '.join(stats)}")

        # Semantic elements
        if page_data.semantic:
            sem = page_data.semantic
            semantic_info = []
            if sem.get("header"):
                semantic_info.append("header")
            if sem.get("nav"):
                semantic_info.append("nav")
            if sem.get("main"):
                semantic_info.append("main")
            if sem.get("footer"):
                semantic_info.append("footer")
            if semantic_info:
                context_parts.append(f"Semantic Elements: {', '.join(semantic_info)}")

        return "\n".join(context_parts)

    def _truncate_html(self, html: str, max_length: int = 10000) -> str:
        """Truncate HTML while trying to preserve structure"""
        if not html or len(html) <= max_length:
            return html or ""

        # Simple truncation with ellipsis
        return html[:max_length] + "... [truncated]"

    async def _call_llm(self, prompt: str, context: Optional[str] = None) -> str:
        """
        Call the LLM with the given prompt.

        Args:
            prompt: The analysis prompt
            context: Optional page context

        Returns:
            LLM response text
        """
        try:
            response = await self.llm.generate(
                prompt=prompt, config=self.get_llm_config(), context=context
            )
            return response.text
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        Try to parse JSON from LLM response.
        Handles various formats including markdown code blocks.
        """
        import json
        import re

        # Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Return as plain text result
        return {"raw_response": text}
