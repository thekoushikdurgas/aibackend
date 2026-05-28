"""Open-Meteo forecast client and normalization for the desktop weather widget."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def c_to_f(celsius: float) -> float:
    return round(celsius * 9.0 / 5.0 + 32.0, 1)


def wmo_weather_summary(code: Optional[int]) -> str:
    """Human-readable label for WMO weather interpretation codes (Open-Meteo)."""
    if code is None:
        return "Unknown"
    if code == 0:
        return "Clear sky"
    if code in (1,):
        return "Mainly clear"
    if code in (2,):
        return "Partly cloudy"
    if code in (3,):
        return "Overcast"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55):
        return "Drizzle"
    if code in (56, 57):
        return "Freezing drizzle"
    if code in (61, 63, 65):
        return "Rain"
    if code in (66, 67):
        return "Freezing rain"
    if code in (71, 73, 75):
        return "Snow"
    if code == 77:
        return "Snow grains"
    if code in (80, 81, 82):
        return "Rain showers"
    if code in (85, 86):
        return "Snow showers"
    if code == 95:
        return "Thunderstorm"
    if code in (96, 99):
        return "Thunderstorm with hail"
    return "Mixed conditions"


def _parse_time(s: str) -> Optional[datetime]:
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def normalize_open_meteo_payload(
    data: Dict[str, Any], latitude: float, longitude: float
) -> Dict[str, Any]:
    """
    Turn raw Open-Meteo JSON into a compact shape for GraphQL JSON scalar / UI.
    Keys use camelCase for direct use in TypeScript.
    """
    cur = data.get("current") or {}
    cur_time = cur.get("time")
    temp_c = cur.get("temperature_2m")
    code = cur.get("weather_code")

    current: Dict[str, Any] = {
        "time": cur_time,
        "tempC": None,
        "tempF": None,
        "weatherCode": code,
        "summary": wmo_weather_summary(int(code) if code is not None else None),
    }
    if isinstance(temp_c, (int, float)):
        current["tempC"] = round(float(temp_c), 1)
        current["tempF"] = c_to_f(float(temp_c))

    hourly_raw = data.get("hourly") or {}
    times: List[str] = list(hourly_raw.get("time") or [])
    temps: List[Any] = list(hourly_raw.get("temperature_2m") or [])
    codes: List[Any] = list(hourly_raw.get("weather_code") or [])

    start_idx = 0
    if cur_time and times:
        ct = _parse_time(str(cur_time))
        if ct:
            for i, t in enumerate(times):
                ht = _parse_time(t)
                if ht and ht >= ct:
                    start_idx = i
                    break

    hourly: List[Dict[str, Any]] = []
    for i in range(start_idx, min(start_idx + 12, len(times))):
        tc = temps[i] if i < len(temps) else None
        wc = codes[i] if i < len(codes) else None
        icode = int(wc) if isinstance(wc, (int, float)) else None
        row: Dict[str, Any] = {
            "time": times[i],
            "tempC": None,
            "tempF": None,
            "weatherCode": icode,
            "summary": wmo_weather_summary(icode),
        }
        if isinstance(tc, (int, float)):
            row["tempC"] = round(float(tc), 1)
            row["tempF"] = c_to_f(float(tc))
        hourly.append(row)

    daily_raw = data.get("daily") or {}
    d_times: List[str] = list(daily_raw.get("time") or [])
    d_max: List[Any] = list(daily_raw.get("temperature_2m_max") or [])
    d_min: List[Any] = list(daily_raw.get("temperature_2m_min") or [])
    d_codes: List[Any] = list(daily_raw.get("weather_code") or [])

    daily: List[Dict[str, Any]] = []
    for i in range(min(5, len(d_times))):
        mx = d_max[i] if i < len(d_max) else None
        mn = d_min[i] if i < len(d_min) else None
        dc = d_codes[i] if i < len(d_codes) else None
        icode = int(dc) if isinstance(dc, (int, float)) else None
        day_row: Dict[str, Any] = {
            "date": d_times[i],
            "minC": None,
            "maxC": None,
            "minF": None,
            "maxF": None,
            "weatherCode": icode,
            "summary": wmo_weather_summary(icode),
        }
        if isinstance(mx, (int, float)):
            day_row["maxC"] = round(float(mx), 1)
            day_row["maxF"] = c_to_f(float(mx))
        if isinstance(mn, (int, float)):
            day_row["minC"] = round(float(mn), 1)
            day_row["minF"] = c_to_f(float(mn))
        daily.append(day_row)

    return {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": data.get("timezone"),
        "timezoneAbbreviation": data.get("timezone_abbreviation"),
        "current": current,
        "hourly": hourly,
        "daily": daily,
    }


async def fetch_weather_forecast(
    latitude: float,
    longitude: float,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """Fetch forecast from Open-Meteo and return normalized camelCase JSON."""
    params: dict[str, str | int | float] = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "forecast_days": 7,
        "current": "temperature_2m,weather_code",
        "hourly": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
    }
    timeout = float(getattr(settings, "weather_http_timeout_seconds", 12.0) or 12.0)

    async def _do(c: httpx.AsyncClient) -> Dict[str, Any]:
        resp = await c.get(OPEN_METEO_FORECAST_URL, params=params)
        resp.raise_for_status()
        raw = resp.json()
        if not isinstance(raw, dict):
            raise RuntimeError("Open-Meteo returned invalid JSON")
        return normalize_open_meteo_payload(raw, latitude, longitude)

    try:
        if client is not None:
            return await _do(client)
        async with httpx.AsyncClient(timeout=timeout) as c:
            return await _do(c)
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Open-Meteo HTTP error: %s %s",
            e.response.status_code,
            e.response.text[:200],
        )
        raise RuntimeError(f"Open-Meteo returned HTTP {e.response.status_code}") from e
    except httpx.HTTPError as e:
        logger.warning("Open-Meteo request failed: %s", e)
        raise RuntimeError("Open-Meteo request failed") from e
