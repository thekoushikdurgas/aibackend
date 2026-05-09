"""
Website Scraper Agent - All-in-one website analyzer
Combines smart scraping, generic extraction, structured data parsing, and AI analysis
"""

import logging
from typing import Any, Dict, List, Optional

from app.models.schemas import PageData
from app.utils.html_parser import HTMLParser
from app.services.scraper import (
    PageDetector,
    StructuredDataParser,
    GenericExtractor,
)
from app.services.council import run_full_council
from .base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class WebsiteScraperAgent(BaseAgent):
    """
    All-in-one website analyzer combining:
    - Smart page type detection (product, article, course, etc.)
    - Generic content extraction (headings, tables, lists, forms)
    - Structured data parsing (JSON-LD, schema.org, microdata)
    - Entity extraction (emails, phones, prices, dates)
    - AI-powered analysis using Council AI
    - Export formatting (JSON, CSV, Excel, Markdown)
    """

    agent_type = "website_scraper"
    description = "Comprehensive website analysis with smart scraping and AI insights"

    def get_system_prompt(self) -> str:
        return """You are a website analysis expert. Analyze web pages and extract:
1. Page type and purpose
2. Key content and entities
3. Structured data and metadata
4. Main insights and takeaways
5. Quality assessment

Provide comprehensive, actionable analysis."""

    async def analyze(
        self,
        page_data: PageData,
        query: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Comprehensive website analysis combining multiple extraction methods.

        Args:
            page_data: Page data from extension
            query: Optional specific query/question
            options: Additional options (use_council, export_format, etc.)

        Returns:
            AgentResponse with complete analysis
        """
        options = options or {}
        use_council = options.get("use_council", True)

        try:
            # Get HTML content
            html_content = page_data.html or page_data.body_html or ""

            if not html_content:
                return AgentResponse(
                    agent_type=self.agent_type,
                    analysis={"error": "No HTML content provided"},
                    summary="Analysis failed: No HTML content available",
                    success=False,
                    error="No HTML content provided",
                )

            # 1. Parse HTML
            html_parser = HTMLParser(html_content)

            # 2. Detect page type
            page_detector = PageDetector()
            structured_data_list = html_parser.extract_structured_data()
            meta_tags = page_data.meta or []
            page_type_result = page_detector.detect(
                url=page_data.url,
                structured_data=structured_data_list,
                html_content=html_content,
                meta_tags=meta_tags,
            )

            # 3. Extract structured data
            structured_parser = StructuredDataParser(html_content)
            structured_data = structured_parser.extract_all()

            # Extract page-type-specific data
            page_type = page_type_result.get("page_type", "generic")
            page_specific_data = {}
            if page_type == "course":
                page_specific_data = structured_parser.extract_course_data()
            elif page_type == "product":
                page_specific_data = structured_parser.extract_product_data()

            # 4. Extract generic content
            generic_extractor = GenericExtractor(html_content)
            generic_content = generic_extractor.extract_all()

            # 5. Extract entities (from content extractor logic)
            from app.agents.content_extractor import ContentExtractorAgent

            content_extractor = ContentExtractorAgent(self.config)
            content_response = await content_extractor.analyze(
                page_data, query, {"extract_type": "auto"}
            )
            entities = content_response.analysis.get("llm_extraction", {}).get(
                "entities", {}
            )

            # 6. Use Council AI for intelligent analysis
            ai_analysis = {}
            if use_council:
                try:
                    # Prepare analysis query
                    analysis_query = (
                        query
                        or f"Analyze this {page_type} page and provide key insights, main takeaways, and quality assessment."
                    )

                    # Run Council AI
                    council_models = options.get("council_models")
                    chairman_model = options.get("chairman_model")
                    council_options = {
                        k: options[k]
                        for k in (
                            "council_policy",
                            "policy",
                            "min_confidence",
                            "allow_web_tool",
                            "min_rag_similarity",
                            "verified_min_similarity",
                            "schema_version",
                        )
                        if k in options and options[k] is not None
                    }

                    stage1_results, stage2_results, stage3_result, council_metadata = (
                        await run_full_council(
                            query=analysis_query,
                            page_data=page_data,
                            council_models=council_models,
                            chairman_model=chairman_model,
                            council_options=council_options or None,
                        )
                    )

                    if stage3_result and stage3_result.get("model") != "error":
                        final_response = stage3_result.get("response", "")
                        ai_analysis = {
                            "summary": final_response,
                            "insights": self._extract_insights(final_response),
                            "classification": page_type,
                            "confidence": page_type_result.get("confidence", 0),
                            "council_metadata": {
                                "models_used": council_metadata.get("models_used", []),
                                "chairman": council_metadata.get("chairman", "unknown"),
                            },
                        }
                    else:
                        # Fallback to basic analysis
                        ai_analysis = {
                            "summary": f"This appears to be a {page_type} page.",
                            "insights": [],
                            "classification": page_type,
                            "confidence": page_type_result.get("confidence", 0),
                            "error": "Council AI analysis unavailable",
                        }
                except Exception as e:
                    logger.warning(f"Council AI analysis failed: {e}")
                    ai_analysis = {
                        "summary": f"This appears to be a {page_type} page.",
                        "insights": [],
                        "classification": page_type,
                        "confidence": page_type_result.get("confidence", 0),
                        "error": str(e),
                    }
            else:
                # Basic analysis without Council
                ai_analysis = {
                    "summary": f"This appears to be a {page_type} page.",
                    "insights": [],
                    "classification": page_type,
                    "confidence": page_type_result.get("confidence", 0),
                }

            # 7. Build comprehensive analysis result
            analysis = {
                "page_info": {
                    "url": page_data.url,
                    "title": page_data.title or html_parser.get_title(),
                    "domain": page_data.domain,
                    "page_type": page_type,
                    "confidence": page_type_result.get("confidence", 0),
                    "indicators": page_type_result.get("indicators", []),
                },
                "structured_data": structured_data,
                "page_specific_data": page_specific_data,
                "extracted_content": {
                    "headings": generic_content.get("headings", {}),
                    "tables": generic_content.get("tables", []),
                    "forms": generic_content.get("forms", []),
                    "lists": generic_content.get("lists", []),
                    "contact_info": generic_content.get("contact_info", {}),
                    "quotes": generic_content.get("quotes", []),
                    "code_blocks": generic_content.get("code_blocks", []),
                    "entities": entities,
                },
                "ai_analysis": ai_analysis,
                "html_analysis": {
                    "structure_stats": html_parser.get_structure_stats(),
                    "semantic_elements": html_parser.get_semantic_elements(),
                    "seo_data": html_parser.get_seo_data(),
                },
            }

            # Build summary
            summary = ai_analysis.get(
                "summary", f"Analyzed {page_type} page: {page_data.url}"
            )
            if len(summary) > 500:
                summary = summary[:500] + "..."

            # Build recommendations
            recommendations = []
            if page_type_result.get("confidence", 0) < 70:
                recommendations.append(
                    "Page type detection confidence is low - manual review recommended"
                )
            if not structured_data.get("json_ld"):
                recommendations.append(
                    "No structured data found - consider adding JSON-LD markup"
                )
            if not generic_content.get("tables") and not generic_content.get("lists"):
                recommendations.append(
                    "Limited structured content found - page may be heavily JavaScript-based"
                )

            result = AgentResponse(
                agent_type=self.agent_type,
                analysis=analysis,
                summary=summary,
                recommendations=recommendations,
                metadata={
                    "page_type": page_type,
                    "confidence": page_type_result.get("confidence", 0),
                    "tables_count": len(generic_content.get("tables", [])),
                    "forms_count": len(generic_content.get("forms", [])),
                    "entities_count": sum(
                        len(v) if isinstance(v, list) else 1 for v in entities.values()
                    ),
                },
                success=True,
            )
            return result

        except Exception as e:
            logger.error(f"Website scraping failed: {e}", exc_info=True)
            return AgentResponse(
                agent_type=self.agent_type,
                analysis={"error": str(e)},
                summary=f"Analysis failed: {str(e)}",
                success=False,
                error=str(e),
            )

    def _extract_insights(self, text: str) -> List[str]:
        """Extract key insights from AI response"""
        # Simple extraction - look for bullet points or numbered lists
        insights = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            # Check for bullet points or numbered items
            if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
                insights.append(line[2:].strip())
            elif line and line[0].isdigit() and (". " in line[:5] or ") " in line[:5]):
                insights.append(
                    line.split(". ", 1)[-1] if ". " in line else line.split(") ", 1)[-1]
                )

        # If no structured insights found, split by sentences
        if not insights and len(text) > 100:
            sentences = text.split(". ")
            insights = [s.strip() + "." for s in sentences[:5] if len(s.strip()) > 20]

        return insights[:10]  # Limit to 10 insights
