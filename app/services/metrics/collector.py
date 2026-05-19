"""
Metrics Collector Service
Handles recording and retrieving benchmark metrics
"""

import logging
from datetime import timedelta
from typing import Dict, List, Optional, Any, cast
from sqlalchemy import select, and_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import BenchmarkRun, ProviderMetric, LatencyHistory, ErrorLog
from app.utils.helpers import generate_id, utc_now

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and manage benchmark metrics"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_benchmark(
        self,
        provider: str,
        model: str,
        prompt: str,
        ttft: Optional[float],
        total_time: float,
        tokens_generated: int,
        tokens_per_second: Optional[float],
        streaming: bool,
        success: bool,
        prompt_tokens: int = 0,
        total_tokens: int = 0,
        request_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        benchmark_run_id: Optional[str] = None,
    ) -> str:
        """
        Record a benchmark result.

        Returns:
            The provider_metric_id
        """
        try:
            # Create provider metric record
            metric_id = generate_id("metric")

            provider_metric = ProviderMetric(
                id=metric_id,
                benchmark_run_id=benchmark_run_id,
                provider=provider,
                model=model,
                ttft=ttft,
                total_time=total_time,
                prompt_tokens=prompt_tokens,
                completion_tokens=tokens_generated,
                total_tokens=total_tokens or (prompt_tokens + tokens_generated),
                tokens_per_second=tokens_per_second,
                request_size_bytes=request_size_bytes,
                response_size_bytes=response_size_bytes,
                success=success,
                error_type=error_type,
                error_message=error,
                response_data=response_data,
                extra_metadata=extra_metadata,
                created_at=utc_now(),
            )

            self.db.add(provider_metric)

            # Create latency history entry
            latency_history = LatencyHistory(
                id=generate_id("latency"),
                provider_metric_id=metric_id,
                provider=provider,
                model=model,
                ttft=ttft,
                total_time=total_time,
                tokens_per_second=tokens_per_second,
                success=success,
                period="point",
                period_start=utc_now(),
                created_at=utc_now(),
            )

            self.db.add(latency_history)

            # If there was an error, log it
            if not success and error:
                error_log = ErrorLog(
                    id=generate_id("error"),
                    provider=provider,
                    model=model,
                    benchmark_run_id=benchmark_run_id,
                    error_type=error_type or "unknown",
                    error_message=error,
                    created_at=utc_now(),
                )
                self.db.add(error_log)

            await self.db.commit()
            logger.info(
                f"Recorded benchmark metric: {metric_id} for {provider}/{model}"
            )
            return metric_id

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error recording benchmark: {e}", exc_info=True)
            raise

    async def create_benchmark_run(
        self,
        run_type: str,
        prompt: str,
        config: Optional[Dict[str, Any]] = None,
        streaming: bool = False,
    ) -> str:
        """Create a new benchmark run record"""
        try:
            run_id = generate_id("benchmark")
            benchmark_run = BenchmarkRun(
                id=run_id,
                run_type=run_type,
                prompt=prompt,
                config=config or {},
                streaming=streaming,
                status="running",
                created_at=utc_now(),
            )
            self.db.add(benchmark_run)
            await self.db.commit()
            return run_id
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating benchmark run: {e}", exc_info=True)
            raise

    async def complete_benchmark_run(
        self,
        run_id: str,
        status: str = "completed",
        error_message: Optional[str] = None,
    ):
        """Mark a benchmark run as completed"""
        try:
            result = await self.db.execute(
                select(BenchmarkRun).where(BenchmarkRun.id == run_id)
            )
            benchmark_run = result.scalar_one_or_none()
            if benchmark_run:
                values: Dict[str, Any] = {
                    "status": status,
                    "completed_at": utc_now(),
                }
                if error_message:
                    values["error_message"] = error_message
                await self.db.execute(
                    update(BenchmarkRun)
                    .where(BenchmarkRun.id == run_id)
                    .values(**values)
                )
                await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error completing benchmark run: {e}", exc_info=True)
            raise

    async def get_provider_stats(
        self, provider: str, days: int = 7, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for a provider.

        Returns:
            Dictionary with aggregated metrics
        """
        try:
            cutoff_date = utc_now() - timedelta(days=days)

            # Build query
            query = select(ProviderMetric).where(
                and_(
                    ProviderMetric.provider == provider,
                    ProviderMetric.created_at >= cutoff_date,
                    ProviderMetric.success.is_(True),
                )
            )

            if model:
                query = query.where(ProviderMetric.model == model)

            result = await self.db.execute(query)
            metrics: List[ProviderMetric] = list(result.scalars().all())

            if not metrics:
                return {
                    "provider": provider,
                    "model": model,
                    "total_runs": 0,
                    "success_rate": 0.0,
                    "avg_ttft": None,
                    "avg_total_time": None,
                    "avg_tokens_per_second": None,
                    "total_tokens": 0,
                }

            # Calculate aggregations
            total_runs = len(metrics)
            successful_runs = sum(1 for m in metrics if m.success)
            success_rate = (successful_runs / total_runs) * 100 if total_runs > 0 else 0

            ttft_values = [
                float(cast(Any, m.ttft)) for m in metrics if m.ttft is not None
            ]
            total_time_values = [
                float(cast(Any, m.total_time)) for m in metrics if m.total_time
            ]
            tps_values = [
                float(cast(Any, m.tokens_per_second))
                for m in metrics
                if m.tokens_per_second is not None
            ]

            total_tokens = sum(m.total_tokens for m in metrics)

            return {
                "provider": provider,
                "model": model,
                "total_runs": total_runs,
                "success_rate": round(success_rate, 2),
                "avg_ttft": (
                    round(sum(ttft_values) / len(ttft_values), 3)
                    if ttft_values
                    else None
                ),
                "min_ttft": round(min(ttft_values), 3) if ttft_values else None,
                "max_ttft": round(max(ttft_values), 3) if ttft_values else None,
                "avg_total_time": (
                    round(sum(total_time_values) / len(total_time_values), 3)
                    if total_time_values
                    else None
                ),
                "min_total_time": (
                    round(min(total_time_values), 3) if total_time_values else None
                ),
                "max_total_time": (
                    round(max(total_time_values), 3) if total_time_values else None
                ),
                "avg_tokens_per_second": (
                    round(sum(tps_values) / len(tps_values), 2) if tps_values else None
                ),
                "min_tokens_per_second": (
                    round(min(tps_values), 2) if tps_values else None
                ),
                "max_tokens_per_second": (
                    round(max(tps_values), 2) if tps_values else None
                ),
                "total_tokens": total_tokens,
                "period_days": days,
            }

        except Exception as e:
            logger.error(f"Error getting provider stats: {e}", exc_info=True)
            raise

    async def get_model_comparison(
        self, model_name: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Compare the same model across different providers.

        Returns:
            List of provider stats for the model
        """
        try:
            cutoff_date = utc_now() - timedelta(days=days)

            # Get all providers that have used this model
            query = (
                select(ProviderMetric.provider)
                .where(
                    and_(
                        ProviderMetric.model == model_name,
                        ProviderMetric.created_at >= cutoff_date,
                    )
                )
                .distinct()
            )

            result = await self.db.execute(query)
            providers = result.scalars().all()

            # Get stats for each provider
            comparisons = []
            for provider in providers:
                stats = await self.get_provider_stats(
                    provider, days=days, model=model_name
                )
                comparisons.append(stats)

            # Sort by avg_tokens_per_second (descending)
            comparisons.sort(
                key=lambda x: x.get("avg_tokens_per_second") or 0, reverse=True
            )

            return comparisons

        except Exception as e:
            logger.error(f"Error getting model comparison: {e}", exc_info=True)
            raise

    async def get_historical_trends(
        self,
        provider: str,
        metric: str = "tokens_per_second",
        days: int = 30,
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get historical trend data for a provider.

        Args:
            provider: Provider name
            metric: Metric to track ('tokens_per_second', 'ttft', 'total_time')
            days: Number of days to look back
            model: Optional model filter

        Returns:
            List of daily aggregated metrics
        """
        try:
            cutoff_date = utc_now() - timedelta(days=days)

            query = select(LatencyHistory).where(
                and_(
                    LatencyHistory.provider == provider,
                    LatencyHistory.created_at >= cutoff_date,
                    LatencyHistory.success.is_(True),
                )
            )

            if model:
                query = query.where(LatencyHistory.model == model)

            query = query.order_by(LatencyHistory.period_start)

            result = await self.db.execute(query)
            history = result.scalars().all()

            # Group by date and aggregate
            daily_data = {}
            for entry in history:
                date_key = entry.period_start.date()
                if date_key not in daily_data:
                    daily_data[date_key] = {
                        "date": date_key.isoformat(),
                        "values": [],
                        "count": 0,
                    }

                # Get the metric value
                if metric == "tokens_per_second":
                    value = entry.tokens_per_second
                elif metric == "ttft":
                    value = entry.ttft
                elif metric == "total_time":
                    value = entry.total_time
                else:
                    continue

                if value is not None:
                    daily_data[date_key]["values"].append(value)
                    daily_data[date_key]["count"] += 1

            # Calculate averages
            trends = []
            for date_key, data in sorted(daily_data.items()):
                if data["values"]:
                    trends.append(
                        {
                            "date": data["date"],
                            "avg": round(sum(data["values"]) / len(data["values"]), 3),
                            "min": round(min(data["values"]), 3),
                            "max": round(max(data["values"]), 3),
                            "count": data["count"],
                        }
                    )

            return trends

        except Exception as e:
            logger.error(f"Error getting historical trends: {e}", exc_info=True)
            raise

    async def get_recent_benchmarks(
        self, limit: int = 50, provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent benchmark runs"""
        try:
            query = (
                select(BenchmarkRun)
                .order_by(desc(BenchmarkRun.created_at))
                .limit(limit)
            )

            if provider:
                # Join with provider_metrics to filter by provider
                query = (
                    query.join(ProviderMetric)
                    .where(ProviderMetric.provider == provider)
                    .distinct()
                )

            result = await self.db.execute(query)
            runs = result.scalars().all()

            out: List[Dict[str, Any]] = []
            for run in runs:
                p = cast(str, getattr(run, "prompt", "") or "")
                out.append(
                    {
                        "id": run.id,
                        "run_type": run.run_type,
                        "prompt": (p[:100] + "..." if len(p) > 100 else p),
                        "status": run.status,
                        "created_at": run.created_at.isoformat(),
                        "completed_at": (
                            run.completed_at.isoformat() if run.completed_at else None
                        ),
                    }
                )
            return out

        except Exception as e:
            logger.error(f"Error getting recent benchmarks: {e}", exc_info=True)
            raise

    async def get_benchmark_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a benchmark run"""
        try:
            # Get the benchmark run
            result = await self.db.execute(
                select(BenchmarkRun).where(BenchmarkRun.id == run_id)
            )
            benchmark_run = result.scalar_one_or_none()

            if not benchmark_run:
                return None

            # Get all metrics for this run
            pm_result = await self.db.execute(
                select(ProviderMetric)
                .where(ProviderMetric.benchmark_run_id == run_id)
                .order_by(ProviderMetric.created_at)
            )
            metrics: List[ProviderMetric] = list(pm_result.scalars().all())

            return {
                "id": benchmark_run.id,
                "run_type": benchmark_run.run_type,
                "prompt": benchmark_run.prompt,
                "config": benchmark_run.config,
                "streaming": benchmark_run.streaming,
                "status": benchmark_run.status,
                "created_at": benchmark_run.created_at.isoformat(),
                "completed_at": (
                    benchmark_run.completed_at.isoformat()
                    if benchmark_run.completed_at
                    else None
                ),
                "error_message": benchmark_run.error_message,
                "results": [
                    {
                        "id": m.id,
                        "provider": m.provider,
                        "model": m.model,
                        "ttft": m.ttft,
                        "total_time": m.total_time,
                        "tokens_per_second": m.tokens_per_second,
                        "total_tokens": m.total_tokens,
                        "success": m.success,
                        "error_message": m.error_message,
                    }
                    for m in metrics
                ],
            }

        except Exception as e:
            logger.error(f"Error getting benchmark run details: {e}", exc_info=True)
            raise
