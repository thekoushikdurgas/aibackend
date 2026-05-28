"""Public weather forecast GraphQL (Open-Meteo via backend)."""

from __future__ import annotations

from typing import Any, Optional, cast

import strawberry
from graphql import GraphQLError
from strawberry.scalars import JSON
from strawberry.types import Info

from app.config import settings
from app.core.response_cache import cached_json_response
from app.graphql.context import GraphQLContext
from app.graphql.modules.util import graphql_params
from app.services.weather.open_meteo import fetch_weather_forecast


def _coerce_float(value: Any, field: str) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        raise GraphQLError(
            f"Invalid {field}; expected a number.",
            extensions={"code": "BAD_USER_INPUT"},
        ) from e


@strawberry.type
class WeatherQuery:
    @strawberry.field
    async def weather_forecast(self, info: Info, params: JSON | None = None) -> JSON:
        """
        Current conditions, hourly strip (~12 slots), and daily highs/lows.
        Params: optional `latitude`, `longitude` (numbers). Falls back to settings defaults.
        """
        p = graphql_params(params)
        lat = _coerce_float(p.get("latitude"), "latitude")
        lon = _coerce_float(p.get("longitude"), "longitude")

        if lat is None:
            lat = float(settings.weather_default_latitude)
        if lon is None:
            lon = float(settings.weather_default_longitude)

        if not (-90.0 <= lat <= 90.0):
            raise GraphQLError(
                "latitude must be between -90 and 90.",
                extensions={"code": "BAD_USER_INPUT"},
            )
        if not (-180.0 <= lon <= 180.0):
            raise GraphQLError(
                "longitude must be between -180 and 180.",
                extensions={"code": "BAD_USER_INPUT"},
            )

        ctx = info.context
        req = ctx.request if isinstance(ctx, GraphQLContext) else None
        key = f"gql:weather:{lat:.4f}:{lon:.4f}"

        async def _fetch() -> Any:
            return await fetch_weather_forecast(lat, lon)

        try:
            if req is not None:
                return cast(JSON, await cached_json_response(req, key, 900.0, _fetch))
            return cast(JSON, await _fetch())
        except RuntimeError as e:
            raise GraphQLError(str(e), extensions={"code": "INTERNAL"}) from e
