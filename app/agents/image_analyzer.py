"""
Image Analyzer Agent - Image analysis and optimization
"""

import logging
from typing import Any, Dict, List, Optional

from app.models.schemas import PageData
from .base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class ImageAnalyzerAgent(BaseAgent):
    """
    Agent specialized in image analysis and optimization.
    Analyzes images for SEO, accessibility, and performance.
    """

    agent_type = "image_analyzer"
    description = "Image analysis, optimization, and accessibility assessment"

    def get_system_prompt(self) -> str:
        return """You are an image optimization expert. Analyze images on web pages for:

1. Accessibility: Alt text quality, descriptiveness, context
2. SEO: Image naming, alt text keywords, file names
3. Performance: Size concerns, lazy loading, format suggestions
4. Quality: Resolution, aspect ratios, visual consistency
5. Usability: Image relevance, placement, mobile considerations

Provide specific recommendations for each image when possible.
Format response as JSON:
{
    "overall_score": 0-100,
    "accessibility_score": 0-100,
    "seo_score": 0-100,
    "performance_score": 0-100,
    "summary": "brief overall assessment",
    "images_analyzed": [
        {
            "src": "image url",
            "alt_quality": "good|poor|missing",
            "issues": [],
            "suggested_alt": "if missing or poor"
        }
    ],
    "critical_issues": ["list of most important issues"],
    "recommendations": ["prioritized recommendations"]
}"""

    async def analyze(
        self,
        page_data: PageData,
        query: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Analyze images on the page.
        """
        options = options or {}
        analyze_limit = options.get("limit", 20)  # Limit images to analyze

        try:
            # Get images from page data
            images = page_data.images or []

            if not images:
                return AgentResponse(
                    agent_type=self.agent_type,
                    analysis={
                        "url": page_data.url,
                        "images_found": 0,
                        "message": "No images found on this page",
                    },
                    summary="No images found on this page to analyze.",
                    recommendations=[
                        "Consider adding relevant images to improve engagement"
                    ],
                    metadata={"images_found": 0},
                )

            # Prepare image data for analysis
            image_data = self._prepare_image_data(images[:analyze_limit])

            # Calculate basic statistics
            stats = self._calculate_image_stats(images)

            # Prepare context
            context = self._prepare_image_context(page_data, stats)

            # Build analysis prompt
            prompt = self._build_image_prompt(image_data, stats, query)

            # Call LLM for analysis
            llm_response = await self._call_llm(prompt, context)

            # Parse response
            image_analysis = self._parse_json_response(llm_response)

            # Combine results
            analysis = {
                "url": page_data.url,
                "statistics": stats,
                "llm_analysis": image_analysis,
                "images_sample": image_data[:10],  # Include sample in response
            }

            # Get scores
            overall_score = image_analysis.get(
                "overall_score", stats.get("accessibility_score", 50)
            )

            # Build summary
            summary = image_analysis.get("summary", self._build_default_summary(stats))

            # Get recommendations
            recommendations = image_analysis.get("recommendations", [])
            if not recommendations:
                recommendations = self._generate_default_recommendations(stats)

            return AgentResponse(
                agent_type=self.agent_type,
                analysis=analysis,
                summary=(
                    summary[:500] if isinstance(summary, str) else str(summary)[:500]
                ),
                recommendations=recommendations[:10],
                metadata={
                    "total_images": stats["total_images"],
                    "images_with_alt": stats["images_with_alt"],
                    "images_without_alt": stats["images_without_alt"],
                    "overall_score": overall_score,
                    "accessibility_score": image_analysis.get("accessibility_score", 0),
                    "seo_score": image_analysis.get("seo_score", 0),
                },
            )

        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return AgentResponse(
                agent_type=self.agent_type,
                analysis={"error": str(e)},
                summary=f"Image analysis failed: {str(e)}",
                success=False,
                error=str(e),
            )

    def _prepare_image_data(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare image data for LLM analysis"""
        prepared = []
        for img in images:
            prepared.append(
                {
                    "src": img.get("src", "")[:200],  # Truncate long URLs
                    "alt": img.get("alt", ""),
                    "title": img.get("title", ""),
                    "has_alt": bool(img.get("alt")),
                    "filename": self._extract_filename(img.get("src", "")),
                    "dimensions": f"{img.get('width', '?')}x{img.get('height', '?')}",
                }
            )
        return prepared

    def _extract_filename(self, url: str) -> str:
        """Extract filename from URL"""
        if not url:
            return ""
        try:
            from urllib.parse import urlparse

            path = urlparse(url).path
            return path.split("/")[-1][:50] if path else ""
        except (AttributeError, IndexError, ValueError):
            return ""

    def _calculate_image_stats(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate image statistics"""
        total = len(images)
        with_alt = sum(1 for img in images if img.get("alt"))
        without_alt = total - with_alt

        # Calculate accessibility score based on alt text coverage
        accessibility_score = int((with_alt / total) * 100) if total > 0 else 100

        # Count data URIs and blob URIs
        data_uris = sum(
            1 for img in images if str(img.get("src", "")).startswith("data:")
        )
        blob_uris = sum(
            1 for img in images if str(img.get("src", "")).startswith("blob:")
        )

        return {
            "total_images": total,
            "images_with_alt": with_alt,
            "images_without_alt": without_alt,
            "alt_coverage_percent": (
                round((with_alt / total) * 100, 1) if total > 0 else 100
            ),
            "accessibility_score": accessibility_score,
            "data_uri_images": data_uris,
            "blob_uri_images": blob_uris,
        }

    def _prepare_image_context(self, page_data: PageData, stats: Dict[str, Any]) -> str:
        """Prepare context for image analysis"""
        return f"""Page: {page_data.url}
Title: {page_data.title or 'Unknown'}
Total Images: {stats['total_images']}
Images with Alt: {stats['images_with_alt']}
Images without Alt: {stats['images_without_alt']}
Alt Coverage: {stats['alt_coverage_percent']}%"""

    def _build_image_prompt(
        self,
        image_data: List[Dict[str, Any]],
        stats: Dict[str, Any],
        query: Optional[str],
    ) -> str:
        """Build image analysis prompt"""
        prompt_parts = ["Analyze the following images from a web page:\n"]

        # Add statistics
        prompt_parts.append("Statistics:")
        prompt_parts.append(f"- Total images: {stats['total_images']}")
        prompt_parts.append(f"- With alt text: {stats['images_with_alt']}")
        prompt_parts.append(f"- Without alt text: {stats['images_without_alt']}")
        prompt_parts.append(f"- Alt coverage: {stats['alt_coverage_percent']}%")

        # Add image details
        prompt_parts.append("\nImage Details:")
        for i, img in enumerate(image_data[:15], 1):  # Limit to 15 for prompt size
            alt_status = "✓" if img["has_alt"] else "✗"
            prompt_parts.append(f"{i}. {img['filename']} [{alt_status}]")
            if img["has_alt"]:
                prompt_parts.append(f"   Alt: {img['alt'][:100]}")
            prompt_parts.append(f"   Size: {img['dimensions']}")

        if query:
            prompt_parts.append(f"\nSpecific question: {query}")

        return "\n".join(prompt_parts)

    def _build_default_summary(self, stats: Dict[str, Any]) -> str:
        """Build default summary from stats"""
        coverage = stats["alt_coverage_percent"]
        if coverage >= 90:
            rating = "Excellent"
        elif coverage >= 70:
            rating = "Good"
        elif coverage >= 50:
            rating = "Needs Improvement"
        else:
            rating = "Poor"

        return f"{rating} image accessibility ({coverage}% alt text coverage). {stats['images_without_alt']} images need alt text."

    def _generate_default_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate default recommendations based on stats"""
        recommendations = []

        if stats["images_without_alt"] > 0:
            recommendations.append(
                f"Add descriptive alt text to {stats['images_without_alt']} images missing it"
            )

        if stats["alt_coverage_percent"] < 100:
            recommendations.append(
                "Ensure all images have meaningful alt text for accessibility"
            )

        if stats["data_uri_images"] > 5:
            recommendations.append(
                "Consider hosting images externally instead of using data URIs for better caching"
            )

        recommendations.append("Use descriptive, keyword-rich file names for images")
        recommendations.append("Implement lazy loading for images below the fold")

        return recommendations
