"""
OpenRouter Usage Monitoring and Error Tracking
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for a single request"""

    timestamp: float
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error_type: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class UsageStats:
    """Aggregated usage statistics"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0.0
    average_latency_ms: float = 0.0
    error_counts: Dict[str, int] = field(default_factory=dict)
    model_usage: Dict[str, int] = field(default_factory=dict)


class OpenRouterMonitor:
    """
    Monitor OpenRouter API usage, errors, and performance.
    Tracks metrics for analysis and alerting.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize monitor.

        Args:
            max_history: Maximum number of requests to keep in history
        """
        self.max_history = max_history
        self.request_history: List[RequestMetrics] = []
        self.stats = UsageStats()
        self._lock = None  # Would use asyncio.Lock in async context

    def record_request(
        self,
        model: str,
        provider: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """
        Record a request and its metrics.

        Args:
            model: Model used
            provider: Provider name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            latency_ms: Request latency in milliseconds
            success: Whether request succeeded
            error_type: Type of error if failed
            error_message: Error message if failed
        """
        metrics = RequestMetrics(
            timestamp=time.time(),
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            success=success,
            error_type=error_type,
            error_message=error_message,
        )

        # Add to history
        self.request_history.append(metrics)

        # Trim history if too long
        if len(self.request_history) > self.max_history:
            self.request_history = self.request_history[-self.max_history :]

        # Update stats
        self._update_stats(metrics)

        # Log errors
        if not success:
            logger.warning(
                f"OpenRouter request failed: model={model}, "
                f"error_type={error_type}, error={error_message}"
            )

    def _update_stats(self, metrics: RequestMetrics):
        """Update aggregated statistics"""
        self.stats.total_requests += 1

        if metrics.success:
            self.stats.successful_requests += 1
        else:
            self.stats.failed_requests += 1
            if metrics.error_type:
                self.stats.error_counts[metrics.error_type] = (
                    self.stats.error_counts.get(metrics.error_type, 0) + 1
                )

        self.stats.total_tokens += metrics.total_tokens
        self.stats.total_prompt_tokens += metrics.prompt_tokens
        self.stats.total_completion_tokens += metrics.completion_tokens

        # Update model usage
        self.stats.model_usage[metrics.model] = (
            self.stats.model_usage.get(metrics.model, 0) + 1
        )

        # Update average latency (simple moving average)
        if self.stats.total_requests == 1:
            self.stats.average_latency_ms = metrics.latency_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats.average_latency_ms = (
                alpha * metrics.latency_ms + (1 - alpha) * self.stats.average_latency_ms
            )

    def get_stats(self, window_minutes: Optional[int] = None) -> UsageStats:
        """
        Get usage statistics.

        Args:
            window_minutes: Optional time window in minutes (None = all time)

        Returns:
            Usage statistics
        """
        if window_minutes is None:
            return self.stats

        # Calculate stats for time window
        cutoff_time = time.time() - (window_minutes * 60)
        recent_requests = [
            r for r in self.request_history if r.timestamp >= cutoff_time
        ]

        if not recent_requests:
            return UsageStats()

        # Aggregate recent requests
        stats = UsageStats()
        for req in recent_requests:
            stats.total_requests += 1
            if req.success:
                stats.successful_requests += 1
            else:
                stats.failed_requests += 1
                if req.error_type:
                    stats.error_counts[req.error_type] = (
                        stats.error_counts.get(req.error_type, 0) + 1
                    )

            stats.total_tokens += req.total_tokens
            stats.total_prompt_tokens += req.prompt_tokens
            stats.total_completion_tokens += req.completion_tokens
            stats.model_usage[req.model] = stats.model_usage.get(req.model, 0) + 1

        # Calculate average latency
        if recent_requests:
            stats.average_latency_ms = sum(r.latency_ms for r in recent_requests) / len(
                recent_requests
            )

        return stats

    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by type"""
        return self.stats.error_counts.copy()

    def get_model_usage(self) -> Dict[str, int]:
        """Get usage count by model"""
        return self.stats.model_usage.copy()

    def get_success_rate(self) -> float:
        """Get overall success rate (0.0 to 1.0)"""
        if self.stats.total_requests == 0:
            return 1.0
        return self.stats.successful_requests / self.stats.total_requests

    def check_health(self) -> Dict[str, Any]:
        """
        Check overall health based on recent metrics.

        Returns:
            Health status dictionary
        """
        # Get stats for last 10 minutes
        recent_stats = self.get_stats(window_minutes=10)

        if recent_stats.total_requests == 0:
            return {
                "status": "unknown",
                "message": "No recent requests",
                "success_rate": 1.0,
            }

        success_rate = (
            recent_stats.successful_requests / recent_stats.total_requests
            if recent_stats.total_requests > 0
            else 1.0
        )

        # Determine health status
        if success_rate >= 0.95:
            status = "healthy"
            message = "All systems operational"
        elif success_rate >= 0.80:
            status = "degraded"
            message = "Some requests failing"
        else:
            status = "unhealthy"
            message = "High failure rate detected"

        return {
            "status": status,
            "message": message,
            "success_rate": success_rate,
            "total_requests": recent_stats.total_requests,
            "failed_requests": recent_stats.failed_requests,
            "average_latency_ms": recent_stats.average_latency_ms,
            "errors": recent_stats.error_counts,
        }

    def clear_history(self):
        """Clear request history and reset stats"""
        self.request_history.clear()
        self.stats = UsageStats()
        logger.info("Cleared OpenRouter monitoring history")


# Global monitor instance
_global_monitor: Optional[OpenRouterMonitor] = None


def get_monitor() -> OpenRouterMonitor:
    """Get or create global monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = OpenRouterMonitor()
    return _global_monitor
