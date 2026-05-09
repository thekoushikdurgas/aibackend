"""
Database models for metrics and benchmarking
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    Text,
    DateTime,
    Index,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy ORM base for metrics tables."""

    pass


class BenchmarkRun(Base):
    """Track individual benchmark test runs"""

    __tablename__ = "benchmark_runs"

    id = Column(String, primary_key=True)
    run_type = Column(String, nullable=False)  # 'single', 'compare', 'stress'
    prompt = Column(Text, nullable=False)
    config = Column(JSON)  # Store LLM config as JSON
    streaming = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")  # 'running', 'completed', 'failed'
    error_message = Column(Text, nullable=True)

    # Relationships
    results = relationship(
        "ProviderMetric", back_populates="benchmark_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_benchmark_runs_created_at", "created_at"),
        Index("idx_benchmark_runs_status", "status"),
    )


class ProviderMetric(Base):
    """Store detailed metrics per provider/model combination"""

    __tablename__ = "provider_metrics"

    id = Column(String, primary_key=True)
    benchmark_run_id = Column(
        String, ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False
    )
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)

    # Timing metrics
    ttft = Column(Float, nullable=True)  # Time to First Token (seconds)
    total_time = Column(Float, nullable=False)  # Total response time (seconds)

    # Token metrics
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    tokens_per_second = Column(Float, nullable=True)

    # Request/Response metrics
    request_size_bytes = Column(Integer, nullable=True)
    response_size_bytes = Column(Integer, nullable=True)

    # Status
    success = Column(Boolean, default=True)
    error_type = Column(
        String, nullable=True
    )  # 'timeout', 'rate_limit', 'api_error', etc.
    error_message = Column(Text, nullable=True)

    # Additional metadata
    response_data = Column(JSON, nullable=True)  # Store full response for analysis
    extra_metadata = Column(JSON, nullable=True)  # Additional provider-specific data

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    benchmark_run = relationship("BenchmarkRun", back_populates="results")
    latency_history = relationship(
        "LatencyHistory", back_populates="provider_metric", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_provider_metrics_provider", "provider"),
        Index("idx_provider_metrics_model", "model"),
        Index("idx_provider_metrics_created_at", "created_at"),
        Index("idx_provider_metrics_success", "success"),
        Index("idx_provider_metrics_benchmark_run", "benchmark_run_id"),
    )


class LatencyHistory(Base):
    """Time-series data for historical latency analysis"""

    __tablename__ = "latency_history"

    id = Column(String, primary_key=True)
    provider_metric_id = Column(
        String, ForeignKey("provider_metrics.id", ondelete="CASCADE"), nullable=False
    )
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)

    # Metrics at this point in time
    ttft = Column(Float, nullable=True)
    total_time = Column(Float, nullable=False)
    tokens_per_second = Column(Float, nullable=True)
    success = Column(Boolean, default=True)

    # Aggregation period (for daily/hourly summaries)
    period = Column(String, nullable=True)  # 'hour', 'day', 'week'
    period_start = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    provider_metric = relationship("ProviderMetric", back_populates="latency_history")

    __table_args__ = (
        Index("idx_latency_history_provider", "provider"),
        Index("idx_latency_history_model", "model"),
        Index("idx_latency_history_period_start", "period_start"),
        Index("idx_latency_history_created_at", "created_at"),
        Index(
            "idx_latency_history_provider_model_period",
            "provider",
            "model",
            "period",
            "period_start",
        ),
    )


class ErrorLog(Base):
    """Track failures and issues for debugging"""

    __tablename__ = "error_logs"

    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=True)
    benchmark_run_id = Column(
        String, ForeignKey("benchmark_runs.id", ondelete="SET NULL"), nullable=True
    )

    error_type = Column(
        String, nullable=False
    )  # 'timeout', 'rate_limit', 'api_error', 'network_error', etc.
    error_message = Column(Text, nullable=False)
    error_details = Column(JSON, nullable=True)  # Stack trace, request details, etc.

    # Request context
    request_url = Column(String, nullable=True)
    request_method = Column(String, nullable=True)
    request_headers = Column(JSON, nullable=True)
    request_body = Column(JSON, nullable=True)

    # Response context (if available)
    response_status = Column(Integer, nullable=True)
    response_headers = Column(JSON, nullable=True)
    response_body = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_error_logs_provider", "provider"),
        Index("idx_error_logs_error_type", "error_type"),
        Index("idx_error_logs_created_at", "created_at"),
        Index("idx_error_logs_benchmark_run", "benchmark_run_id"),
    )


class CohereUsage(Base):
    """Track Cohere API usage"""

    __tablename__ = "cohere_usage"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(
        String, nullable=False
    )  # chat, embed, classify, rerank, summarize
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    request_id = Column(String, nullable=True)
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_cohere_usage_endpoint", "endpoint"),
        Index("idx_cohere_usage_model", "model"),
        Index("idx_cohere_usage_created_at", "created_at"),
        Index("idx_cohere_usage_success", "success"),
    )


class CohereConnectorLog(Base):
    """Track Cohere connector usage"""

    __tablename__ = "cohere_connector_logs"

    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    documents_retrieved = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_cohere_connector_logs_connector_id", "connector_id"),
        Index("idx_cohere_connector_logs_created_at", "created_at"),
        Index("idx_cohere_connector_logs_success", "success"),
    )
