"""
Tests for benchmark orchestration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.benchmark import BenchmarkOrchestrator
from app.services.llm.base import LLMConfig


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_metrics_collector():
    """Mock metrics collector"""
    collector = AsyncMock()
    collector.create_benchmark_run = AsyncMock(return_value="benchmark_run_123")
    collector.record_benchmark = AsyncMock(return_value="metric_123")
    collector.complete_benchmark_run = AsyncMock()
    return collector


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider"""
    provider = AsyncMock()
    provider.generate = AsyncMock(return_value=MagicMock(
        text="Test response",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    ))
    provider.stream = AsyncMock()
    return provider


@pytest.mark.asyncio
@patch("app.services.benchmark.get_llm_provider")
@patch("app.services.benchmark.MetricsCollector")
async def test_run_single_benchmark(
    mock_collector_class,
    mock_get_provider,
    mock_db,
    mock_llm_provider
):
    """Test single benchmark execution"""
    mock_collector = AsyncMock()
    mock_collector.create_benchmark_run = AsyncMock(return_value="run_123")
    mock_collector.record_benchmark = AsyncMock(return_value="metric_123")
    mock_collector.complete_benchmark_run = AsyncMock()
    mock_collector_class.return_value = mock_collector
    
    mock_get_provider.return_value = mock_llm_provider
    
    orchestrator = BenchmarkOrchestrator(mock_db)
    
    config = LLMConfig(model="test-model", max_tokens=100)
    result = await orchestrator.run_single_benchmark(
        provider="fireworks",
        model="test-model",
        prompt="Test prompt",
        config=config,
        streaming=False
    )
    
    assert result["provider"] == "fireworks"
    assert result["success"] is True
    assert "total_time" in result
    assert "tokens_generated" in result


@pytest.mark.asyncio
@patch("app.services.benchmark.get_llm_provider")
@patch("app.services.benchmark.MetricsCollector")
async def test_run_comparative_benchmark(
    mock_collector_class,
    mock_get_provider,
    mock_db,
    mock_llm_provider
):
    """Test comparative benchmark execution"""
    mock_collector = AsyncMock()
    mock_collector.create_benchmark_run = AsyncMock(return_value="run_123")
    mock_collector.record_benchmark = AsyncMock(return_value="metric_123")
    mock_collector.complete_benchmark_run = AsyncMock()
    mock_collector_class.return_value = mock_collector
    
    mock_get_provider.return_value = mock_llm_provider
    
    orchestrator = BenchmarkOrchestrator(mock_db)
    
    config = LLMConfig(model="test-model", max_tokens=100)
    result = await orchestrator.run_comparative_benchmark(
        providers=["fireworks", "groq"],
        prompt="Test prompt",
        config=config
    )
    
    assert result["run_id"] == "run_123"
    assert len(result["results"]) == 2
    assert "rankings" in result


@pytest.mark.asyncio
@patch("app.services.benchmark.get_llm_provider")
@patch("app.services.benchmark.MetricsCollector")
async def test_stress_test(
    mock_collector_class,
    mock_get_provider,
    mock_db,
    mock_llm_provider
):
    """Test stress test execution"""
    mock_collector = AsyncMock()
    mock_collector.create_benchmark_run = AsyncMock(return_value="run_123")
    mock_collector.complete_benchmark_run = AsyncMock()
    mock_collector_class.return_value = mock_collector
    
    mock_get_provider.return_value = mock_llm_provider
    
    orchestrator = BenchmarkOrchestrator(mock_db)
    
    config = LLMConfig(model="test-model", max_tokens=100)
    
    # Use short duration for testing
    result = await orchestrator.run_stress_test(
        provider="fireworks",
        model="test-model",
        prompt="Test prompt",
        concurrent_requests=2,
        duration_seconds=2,
        config=config
    )
    
    assert result["provider"] == "fireworks"
    assert "total_requests" in result
    assert "successful_requests" in result
    assert "error_rate" in result
