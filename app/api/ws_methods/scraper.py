"""Scraper method handlers."""

from typing import Dict, Any, Optional
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.scraper.generic_extractor import GenericExtractor
from app.services.scraper.structured_data import StructuredDataParser
from app.services.scraper.page_detector import PageDetector


async def handle_scraper_scrape(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    page_data = params.get("page_data") or {}
    html = page_data.get("html") or params.get("html")
    url = page_data.get("url") or params.get("url")
    if not html or not url:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing page_data.html/page_data.url"
        )

    generic = GenericExtractor(html).extract_all()
    structured = StructuredDataParser(html).extract_all()
    detected = PageDetector().detect(
        url=url, structured_data=structured.get("json_ld"), html_content=html
    )
    return {
        "url": url,
        "page_type": detected,
        "generic": generic,
        "structured_data": structured,
    }


def get_methods() -> Dict[str, Any]:
    return {"scraper.scrape": handle_scraper_scrape}
