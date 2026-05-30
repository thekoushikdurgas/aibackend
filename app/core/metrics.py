"""
Prometheus Metrics Instrumentation for DurgasOS.
"""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# 1. HTTP Request Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "durgasos_http_requests_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "durgasos_http_request_duration_seconds",
    "HTTP request latencies in seconds",
    ["method", "endpoint"]
)

# 2. Kafka Event Bus Metrics
KAFKA_PUBLISHED_EVENTS_TOTAL = Counter(
    "durgasos_kafka_published_events_total",
    "Total count of events published to Kafka",
    ["topic"]
)

KAFKA_CONSUMED_EVENTS_TOTAL = Counter(
    "durgasos_kafka_consumed_events_total",
    "Total count of events consumed from Kafka",
    ["topic", "group_id"]
)

# 3. AI Memory / Vector Store Metrics
CHROMADB_QUERY_DURATION_SECONDS = Histogram(
    "durgasos_chromadb_query_duration_seconds",
    "ChromaDB query latencies in seconds",
    ["operation"]
)

# 4. Redis Cache Metrics
REDIS_CACHE_ACCESS_TOTAL = Counter(
    "durgasos_redis_cache_access_total",
    "Total count of Redis cache lookups",
    ["result"]  # "hit" or "miss"
)


def get_metrics_response() -> Response:
    """Generate latest metrics from registry as a FastAPI response."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
