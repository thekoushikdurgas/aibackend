"""
SEO Agent - SEO analysis and recommendations
"""

import logging
from typing import Any, Dict, List, Optional

from app.models.schemas import PageData
from app.utils.html_parser import HTMLParser
from .base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class SEOAgent(BaseAgent):
    """
    Agent specialized in SEO analysis and recommendations.
    Analyzes on-page SEO factors and provides actionable suggestions.
    """

    agent_type = "seo"
    description = "SEO analysis and optimization recommendations"

    def get_system_prompt(self) -> str:
        return """You are an expert SEO analyst. Analyze web pages for SEO optimization:

1. Title Tag Analysis: Length, keyword usage, uniqueness
2. Meta Description: Length, call-to-action, keyword relevance
3. Heading Structure: H1-H6 hierarchy, keyword distribution
4. Content Quality: Keyword density, readability, length
5. Technical SEO: URL structure, internal links, image optimization
6. Mobile & Speed: Mobile-friendliness indicators

Provide specific, actionable SEO recommendations.
Format response as JSON:
{
    "seo_score": 0-100,
    "title_analysis": {
        "score": 0-100,
        "length": 0,
        "issues": [],
        "recommendations": []
    },
    "meta_analysis": {
        "score": 0-100,
        "length": 0,
        "issues": [],
        "recommendations": []
    },
    "heading_analysis": {
        "score": 0-100,
        "h1_count": 0,
        "hierarchy_valid": true/false,
        "issues": [],
        "recommendations": []
    },
    "content_analysis": {
        "score": 0-100,
        "word_count": 0,
        "keyword_density": {},
        "issues": [],
        "recommendations": []
    },
    "image_analysis": {
        "score": 0-100,
        "total_images": 0,
        "missing_alt": 0,
        "issues": [],
        "recommendations": []
    },
    "priority_actions": ["top 5 most important actions"]
}"""

    async def analyze(
        self,
        page_data: PageData,
        query: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Perform comprehensive SEO analysis.
        """
        options = options or {}
        target_keyword = options.get("target_keyword")

        try:
            # Parse HTML and get SEO data
            seo_data = {}
            if page_data.html or page_data.body_html:
                html_content = (page_data.html or page_data.body_html) or ""
                try:
                    parser = HTMLParser(html_content)
                    seo_data = {
                        "title": parser.get_title(),
                        "meta_description": parser.get_meta_description(),
                        "headings": parser.get_headings(),
                        "seo_data": parser.get_seo_data(),
                        "image_analysis": parser.analyze_images_seo(),
                        "word_count": parser.get_word_count(),
                        "links": len(parser.get_links()),
                    }
                except Exception as e:
                    logger.warning(f"HTML parsing failed: {e}")

            # Prepare context
            context = self._prepare_seo_context(page_data, seo_data)

            # Build SEO analysis prompt
            prompt = self._build_seo_prompt(page_data, seo_data, target_keyword, query)

            # Call LLM for analysis
            llm_response = await self._call_llm(prompt, context)

            # Parse response
            seo_analysis = self._parse_json_response(llm_response)

            # Combine results
            analysis = {
                "url": page_data.url,
                "parsed_seo_data": seo_data,
                "llm_analysis": seo_analysis,
            }

            # Calculate overall SEO score
            seo_score = seo_analysis.get(
                "seo_score", self._calculate_seo_score(seo_data, seo_analysis)
            )

            # Build summary
            summary = self._build_seo_summary(seo_score, seo_analysis)

            # Get priority recommendations
            priority_actions = seo_analysis.get("priority_actions", [])
            recommendations = (
                priority_actions
                if priority_actions
                else self._extract_recommendations(seo_analysis)
            )

            return AgentResponse(
                agent_type=self.agent_type,
                analysis=analysis,
                summary=summary,
                recommendations=recommendations[:10],
                metadata={
                    "seo_score": seo_score,
                    "title_score": seo_analysis.get("title_analysis", {}).get(
                        "score", 0
                    ),
                    "meta_score": seo_analysis.get("meta_analysis", {}).get("score", 0),
                    "heading_score": seo_analysis.get("heading_analysis", {}).get(
                        "score", 0
                    ),
                    "content_score": seo_analysis.get("content_analysis", {}).get(
                        "score", 0
                    ),
                    "image_score": seo_analysis.get("image_analysis", {}).get(
                        "score", 0
                    ),
                },
            )

        except Exception as e:
            logger.error(f"SEO analysis failed: {e}")
            return AgentResponse(
                agent_type=self.agent_type,
                analysis={"error": str(e)},
                summary=f"SEO analysis failed: {str(e)}",
                success=False,
                error=str(e),
            )

    def _prepare_seo_context(
        self, page_data: PageData, seo_data: Dict[str, Any]
    ) -> str:
        """Prepare SEO-specific context"""
        context_parts = [
            f"URL: {page_data.url}",
            f"Domain: {page_data.domain or 'Unknown'}",
        ]

        if seo_data.get("title"):
            context_parts.append(
                f"Title ({len(seo_data['title'])} chars): {seo_data['title']}"
            )

        if seo_data.get("meta_description"):
            desc = seo_data["meta_description"]
            context_parts.append(f"Meta Description ({len(desc)} chars): {desc[:160]}")

        if seo_data.get("word_count"):
            context_parts.append(f"Word Count: {seo_data['word_count']}")

        return "\n".join(context_parts)

    def _build_seo_prompt(
        self,
        page_data: PageData,
        seo_data: Dict[str, Any],
        target_keyword: Optional[str],
        query: Optional[str],
    ) -> str:
        """Build SEO analysis prompt"""
        prompt_parts = ["Perform a comprehensive SEO analysis:\n"]

        # Add parsed data
        if seo_data.get("title"):
            prompt_parts.append(
                f"Title: {seo_data['title']} ({len(seo_data['title'])} characters)"
            )
        else:
            prompt_parts.append("Title: MISSING")

        if seo_data.get("meta_description"):
            prompt_parts.append(
                f"Meta Description: {seo_data['meta_description'][:160]}..."
            )
        else:
            prompt_parts.append("Meta Description: MISSING")

        # Headings
        if seo_data.get("headings"):
            headings = seo_data["headings"]
            h1_count = len(headings.get("h1", []))
            h2_count = len(headings.get("h2", []))
            prompt_parts.append(f"Headings: {h1_count} H1, {h2_count} H2")
            if headings.get("h1"):
                prompt_parts.append(
                    f"H1 Content: {headings['h1'][0] if headings['h1'] else 'None'}"
                )

        # Images
        if seo_data.get("image_analysis"):
            img = seo_data["image_analysis"]
            prompt_parts.append(
                f"Images: {img.get('total_images', 0)} total, {img.get('images_without_alt', 0)} missing alt"
            )

        # Word count
        if seo_data.get("word_count"):
            prompt_parts.append(f"Word Count: {seo_data['word_count']}")

        # Target keyword
        if target_keyword:
            prompt_parts.append(f"\nTarget Keyword: {target_keyword}")
            prompt_parts.append(
                "Analyze keyword usage and optimization for this keyword."
            )

        # Custom query
        if query:
            prompt_parts.append(f"\nSpecific question: {query}")

        return "\n".join(prompt_parts)

    def _calculate_seo_score(
        self, seo_data: Dict[str, Any], seo_analysis: Dict[str, Any]
    ) -> int:
        """Calculate overall SEO score if not provided by LLM"""
        scores = []

        # Title score
        title = seo_data.get("title", "")
        if title:
            title_len = len(title)
            if 50 <= title_len <= 60:
                scores.append(100)
            elif 40 <= title_len <= 70:
                scores.append(70)
            else:
                scores.append(40)
        else:
            scores.append(0)

        # Meta description score
        desc = seo_data.get("meta_description", "")
        if desc:
            desc_len = len(desc)
            if 150 <= desc_len <= 160:
                scores.append(100)
            elif 120 <= desc_len <= 170:
                scores.append(70)
            else:
                scores.append(40)
        else:
            scores.append(0)

        # Image alt score
        if seo_data.get("image_analysis"):
            img = seo_data["image_analysis"]
            coverage = img.get("alt_coverage_percent", 0)
            scores.append(int(coverage))

        return int(sum(scores) / len(scores)) if scores else 50

    def _build_seo_summary(self, score: int, analysis: Dict[str, Any]) -> str:
        """Build SEO summary"""
        if score >= 80:
            rating = "Good"
        elif score >= 60:
            rating = "Needs Improvement"
        else:
            rating = "Poor"

        issues_count = sum(
            len(section.get("issues", []))
            for section in analysis.values()
            if isinstance(section, dict)
        )

        return f"SEO Score: {score}/100 ({rating}). Found {issues_count} issues to address."

    def _extract_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Extract recommendations from analysis sections"""
        recommendations = []

        for key, section in analysis.items():
            if isinstance(section, dict) and "recommendations" in section:
                recommendations.extend(section["recommendations"])

        return recommendations[:10]
