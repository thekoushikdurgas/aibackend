"""
Rate limiting configuration for DurgasAI Backend
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def get_identifier(request):
    """
    Get identifier for rate limiting.
    Uses API key if present, otherwise falls back to IP address.
    """
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"

    # Try to get from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1][:20]  # Use first 20 chars of token
        return f"token:{token}"

    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance (anonymous baseline; route decorators may tighten/loosen).
limiter = Limiter(
    key_func=get_identifier,
    default_limits=[f"{settings.rate_limit_per_minute_anonymous}/minute"],
)


# Rate limit decorators for different endpoints
def rate_limit_chat():
    """Rate limit for chat endpoints - higher limit"""
    return limiter.limit(f"{settings.rate_limit_per_minute_authenticated * 2}/minute")


def rate_limit_agents():
    """Rate limit for agent endpoints - standard limit"""
    return limiter.limit(f"{settings.rate_limit_per_minute_authenticated}/minute")


def rate_limit_rag():
    """Rate limit for RAG endpoints - lower limit for writes"""
    return limiter.limit(
        f"{max(1, settings.rate_limit_per_minute_authenticated // 2)}/minute"
    )


def rate_limit_auth():
    """Rate limit for auth endpoints - strict limit"""
    return limiter.limit("10/minute")
