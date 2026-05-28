"""
Agent Router - Routes requests to appropriate agents
"""

import logging
from typing import Any, Dict, Optional, Type

from app.models.schemas import AgentType, PageData
from .base import BaseAgent, AgentResponse, AgentConfig
from .page_analyzer import PageAnalyzerAgent
from .content_extractor import ContentExtractorAgent
from .seo_agent import SEOAgent
from .image_analyzer import ImageAnalyzerAgent
from .research_agent import ResearchAgent
from .council_agent import CouncilAgent
from .website_scraper import WebsiteScraperAgent

logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Routes requests to the appropriate agent based on type.
    Also supports automatic agent selection based on query.
    """

    # Registry of available agents
    _agents: Dict[AgentType, Type[BaseAgent]] = {
        AgentType.PAGE_ANALYZER: PageAnalyzerAgent,
        AgentType.CONTENT_EXTRACTOR: ContentExtractorAgent,
        AgentType.SEO: SEOAgent,
        AgentType.IMAGE_ANALYZER: ImageAnalyzerAgent,
        AgentType.RESEARCH: ResearchAgent,
        AgentType.COUNCIL: CouncilAgent,
        AgentType.WEBSITE_SCRAPER: WebsiteScraperAgent,
    }

    # Cache of agent instances
    _instances: Dict[str, BaseAgent] = {}

    @classmethod
    def get_agent(
        cls, agent_type: AgentType, config: Optional[AgentConfig] = None
    ) -> BaseAgent:
        """
        Get or create an agent instance.

        Args:
            agent_type: Type of agent to get
            config: Optional agent configuration

        Returns:
            Agent instance
        """
        # Get agent class
        if agent_type not in cls._agents:
            available = ", ".join(t.value for t in cls._agents.keys())
            raise ValueError(
                f"Unknown agent type: {agent_type}. Available: {available}"
            )

        agent_class = cls._agents[agent_type]

        # Create cache key
        cache_key = f"{agent_type.value}_{id(config)}"

        # Return cached instance if available and config matches
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        # Create new instance
        instance = agent_class(config)
        cls._instances[cache_key] = instance

        logger.debug(f"Created agent instance: {agent_type.value}")
        return instance

    @classmethod
    async def route(
        cls,
        agent_type: AgentType,
        page_data: PageData,
        query: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        config: Optional[AgentConfig] = None,
    ) -> AgentResponse:
        """
        Route a request to the appropriate agent.

        Args:
            agent_type: Type of agent to use
            page_data: Page data to analyze
            query: Optional query/question
            options: Additional options
            config: Agent configuration

        Returns:
            AgentResponse from the agent
        """
        agent = cls.get_agent(agent_type, config)
        return await agent.analyze(page_data, query, options)

    @classmethod
    async def auto_route(
        cls, query: str, page_data: PageData, options: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Automatically select and route to the best agent based on query.

        Args:
            query: User's query/question
            page_data: Page data to analyze
            options: Additional options

        Returns:
            AgentResponse from the selected agent
        """
        # Determine best agent based on query keywords
        agent_type = cls._detect_agent_type(query)

        logger.info(
            f"Auto-selected agent: {agent_type.value} for query: {query[:50]}..."
        )

        return await cls.route(agent_type, page_data, query, options)

    @classmethod
    def _detect_agent_type(cls, query: str) -> AgentType:
        """
        Detect the best agent type based on query content.
        """
        query_lower = query.lower()

        # SEO keywords
        seo_keywords = [
            "seo",
            "search engine",
            "ranking",
            "meta",
            "title tag",
            "keywords",
            "optimization",
            "google",
        ]
        if any(kw in query_lower for kw in seo_keywords):
            return AgentType.SEO

        # Image keywords
        image_keywords = [
            "image",
            "images",
            "photo",
            "picture",
            "alt text",
            "thumbnail",
            "visual",
        ]
        if any(kw in query_lower for kw in image_keywords):
            return AgentType.IMAGE_ANALYZER

        # Content extraction keywords
        extract_keywords = [
            "extract",
            "find",
            "get",
            "what is",
            "contact",
            "email",
            "phone",
            "price",
            "product",
            "data",
        ]
        if any(kw in query_lower for kw in extract_keywords):
            return AgentType.CONTENT_EXTRACTOR

        # Structure keywords
        structure_keywords = [
            "structure",
            "html",
            "dom",
            "element",
            "layout",
            "semantic",
            "accessibility",
            "component",
        ]
        if any(kw in query_lower for kw in structure_keywords):
            return AgentType.PAGE_ANALYZER

        # Council keywords (multi-model, consensus, verify, compare)
        council_keywords = [
            "compare",
            "verify",
            "multiple perspectives",
            "council",
            "consensus",
            "cross-check",
            "validate",
            "peer review",
        ]
        if any(kw in query_lower for kw in council_keywords):
            return AgentType.COUNCIL

        # Default to research for general questions
        return AgentType.RESEARCH

    @classmethod
    def list_agents(cls) -> Dict[str, str]:
        """List all available agents with descriptions"""
        return {
            agent_type.value: cls._agents[agent_type](None).description
            for agent_type in cls._agents.keys()
        }

    @classmethod
    def clear_cache(cls):
        """Clear agent instance cache"""
        cls._instances.clear()
        logger.info("Cleared agent cache")
