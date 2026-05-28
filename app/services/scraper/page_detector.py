"""
Page Type Detector - Detects what type of page we're analyzing
"""

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class PageDetector:
    """
    Detects page type using multiple heuristics:
    - URL patterns
    - Structured data (JSON-LD @type)
    - DOM patterns
    - Content analysis
    """

    # URL patterns for different page types
    URL_PATTERNS = {
        "course": [
            r"/course/",
            r"/courses/",
            r"/learn/",
            r"/training/",
            r"/tutorial/",
            r"udemy\.com",
            r"coursera\.org",
            r"edx\.org",
        ],
        "product": [
            r"/product/",
            r"/products/",
            r"/p/",
            r"/dp/",
            r"amazon\.com",
            r"shopify\.com",
            r"etsy\.com",
        ],
        "article": [
            r"/article/",
            r"/articles/",
            r"/post/",
            r"/posts/",
            r"/blog/",
            r"medium\.com",
            r"wordpress\.com",
        ],
        "documentation": [
            r"/docs/",
            r"/documentation/",
            r"/guide/",
            r"/api/",
            r"readthedocs\.io",
            r"github\.io",
        ],
        "landing": [
            r"/$",  # Root path
            r"/home",
            r"/index",
        ],
    }

    # Structured data types that indicate page type
    STRUCTURED_DATA_TYPES = {
        "course": ["Course", "CourseInstance", "LearningResource"],
        "product": ["Product", "Offer", "AggregateOffer"],
        "article": ["Article", "BlogPosting", "NewsArticle"],
        "organization": ["Organization", "LocalBusiness", "Corporation"],
        "person": ["Person", "ProfilePage"],
        "event": ["Event"],
        "recipe": ["Recipe"],
        "video": ["VideoObject"],
    }

    def __init__(self):
        """Initialize the page detector"""
        pass

    def detect(
        self,
        url: str,
        structured_data: Optional[List[Dict[str, Any]]] = None,
        html_content: Optional[str] = None,
        meta_tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Detect page type using multiple heuristics.

        Args:
            url: Page URL
            structured_data: Extracted JSON-LD structured data
            html_content: HTML content for pattern matching
            meta_tags: Meta tags from page

        Returns:
            Dictionary with:
            - page_type: Detected type (str)
            - confidence: Confidence score 0-100 (float)
            - indicators: List of indicators that led to detection
        """
        indicators: List[str] = []
        scores: Dict[str, float] = {}

        # 1. Check URL patterns
        url_type, url_confidence = self._detect_from_url(url)
        if url_type:
            scores[url_type] = scores.get(url_type, 0) + url_confidence
            indicators.append(f"URL pattern: {url_type}")

        # 2. Check structured data
        if structured_data:
            sd_type, sd_confidence = self._detect_from_structured_data(structured_data)
            if sd_type:
                scores[sd_type] = scores.get(sd_type, 0) + sd_confidence
                indicators.append(f"Structured data: {sd_type}")

        # 3. Check meta tags
        if meta_tags:
            meta_type, meta_confidence = self._detect_from_meta(meta_tags)
            if meta_type:
                scores[meta_type] = scores.get(meta_type, 0) + meta_confidence
                indicators.append(f"Meta tags: {meta_type}")

        # 4. Check DOM patterns (if HTML provided)
        if html_content:
            dom_type, dom_confidence = self._detect_from_dom(html_content)
            if dom_type:
                scores[dom_type] = scores.get(dom_type, 0) + dom_confidence
                indicators.append(f"DOM pattern: {dom_type}")

        # Determine final type
        if scores:
            page_type = max(scores.items(), key=lambda x: x[1])[0]
            confidence = min(scores[page_type], 100.0)
        else:
            page_type = "generic"
            confidence = 50.0
            indicators.append("No specific indicators found, defaulting to generic")

        return {
            "page_type": page_type,
            "confidence": round(confidence, 1),
            "indicators": indicators,
            "scores": scores,
        }

    def _detect_from_url(self, url: str) -> tuple:
        """Detect page type from URL patterns"""
        url_lower = url.lower()

        for page_type, patterns in self.URL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return page_type, 70.0

        return None, 0.0

    def _detect_from_structured_data(
        self, structured_data: List[Dict[str, Any]]
    ) -> tuple:
        """Detect page type from JSON-LD structured data"""
        for data in structured_data:
            if isinstance(data, dict):
                # Handle @graph arrays
                items = data.get("@graph", [data])

                for item in items:
                    if isinstance(item, dict):
                        item_type = item.get("@type", "")
                        if isinstance(item_type, str):
                            item_type = item_type.split("/")[-1]  # Get last part
                        elif isinstance(item_type, list):
                            item_type = item_type[0] if item_type else ""

                        # Check against known types
                        for page_type, types in self.STRUCTURED_DATA_TYPES.items():
                            if item_type in types:
                                return page_type, 85.0

        return None, 0.0

    def _detect_from_meta(self, meta_tags: List[Dict[str, str]]) -> tuple:
        """Detect page type from meta tags"""
        for meta in meta_tags:
            property_name = meta.get("property", "").lower()
            name = meta.get("name", "").lower()

            # Open Graph type
            if property_name == "og:type":
                og_type = meta.get("content", "").lower()
                if "article" in og_type:
                    return "article", 75.0
                elif "product" in og_type:
                    return "product", 75.0
                elif "video" in og_type:
                    return "video", 75.0

            # Twitter card
            if name == "twitter:card":
                card_type = meta.get("content", "").lower()
                if "summary_large_image" in card_type or "summary" in card_type:
                    return "article", 60.0

        return None, 0.0

    def _detect_from_dom(self, html_content: str) -> tuple:
        """Detect page type from DOM patterns"""
        html_lower = html_content.lower()

        # Course indicators
        course_indicators = [
            "curriculum",
            "syllabus",
            "lecture",
            "instructor",
            "enroll",
            "course-content",
            "learning-objectives",
        ]
        if any(indicator in html_lower for indicator in course_indicators):
            return "course", 65.0

        # Product indicators
        product_indicators = [
            "add-to-cart",
            "buy-now",
            "price",
            "product-details",
            "shopping-cart",
            "add-to-bag",
        ]
        if any(indicator in html_lower for indicator in product_indicators):
            return "product", 65.0

        # Article indicators
        article_indicators = [
            "article-content",
            "post-content",
            "author",
            "publish-date",
            "reading-time",
            "article-body",
        ]
        if any(indicator in html_lower for indicator in article_indicators):
            return "article", 65.0

        return None, 0.0
