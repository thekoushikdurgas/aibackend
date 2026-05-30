"""
Supply Chain Monitor API Router
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["SupplyChain"])

# In-memory cache to prevent quota limits (429 Rate Limits / Exceeded quotas)
events_cache: Optional[Dict[str, Any]] = None
news_cache: Dict[str, Dict[str, Any]] = {}

EVENTS_CACHE_DURATION = 15 * 60  # 15 minutes in seconds
NEWS_CACHE_DURATION = 15 * 60  # 15 minutes in seconds


def get_fallback_events() -> List[Dict[str, Any]]:
    """Fallback data generator for global events"""
    return [
        {
            "id": "suez",
            "title": "Suez Canal Security Review",
            "summary": "Maritime coordination authorities verify clearance routes and electronic tracking resilience protocols across critical transit corridors.",
            "category": "Geopolitics",
            "country": "Egypt",
            "lat": 30.5852,
            "lng": 32.2654,
            "size": 1.8,
            "isFallback": True,
            "daysAgo": 0,
        },
        {
            "id": "panama",
            "title": "Panama Canal Lock Operations Update",
            "summary": "Canal locks schedule routine conservation procedures to optimize fresh water levels ahead of seasonal vessel arrivals.",
            "category": "Geopolitics",
            "country": "Panama",
            "lat": 9.1438,
            "lng": -79.7345,
            "size": 1.5,
            "isFallback": True,
            "daysAgo": 1,
        },
        {
            "id": "bab",
            "title": "Bab el-Mandeb Safe Transit Measures",
            "summary": "Naval authorities implement coordinated safe passage zones for commercial vessels traversing high-traffic choke points.",
            "category": "Military",
            "country": "Yemen",
            "lat": 12.5833,
            "lng": 43.3333,
            "size": 1.7,
            "isFallback": True,
            "daysAgo": 2,
        },
        {
            "id": "hormuz",
            "title": "Strait of Hormuz Resource Transport Corridor",
            "summary": "LNG and chemical tanker transits operate normally following unified commercial logistics protection coordination standard.",
            "category": "Military",
            "country": "Iran",
            "lat": 26.5667,
            "lng": 56.2500,
            "size": 1.6,
            "isFallback": True,
            "daysAgo": 3,
        },
        {
            "id": "sa",
            "title": "Cape Corridor Freight Capacity Surge",
            "summary": "Continental maritime agencies report standard handling bandwidth at deep water cargo berths as bypass volume balances.",
            "category": "Economy",
            "country": "South Africa",
            "lat": -30.5595,
            "lng": 22.9375,
            "size": 1.5,
            "isFallback": True,
            "daysAgo": 4,
        },
        {
            "id": "tx",
            "title": "Texas Energy Hub Distribution Upgrades",
            "summary": "Grid operators install advanced weatherproofing units to shield priority energy lines from extreme conditions.",
            "category": "Energy",
            "country": "United States",
            "lat": 31.9686,
            "lng": -99.9018,
            "size": 1.2,
            "isFallback": True,
            "daysAgo": 5,
        },
        {
            "id": "ua",
            "title": "Sub-Carpathian Strategic Reservoirs Protection",
            "summary": "Grid resilience response teams finalize early-season storage procedures to guarantee uninterrupted continental supply flow.",
            "category": "Energy",
            "country": "Ukraine",
            "lat": 48.3794,
            "lng": 31.1656,
            "size": 1.8,
            "isFallback": True,
            "daysAgo": 6,
        },
        {
            "id": "ru",
            "title": "Northern Logistics Infrastructure Expansion",
            "summary": "Arctic corridor route expansion initiatives confirm structural upgrades on deep-sea harbor installations.",
            "category": "Energy",
            "country": "Russia",
            "lat": 61.5240,
            "lng": 105.3188,
            "size": 1.8,
            "isFallback": True,
            "daysAgo": 7,
        },
        {
            "id": "il",
            "title": "Bilateral Logistics Connectivity Pact",
            "summary": "Joint trade commission ratifies streamlined digital customs integration standard to accelerate critical transport operations.",
            "category": "Military",
            "country": "Israel",
            "lat": 31.0461,
            "lng": 34.8516,
            "size": 1.7,
            "isFallback": True,
            "daysAgo": 1,
        },
        {
            "id": "tw",
            "title": "High-Value Semiconductor Fab Safeguards",
            "summary": "Hardware manufacturers outline advanced business continuity measures to secure supply chains during regional geological patterns.",
            "category": "Economy",
            "country": "Taiwan",
            "lat": 23.6978,
            "lng": 120.9605,
            "size": 1.6,
            "isFallback": True,
            "daysAgo": 3,
        },
    ]


def get_fallback_news(country: str, category: str) -> Dict[str, Any]:
    """Fallback data generator for news reports"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    headline = f"{category} Regional Assessment for {country}"

    summary = f"Strategic analysis of local parameters regarding {category} in {country} demonstrates ongoing stability under revised operational frameworks."
    details = [
        f"Local authorities in {country} have authorized precautionary route protections to ensure consistent flow.",
        "Security intelligence services report normal activities without foreign or regional interference warnings.",
        "A newly introduced digital tracking scheme has boosted real-time coordination by 15% across hubs.",
    ]

    cat_lower = category.lower()
    if "energy" in cat_lower:
        summary = f"{country} storage terminals report stable stockpiles of essential fuel vectors following successful infrastructure modernization sweeps."
        details = [
            f"Undersea grid interconnectors in {country} have logged record capacity transfer levels with zero disruption events.",
            "Commercial energy trade agreements have been renewed with strategic neighboring economies to lock stable tariffs.",
            "Independent regulatory reports confirm adequate winter buffers are in place at primary storage facilities.",
        ]
    elif "military" in cat_lower or "conflict" in cat_lower:
        summary = f"Integrated patrol coordination teams have established preventive security monitors near shipping lines in {country}."
        details = [
            "Combined marine forces conducted routine navigation protection drills successfully under global safety treaties.",
            "Cyber defense units confirmed that key port control operations are actively insulated from unauthorized intrusion.",
            "Local warning networks are in active standby with communication lines fully functional.",
        ]
    elif (
        "politics" in cat_lower or "appoint" in cat_lower or "geopolitics" in cat_lower
    ):
        summary = f"The diplomatic registry of {country} has briefed partner authorities regarding refined regulatory frameworks for cross-border transit logistics."
        details = [
            "Cabinet officials confirmed the appointment of an expert task force to oversee direct port access negotiations.",
            "A high-level trade accord has been ratified to lower port handling friction and cargo transit times.",
            "National infrastructure directors outlined a long-term capital allocation plan supporting logistics corridors.",
        ]
    elif "economy" in cat_lower:
        summary = f"{country} industrial manufacturing pipelines indicate sturdy performance metrics despite dynamic global market shifts."
        details = [
            "The regional cargo terminal has expanded deep-water vessel processing speed by an estimated 10%.",
            "Strategic trade councils resolved to expand regional transport finance incentives to offset global shipping rate surges.",
            "Economic indicators tracking trade processing times have dropped for the third consecutive quarter.",
        ]

    return {
        "data": {
            "headline": headline,
            "summary": summary,
            "details": details,
            "timestamp": timestamp,
        },
        "groundingMetadata": None,
    }


