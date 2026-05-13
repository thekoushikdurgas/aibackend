"""Tests for Open-Meteo weather normalization and fetch."""

import httpx
import pytest

from app.services.weather.open_meteo import (
    c_to_f,
    fetch_weather_forecast,
    normalize_open_meteo_payload,
    wmo_weather_summary,
)

_CANNED_OPEN_METEO = {
    "latitude": 40.71,
    "longitude": -74.01,
    "generationtime_ms": 1.0,
    "utc_offset_seconds": 0,
    "timezone": "America/New_York",
    "timezone_abbreviation": "EST",
    "elevation": 10.0,
    "current_units": {
        "time": "iso8601",
        "temperature_2m": "°C",
        "weather_code": "wmo code",
    },
    "current": {
        "time": "2026-05-12T15:00",
        "temperature_2m": 18.5,
        "weather_code": 2,
    },
    "hourly_units": {
        "time": "iso8601",
        "temperature_2m": "°C",
        "weather_code": "wmo code",
    },
    "hourly": {
        "time": [
            "2026-05-12T14:00",
            "2026-05-12T15:00",
            "2026-05-12T16:00",
            "2026-05-12T17:00",
        ],
        "temperature_2m": [17.0, 18.5, 19.0, 18.0],
        "weather_code": [1, 2, 3, 61],
    },
    "daily_units": {
        "time": "iso8601",
        "weather_code": "wmo code",
        "temperature_2m_max": "°C",
        "temperature_2m_min": "°C",
    },
    "daily": {
        "time": ["2026-05-12", "2026-05-13"],
        "weather_code": [2, 61],
        "temperature_2m_max": [20.0, 22.0],
        "temperature_2m_min": [12.0, 14.0],
    },
}


def test_c_to_f():
    assert c_to_f(0.0) == 32.0
    assert c_to_f(100.0) == 212.0


def test_wmo_weather_summary():
    assert wmo_weather_summary(0) == "Clear sky"
    assert wmo_weather_summary(61) == "Rain"
    assert wmo_weather_summary(None) == "Unknown"


def test_normalize_open_meteo_payload_shape():
    out = normalize_open_meteo_payload(_CANNED_OPEN_METEO, 40.71, -74.01)
    assert out["latitude"] == 40.71
    assert out["longitude"] == -74.01
    assert out["timezone"] == "America/New_York"
    assert out["timezoneAbbreviation"] == "EST"
    assert out["current"]["tempC"] == 18.5
    assert out["current"]["tempF"] == c_to_f(18.5)
    assert out["current"]["weatherCode"] == 2
    assert out["current"]["summary"] == "Partly cloudy"
    assert len(out["hourly"]) >= 1
    assert out["hourly"][0]["time"] == "2026-05-12T15:00"
    assert len(out["daily"]) == 2
    assert out["daily"][0]["date"] == "2026-05-12"
    assert out["daily"][0]["maxC"] == 20.0
    assert out["daily"][0]["minC"] == 12.0


@pytest.mark.asyncio
async def test_fetch_weather_forecast_with_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "open-meteo.com" in str(request.url)
        return httpx.Response(200, json=_CANNED_OPEN_METEO)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        out = await fetch_weather_forecast(40.71, -74.01, client=client)
    assert out["current"]["summary"] == "Partly cloudy"
    assert out["hourly"][0]["weatherCode"] == 2
