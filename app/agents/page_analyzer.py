"""
Page Analyzer Agent - Deep page structure analysis
"""

import logging
from typing import Any, Dict, Optional

from app.models.schemas import PageData
from app.utils.html_parser import HTMLParser
from .base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class PageAnalyzerAgent(BaseAgent):
    """
    Agent specialized in deep page structure analysis.
    Analyzes HTML structure, semantic elements, and page organization.
    """

    agent_type = "page_analyzer"
    description = "Deep page structure and organization analysis"

    def get_system_prompt(self) -> str:
        return """You are a web page analysis expert. Your role is to analyze web pages and provide:

1. Structural Analysis: How the page is organized, DOM structure, nesting depth
2. Semantic Assessment: Use of semantic HTML5 elements (header, nav, main, footer, article, section)
3. Accessibility Notes: Potential accessibility issues based on structure
4. Component Identification: Identify main components (hero, navigation, content areas, forms)
5. Quality Assessment: Overall structural quality score and areas for improvement

Provide detailed, actionable insights that help understand the page architecture.
Format your response as JSON with the following structure:
{
    "structure_score": 0-100,
    "semantic_score": 0-100,
    "components": ["list of identified components"],
    "structure_analysis": "detailed analysis",
    "issues": ["list of issues found"],
    "recommendations": ["list of recommendations"]
}"""

    async def analyze(
        self,
        page_data: PageData,
        query: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Analyze page structure and organization.
        """
        options = options or {}

        try:
            # Prepare context
            context = self._prepare_page_context(page_data)

            # Parse HTML if available
            html_analysis = {}
            if page_data.html or page_data.body_html:
                html_content = (page_data.html or page_data.body_html) or ""
                try:
                    parser = HTMLParser(html_content)
                    html_analysis = parser.get_full_analysis()
                except Exception as e:
                    logger.warning(f"HTML parsing failed: {e}")

            # Build analysis prompt
            prompt = self._build_analysis_prompt(page_data, html_analysis, query)

            # Call LLM for analysis
            llm_response = await self._call_llm(prompt, context)

            # Parse response
            analysis_data = self._parse_json_response(llm_response)

            # Build final analysis
            analysis = {
                "url": page_data.url,
                "title": page_data.title,
                "html_analysis": html_analysis,
                "llm_analysis": analysis_data,
                "structure_stats": page_data.structure or {},
                "semantic_elements": page_data.semantic or {},
            }

            # Extract summary and recommendations
            summary = analysis_data.get(
                "structure_analysis",
                f"Page structure analysis completed for {page_data.url}",
            )
            recommendations = analysis_data.get("recommendations", [])

            # Calculate overall scores
            structure_score = analysis_data.get("structure_score", 0)
            semantic_score = analysis_data.get("semantic_score", 0)

            return AgentResponse(
                agent_type=self.agent_type,
                analysis=analysis,
                summary=(
                    summary[:500] if isinstance(summary, str) else str(summary)[:500]
                ),
                recommendations=(
                    recommendations[:10] if isinstance(recommendations, list) else []
                ),
                metadata={
                    "structure_score": structure_score,
                    "semantic_score": semantic_score,
                    "components_found": analysis_data.get("components", []),
                    "issues_count": len(analysis_data.get("issues", [])),
                },
            )

        except Exception as e:
            logger.error(f"Page analysis failed: {e}")
            return AgentResponse(
                agent_type=self.agent_type,
                analysis={"error": str(e)},
                summary=f"Analysis failed: {str(e)}",
                success=False,
                error=str(e),
            )

    def _build_analysis_prompt(
        self, page_data: PageData, html_analysis: Dict[str, Any], query: Optional[str]
    ) -> str:
        """Build the analysis prompt for the LLM"""
        prompt_parts = ["Analyze the following web page structure:\n"]

        # Add URL and title
        prompt_parts.append(f"URL: {page_data.url}")
        if page_data.title:
            prompt_parts.append(f"Title: {page_data.title}")

        # Add structure stats
        if page_data.structure:
            prompt_parts.append("\nStructure Statistics:")
            for key, value in page_data.structure.items():
                if isinstance(value, dict):
                    prompt_parts.append(f"  {key}: {value}")
                else:
                    prompt_parts.append(f"  {key}: {value}")

        # Add semantic info
        if page_data.semantic:
            prompt_parts.append("\nSemantic Elements:")
            for key, value in page_data.semantic.items():
                prompt_parts.append(f"  {key}: {value}")

        # Add HTML analysis results
        if html_analysis:
            prompt_parts.append("\nHTML Analysis:")
            if html_analysis.get("headings"):
                headings = html_analysis["headings"]
                prompt_parts.append(
                    f"  Headings: H1={len(headings.get('h1', []))}, H2={len(headings.get('h2', []))}, H3={len(headings.get('h3', []))}"
                )
            if html_analysis.get("semantic_elements"):
                prompt_parts.append(f"  Semantic: {html_analysis['semantic_elements']}")

        # Add specific query if provided
        if query:
            prompt_parts.append(f"\nSpecific question: {query}")
        else:
            prompt_parts.append("\nProvide a comprehensive structural analysis.")

        return "\n".join(prompt_parts)
