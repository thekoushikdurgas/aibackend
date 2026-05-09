"""
WebSocket Metrics Collection
Tracks connections, throughput, latency, and token usage.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from collections import defaultdict, deque

from app.core.connection_manager import connection_manager

logger = logging.getLogger(__name__)


class WebSocketMetrics:
    """
    Collect and track WebSocket-specific metrics.
    """

    def __init__(self):
        self.active_connections = 0
        self.total_connections = 0
        self.total_disconnections = 0
        self.message_count = 0
        self.message_history: deque = deque(maxlen=1000)  # Last 1000 messages
        self.token_usage: Dict[str, int] = defaultdict(int)  # provider -> tokens
        self.latency_history: deque = deque(maxlen=100)  # Last 100 latencies
        self.error_count = 0
        self.start_time = datetime.utcnow()

    def record_connection(self):
        """Record a new connection"""
        self.active_connections = connection_manager.get_connection_count()
        self.total_connections += 1

    def record_disconnection(self):
        """Record a disconnection"""
        self.active_connections = connection_manager.get_connection_count()
        self.total_disconnections += 1

    def record_message(self, size_bytes: int = 0):
        """Record a message"""
        self.message_count += 1
        self.message_history.append(
            {"timestamp": datetime.utcnow(), "size_bytes": size_bytes}
        )

    def record_tokens(self, provider: str, tokens: int):
        """Record token usage"""
        self.token_usage[provider] += tokens

    def record_latency(self, latency_ms: float):
        """Record latency in milliseconds"""
        self.latency_history.append(
            {"timestamp": datetime.utcnow(), "latency_ms": latency_ms}
        )

    def record_error(self):
        """Record an error"""
        self.error_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current metrics statistics.

        Returns:
            Dictionary with metrics
        """
        now = datetime.utcnow()
        uptime_seconds = (now - self.start_time).total_seconds()

        # Calculate message throughput (messages per second)
        if len(self.message_history) > 1:
            time_span = (
                self.message_history[-1]["timestamp"]
                - self.message_history[0]["timestamp"]
            ).total_seconds()
            if time_span > 0:
                throughput = len(self.message_history) / time_span
            else:
                throughput = 0
        else:
            throughput = 0

        # Calculate average latency
        if self.latency_history:
            avg_latency = sum(m["latency_ms"] for m in self.latency_history) / len(
                self.latency_history
            )
            min_latency = min(m["latency_ms"] for m in self.latency_history)
            max_latency = max(m["latency_ms"] for m in self.latency_history)
        else:
            avg_latency = 0
            min_latency = 0
            max_latency = 0

        # Calculate error rate
        error_rate = self.error_count / max(self.message_count, 1)

        return {
            "active_connections": self.active_connections,
            "total_connections": self.total_connections,
            "total_disconnections": self.total_disconnections,
            "message_count": self.message_count,
            "messages_per_second": throughput,
            "token_usage": dict(self.token_usage),
            "total_tokens": sum(self.token_usage.values()),
            "latency": {
                "average_ms": avg_latency,
                "min_ms": min_latency,
                "max_ms": max_latency,
                "samples": len(self.latency_history),
            },
            "error_count": self.error_count,
            "error_rate": error_rate,
            "uptime_seconds": uptime_seconds,
        }

    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics per provider.

        Returns:
            Dict mapping provider name to stats
        """
        stats = {}
        for provider, tokens in self.token_usage.items():
            stats[provider] = {
                "total_tokens": tokens,
                "percentage": tokens / max(sum(self.token_usage.values()), 1) * 100,
            }
        return stats

    def reset(self):
        """Reset all metrics"""
        self.active_connections = 0
        self.total_connections = 0
        self.total_disconnections = 0
        self.message_count = 0
        self.message_history.clear()
        self.token_usage.clear()
        self.latency_history.clear()
        self.error_count = 0
        self.start_time = datetime.utcnow()


# Global metrics instance
websocket_metrics = WebSocketMetrics()