@router.get("/events")
async def get_events(refresh: bool = Query(False)) -> JSONResponse:
    """Get active global events related to supply chain stability"""
    global events_cache

    current_time = time.time()
    if not refresh and events_cache and events_cache.get("expiry", 0) > current_time:
        return JSONResponse(events_cache["data"])

    # Fallback if api key is missing or is placeholder
    api_key = settings.gemini_api_key
    if not api_key or any(
        p in api_key.lower() for p in ["placeholder", "your-api-key"]
    ):
        logger.warning(
            "Using fallback local events data due to missing or placeholder gemini_api_key."
        )
        return JSONResponse(get_fallback_events())

    model = settings.gemini_model or "gemini-2.5-flash"
    url = f"{settings.gemini_base_url}/models/{model}:generateContent?key={api_key}"

    # Setup schema matching the expected fields
    response_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "id": {"type": "STRING"},
                "title": {"type": "STRING"},
                "summary": {"type": "STRING"},
                "category": {
                    "type": "STRING",
                    "enum": ["Geopolitics", "Energy", "Military", "Economy"],
                },
                "country": {"type": "STRING"},
                "lat": {"type": "NUMBER"},
                "lng": {"type": "NUMBER"},
                "size": {
                    "type": "NUMBER",
                    "description": "Importance of event from 1.0 to 2.0",
                },
                "daysAgo": {
                    "type": "INTEGER",
                    "description": "Relative age of the event in days (0 to 7, integer)",
                },
            },
            "required": [
                "id",
                "title",
                "summary",
                "category",
                "country",
                "lat",
                "lng",
                "size",
                "daysAgo",
            ],
        },
    }

    prompt = (
        "Find current real global news events in the categories of Geopolitics, Energy, Military, and Economy. "
        "Return a list of 10-15 recent events. For each event, provide a unique ID, a title, a brief summary, "
        "the category, the country it occurred in, the latitude and longitude of that country, and how many days ago "
        "it occurred (from 0 to 7 days, with 0 being today). Make sure the coordinates are accurate."
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Parse structural content
            candidate = data["candidates"][0]
            text_content = candidate["content"]["parts"][0]["text"]
            import json

            events = json.loads(text_content)

            # Map fallback property to false
            final_events = [{**ev, "isFallback": False} for ev in events]

            # Cache response
            events_cache = {
                "data": final_events,
                "expiry": current_time + EVENTS_CACHE_DURATION,
            }
            return JSONResponse(final_events)

    except Exception as e:
        logger.error(f"Gemini events API error: {e}", exc_info=True)
        # Graceful fallback recovery
        return JSONResponse(get_fallback_events())


@router.get("/news")
async def get_news(
    country: str, category: str, refresh: bool = Query(False)
) -> JSONResponse:
    """Get detailed news reports for a specific country and category using Gemini with Google Search grounding"""
    global news_cache

    cache_key = f"{country}_{category}"
    current_time = time.time()

    if (
        not refresh
        and cache_key in news_cache
        and news_cache[cache_key].get("expiry", 0) > current_time
    ):
        return JSONResponse(news_cache[cache_key]["data"])

    # Fallback if api key is missing or is placeholder
    api_key = settings.gemini_api_key
    if not api_key or any(
        p in api_key.lower() for p in ["placeholder", "your-api-key"]
    ):
        logger.warning(
            "Using fallback local news data due to missing or placeholder gemini_api_key."
        )
        return JSONResponse(get_fallback_news(country, category))

    model = settings.gemini_model or "gemini-2.5-flash"
    url = f"{settings.gemini_base_url}/models/{model}:generateContent?key={api_key}"

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "headline": {
                "type": "STRING",
                "description": "A concise, catchy headline for the news.",
            },
            "summary": {
                "type": "STRING",
                "description": "A short summary of the events (e.g., 'Power blackout due to oil blockade').",
            },
            "details": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "A few bullet points detailing the events and their impact.",
            },
            "timestamp": {
                "type": "STRING",
                "description": "The current date and time of the report.",
            },
        },
        "required": ["headline", "summary", "details", "timestamp"],
    }

    prompt = (
        f"Provide the latest news regarding {category} for {country}. "
        f"Summarize how these specific events are currently affecting the region and global landscape. "
        f"Keep it concise."
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            candidate = data["candidates"][0]
            text_content = candidate["content"]["parts"][0]["text"]

            import json

            parsed_data = json.loads(text_content)

            # Extract grounding metadata if present
            grounding_metadata = candidate.get("groundingMetadata")

            response_data = {
                "data": parsed_data,
                "groundingMetadata": grounding_metadata,
            }

            # Cache response
            news_cache[cache_key] = {
                "data": response_data,
                "expiry": current_time + NEWS_CACHE_DURATION,
            }
            return JSONResponse(response_data)

    except Exception as e:
        logger.error(
            f"Gemini news API error for {country}/{category}: {e}", exc_info=True
        )
        # Graceful fallback recovery
        return JSONResponse(get_fallback_news(country, category))
