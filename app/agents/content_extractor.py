"""
Content Extractor Agent - Extract structured data from pages
"""

import logging
from typing import Any, Dict, List, Optional

from app.models.schemas import PageData
from app.utils.html_parser import HTMLParser
from app.utils.helpers import extract_keywords, calculate_reading_time
from .base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class ContentExtractorAgent(BaseAgent):
    """
    Agent specialized in extracting structured data from web pages.
    Identifies and extracts products, articles, contact info, etc.
    """

    agent_type = "content_extractor"
    description = "Extract structured data and entities from pages"

    def get_system_prompt(self) -> str:
        return """You are a data extraction expert. Your role is to extract structured information from web pages:

1. Entity Extraction: People, organizations, products, prices, dates, locations
2. Content Type Detection: Is this an article, product page, landing page, etc.?
3. Key Information: Main topic, purpose, target audience
4. Structured Data: Extract any product info, contact details, social links
5. Content Summary: Main points and key takeaways

Format your response as JSON:
{
    "content_type": "article|product|landing|blog|ecommerce|other",
    "main_topic": "brief topic description",
    "entities": {
        "people": [],
        "organizations": [],
        "products": [],
        "prices": [],
        "dates": [],
        "locations": [],
        "emails": [],
        "phones": []
    },
    "key_points": ["list of main points"],
    "extracted_data": {
        "title": "",
        "author": "",
        "publish_date": "",
        "price": "",
        "currency": ""
    },
    "confidence": 0-100
}"""

    async def analyze(
        self,
        page_data: PageData,
        query: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Extract structured content from the page.
        """
        options = options or {}
        extract_type = options.get("extract_type", "auto")

        try:
            # Prepare context
            context = self._prepare_page_context(page_data)

            # Parse HTML and extract basic info
            basic_extraction = {}
            text_content = ""

            if page_data.html or page_data.body_html:
                html_content = page_data.html or page_data.body_html
                try:
                    parser = HTMLParser(html_content)
                    basic_extraction = {
                        "title": parser.get_title(),
                        "meta_description": parser.get_meta_description(),
                        "headings": parser.get_headings(),
                        "links_count": len(parser.get_links()),
                        "images_count": len(parser.get_images()),
                        "word_count": parser.get_word_count(),
                    }
                    text_content = parser.get_text_content(max_length=5000)
                except Exception as e:
                    logger.warning(f"HTML parsing failed: {e}")

            # Extract keywords locally
            keywords = (
                extract_keywords(text_content, max_keywords=15) if text_content else []
            )
            reading_time = calculate_reading_time(text_content) if text_content else 0

            # Build extraction prompt
            prompt = self._build_extraction_prompt(
                page_data, basic_extraction, text_content, query, extract_type
            )

            # Call LLM for extraction
            llm_response = await self._call_llm(prompt, context)

            # Parse response
            extracted_data = self._parse_json_response(llm_response)

            # Combine results
            analysis = {
                "url": page_data.url,
                "basic_extraction": basic_extraction,
                "llm_extraction": extracted_data,
                "keywords": keywords,
                "reading_time_minutes": reading_time,
                "text_preview": text_content[:500] if text_content else "",
            }

            # Build summary
            content_type = extracted_data.get("content_type", "unknown")
            main_topic = extracted_data.get("main_topic", "")
            summary = f"Content type: {content_type}. {main_topic}"

            # Get recommendations based on extraction
            recommendations = self._generate_recommendations(extracted_data)

            return AgentResponse(
                agent_type=self.agent_type,
                analysis=analysis,
                summary=summary[:500],
                recommendations=recommendations,
                metadata={
                    "content_type": content_type,
                    "confidence": extracted_data.get("confidence", 0),
                    "entities_found": self._count_entities(
                        extracted_data.get("entities", {})
                    ),
                    "keywords": keywords[:5],
                },
            )

        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return AgentResponse(
                agent_type=self.agent_type,
                analysis={"error": str(e)},
                summary=f"Extraction failed: {str(e)}",
                success=False,
                error=str(e),
            )

    def _build_extraction_prompt(
        self,
        page_data: PageData,
        basic_extraction: Dict[str, Any],
        text_content: str,
        query: Optional[str],
        extract_type: str,
    ) -> str:
        """Build the extraction prompt"""
        prompt_parts = ["Extract structured data from this web page:\n"]

        # Add basic info
        prompt_parts.append(f"URL: {page_data.url}")
        if basic_extraction.get("title"):
            prompt_parts.append(f"Title: {basic_extraction['title']}")
        if basic_extraction.get("meta_description"):
            prompt_parts.append(f"Description: {basic_extraction['meta_description']}")

        # Add text content preview
        if text_content:
            prompt_parts.append(
                f"\nContent Preview (first 2000 chars):\n{text_content[:2000]}"
            )

        # Add headings for context
        if basic_extraction.get("headings"):
            h1s = basic_extraction["headings"].get("h1", [])
            h2s = basic_extraction["headings"].get("h2", [])
            if h1s:
                prompt_parts.append(f"\nH1 Headings: {', '.join(h1s[:3])}")
            if h2s:
                prompt_parts.append(f"H2 Headings: {', '.join(h2s[:5])}")

        # Add specific extraction request
        if extract_type != "auto":
            prompt_parts.append(f"\nFocus on extracting: {extract_type}")

        if query:
            prompt_parts.append(f"\nSpecific request: {query}")

        return "\n".join(prompt_parts)

    def _count_entities(self, entities: Dict[str, List]) -> int:
        """Count total entities found"""
        total = 0
        for entity_list in entities.values():
            if isinstance(entity_list, list):
                total += len(entity_list)
        return total

    def _generate_recommendations(self, extracted_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on extraction results"""
        recommendations = []

        entities = extracted_data.get("entities", {})

        # Check for missing structured data
        if not entities.get("emails") and not entities.get("phones"):
            recommendations.append("Consider adding visible contact information")

        if extracted_data.get("content_type") == "product" and not entities.get(
            "prices"
        ):
            recommendations.append("Product page should have clear pricing information")

        if not extracted_data.get("main_topic"):
            recommendations.append("Page purpose is unclear - improve content focus")

        return recommendations
