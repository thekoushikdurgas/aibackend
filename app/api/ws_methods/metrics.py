"""
Metrics method handlers
"""

import logging
from typing import Dict, Any, Optional

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_metrics_summary(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle metrics.summary method"""
    try:
        from app.services.metrics import MetricsService

        service = MetricsService()
        summary = await service.get_summary()
        return summary
    except ImportError:
        # Metrics service may not be available
        return {"total_requests": 0, "total_tokens": 0, "providers": {}}
    except Exception as e:
        logger.error(f"Metrics summary error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Metrics summary failed: {str(e)}"
        )


async def handle_metrics_council(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Counters for Council v2 claim verification and abstention."""
    try:
        from app.services.metrics.council_metrics import council_metrics

        return council_metrics.snapshot()
    except Exception as e:
        logger.error("Metrics council error: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"Metrics council failed: {str(e)}",
        ) from e


async def handle_metrics_providers(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle metrics.providers method"""
    try:
        from app.services.metrics import MetricsService

        service = MetricsService()
        providers = await service.get_provider_metrics()
        return {"providers": providers}
    except ImportError:
        return {"providers": []}
    except Exception as e:
        logger.error(f"Metrics providers error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Metrics providers failed: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "metrics.summary": handle_metrics_summary,
        "metrics.providers": handle_metrics_providers,
        "metrics.council": handle_metrics_council,
    }
