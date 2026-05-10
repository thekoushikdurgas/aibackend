"""
Research Agent - Summarization and research capabilities
"""

import logging
from typing import Any, Dict, List, Optional

from app.models.schemas import PageData
from app.utils.html_parser import HTMLParser
from app.utils.helpers import extract_keywords, calculate_reading_time
from .base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """
    Agent specialized in content summarization and research.
    Can summarize pages, answer questions, and provide insights.
    """

    agent_type = "research"
    description = "Content summarization, Q&A, and research insights"

    def get_system_prompt(self) -> str:
        return """You are a research assistant specialized in analyzing web content. Your capabilities include:

1. Summarization: Create concise summaries of web page content
2. Q&A: Answer specific questions about the page content
3. Key Points: Extract main ideas and takeaways
4. Insights: Provide analytical insights about the content
5. Context: Understand the broader context and significance

Be accurate, concise, and helpful. Base your analysis only on the provided content.
Format response as JSON:
{
    "summary": "concise summary (2-3 sentences)",
    "key_points": ["list of main points"],
    "topics": ["main topics covered"],
    "insights": ["analytical observations"],
    "answer": "answer to specific question if asked",
    "confidence": 0-100,
    "content_quality": {
        "depth": "shallow|moderate|deep",
        "clarity": "poor|fair|good|excellent",
        "completeness": "incomplete|partial|complete"
    }
}"""

    async def analyze(
        self,
        page_data: PageData,
        query: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Research and summarize page content.
        """
        options = options or {}
        task_type = options.get("task", "summarize")  # summarize, qa, insights

        try:
            # Extract text content
            text_content = ""
            title = page_data.title

            if page_data.html or page_data.body_html:
                html_content = (page_data.html or page_data.body_html) or ""
                try:
                    parser = HTMLParser(html_content)
                    text_content = parser.get_text_content(max_length=8000)
                    title = title or parser.get_title()
                except Exception as e:
                    logger.warning(f"HTML parsing failed: {e}")

            if not text_content:
                return AgentResponse(
                    agent_type=self.agent_type,
                    analysis={
                        "url": page_data.url,
                        "message": "No content available to analyze",
                    },
                    summary="Unable to extract content from this page.",
                    success=False,
                    error="No content available",
                )

            # Extract basic metrics
            word_count = len(text_content.split())
            reading_time = calculate_reading_time(text_content)
            keywords = extract_keywords(text_content, max_keywords=10)

            # Prepare context
            context = self._prepare_research_context(
                page_data, word_count, reading_time
            )

            title_str = title or ""

            # Build research prompt based on task
            prompt = self._build_research_prompt(
                text_content, title_str, query, task_type, keywords
            )

            # Call LLM for research
            llm_response = await self._call_llm(prompt, context)

            # Parse response
            research_data = self._parse_json_response(llm_response)

            # Combine results
            analysis = {
                "url": page_data.url,
                "title": title,
                "word_count": word_count,
                "reading_time_minutes": reading_time,
                "extracted_keywords": keywords,
                "research_results": research_data,
                "task_type": task_type,
            }

            # Build summary based on task type
            if task_type == "qa" and query:
                summary = research_data.get("answer", research_data.get("summary", ""))
            else:
                summary = research_data.get("summary", "")

            if not summary:
                summary = f"Analyzed page with {word_count} words. Main topics: {', '.join(keywords[:5])}"

            # Get key points as recommendations
            key_points = research_data.get("key_points", [])
            insights = research_data.get("insights", [])

            return AgentResponse(
                agent_type=self.agent_type,
                analysis=analysis,
                summary=(
                    summary[:500] if isinstance(summary, str) else str(summary)[:500]
                ),
                recommendations=key_points[:5] + insights[:5],
                metadata={
                    "word_count": word_count,
                    "reading_time_minutes": reading_time,
                    "topics": research_data.get("topics", keywords[:5]),
                    "confidence": research_data.get("confidence", 0),
                    "content_quality": research_data.get("content_quality", {}),
                    "task_type": task_type,
                },
            )

        except Exception as e:
            logger.error(f"Research analysis failed: {e}")
            return AgentResponse(
                agent_type=self.agent_type,
                analysis={"error": str(e)},
                summary=f"Research analysis failed: {str(e)}",
                success=False,
                error=str(e),
            )

    def _prepare_research_context(
        self, page_data: PageData, word_count: int, reading_time: float
    ) -> str:
        """Prepare context for research"""
        return f"""Source: {page_data.url}
Domain: {page_data.domain or 'Unknown'}
Content Length: {word_count} words
Estimated Reading Time: {reading_time} minutes"""

    def _build_research_prompt(
        self,
        text_content: str,
        title: str,
        query: Optional[str],
        task_type: str,
        keywords: List[str],
    ) -> str:
        """Build research prompt based on task type"""
        prompt_parts = []

        # Add task-specific instruction
        if task_type == "qa" and query:
            prompt_parts.append(f"Answer this question about the web page: {query}\n")
        elif task_type == "insights":
            prompt_parts.append("Provide analytical insights about this content:\n")
        else:
            prompt_parts.append("Summarize and analyze this web page content:\n")

        # Add title
        if title:
            prompt_parts.append(f"Title: {title}\n")

        # Add keywords
        if keywords:
            prompt_parts.append(f"Key Terms: {', '.join(keywords[:10])}\n")

        # Add content
        prompt_parts.append("Content:\n")
        prompt_parts.append(text_content[:6000])  # Limit content length

        if len(text_content) > 6000:
            prompt_parts.append("\n... [content truncated]")

        return "\n".join(prompt_parts)
