"""
Metrics Analytics Service
Provides data aggregation, percentile calculation, and performance analysis
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import statistics

from app.models.metrics import ProviderMetric

logger = logging.getLogger(__name__)


class MetricsAnalytics:
    """Analytics and reporting for metrics data"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_percentiles(
        self, data: List[float], percentiles: List[float] = [50, 75, 90, 95, 99]
    ) -> Dict[str, float]:
        """
        Calculate percentiles for a list of values.

        Args:
            data: List of numeric values
            percentiles: List of percentile values to calculate (0-100)

        Returns:
            Dictionary mapping percentile names to values
        """
        if not data:
            return {f"p{p}": 0.0 for p in percentiles}

        sorted_data = sorted(data)
        result = {}

        for p in percentiles:
            index = (p / 100.0) * (len(sorted_data) - 1)
            lower = int(index)
            upper = min(lower + 1, len(sorted_data) - 1)
            weight = index - lower

            if lower == upper:
                value = sorted_data[lower]
            else:
                value = sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

            result[f"p{p}"] = round(value, 3)

        return result

    async def get_provider_percentiles(
        self,
        provider: str,
        metric: str = "tokens_per_second",
        days: int = 7,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get percentile statistics for a provider.

        Args:
            provider: Provider name
            metric: Metric to analyze ('tokens_per_second', 'ttft', 'total_time')
            days: Number of days to look back
            model: Optional model filter

        Returns:
            Dictionary with percentile statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

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
            metrics = result.scalars().all()

            # Extract metric values
            values: List[float] = []
            for m in metrics:
                if metric == "tokens_per_second":
                    value = m.tokens_per_second
                elif metric == "ttft":
                    value = m.ttft
                elif metric == "total_time":
                    value = m.total_time
                else:
                    continue

                if value is not None:
                    values.append(float(value))

            if not values:
                return {
                    "provider": provider,
                    "model": model,
                    "metric": metric,
                    "count": 0,
                    "percentiles": {},
                }

            percentiles = await self.calculate_percentiles(values)

            return {
                "provider": provider,
                "model": model,
                "metric": metric,
                "count": len(values),
                "mean": round(statistics.mean(values), 3),
                "median": round(statistics.median(values), 3),
                "stdev": round(statistics.stdev(values), 3) if len(values) > 1 else 0.0,
                "min": round(min(values), 3),
                "max": round(max(values), 3),
                "percentiles": percentiles,
            }

        except Exception as e:
            logger.error(f"Error calculating percentiles: {e}", exc_info=True)
            raise

    async def detect_performance_degradation(
        self,
        provider: str,
        metric: str = "tokens_per_second",
        days: int = 7,
        threshold_percent: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Detect if provider performance has degraded.

        Args:
            provider: Provider name
            metric: Metric to check
            days: Number of days to compare
            threshold_percent: Percentage drop to consider degradation

        Returns:
            Dictionary with degradation analysis
        """
        try:
            # Get recent performance (last 2 days)
            recent_cutoff = datetime.utcnow() - timedelta(days=2)
            older_cutoff = datetime.utcnow() - timedelta(days=days)

            # Recent metrics
            recent_query = select(ProviderMetric).where(
                and_(
                    ProviderMetric.provider == provider,
                    ProviderMetric.created_at >= recent_cutoff,
                    ProviderMetric.success.is_(True),
                )
            )

            # Older metrics (for comparison)
            older_query = select(ProviderMetric).where(
                and_(
                    ProviderMetric.provider == provider,
                    ProviderMetric.created_at >= older_cutoff,
                    ProviderMetric.created_at < recent_cutoff,
                    ProviderMetric.success.is_(True),
                )
            )

            recent_result = await self.db.execute(recent_query)
            older_result = await self.db.execute(older_query)

            recent_metrics = recent_result.scalars().all()
            older_metrics = older_result.scalars().all()

            # Extract values
            def get_values(metrics_list):
                values = []
                for m in metrics_list:
                    if metric == "tokens_per_second":
                        value = m.tokens_per_second
                    elif metric == "ttft":
                        value = m.ttft
                    elif metric == "total_time":
                        value = m.total_time
                    else:
                        continue
                    if value is not None:
                        values.append(value)
                return values

            recent_values = get_values(recent_metrics)
            older_values = get_values(older_metrics)

            if not recent_values or not older_values:
                return {
                    "provider": provider,
                    "degradation_detected": False,
                    "reason": "insufficient_data",
                }

            recent_avg = statistics.mean(recent_values)
            older_avg = statistics.mean(older_values)

            if older_avg == 0:
                return {
                    "provider": provider,
                    "degradation_detected": False,
                    "reason": "no_baseline",
                }

            percent_change = ((recent_avg - older_avg) / older_avg) * 100

            # For metrics where lower is better (ttft, total_time), degradation is increase
            # For metrics where higher is better (tokens_per_second), degradation is decrease
            if metric in ["ttft", "total_time"]:
                degradation_detected = percent_change > threshold_percent
            else:
                degradation_detected = percent_change < -threshold_percent

            return {
                "provider": provider,
                "metric": metric,
                "degradation_detected": degradation_detected,
                "recent_avg": round(recent_avg, 3),
                "older_avg": round(older_avg, 3),
                "percent_change": round(percent_change, 2),
                "threshold": threshold_percent,
                "recent_count": len(recent_values),
                "older_count": len(older_values),
            }

        except Exception as e:
            logger.error(f"Error detecting performance degradation: {e}", exc_info=True)
            raise

    async def generate_comparison_report(
        self, providers: List[str], days: int = 7
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive comparison report for multiple providers.

        Returns:
            Dictionary with comparison data
        """
        try:
            report: Dict[str, Any] = {
                "period_days": days,
                "generated_at": datetime.utcnow().isoformat(),
                "providers": [],
            }

            for provider in providers:
                # Get stats for each provider
                stats_query = select(
                    func.avg(ProviderMetric.tokens_per_second).label("avg_tps"),
                    func.avg(ProviderMetric.ttft).label("avg_ttft"),
                    func.avg(ProviderMetric.total_time).label("avg_total_time"),
                    func.count(ProviderMetric.id).label("total_runs"),
                    func.sum(ProviderMetric.total_tokens).label("total_tokens"),
                ).where(
                    and_(
                        ProviderMetric.provider == provider,
                        ProviderMetric.created_at
                        >= datetime.utcnow() - timedelta(days=days),
                        ProviderMetric.success.is_(True),
                    )
                )

                result = await self.db.execute(stats_query)
                row = result.first()

                if row and row.total_runs > 0:
                    report["providers"].append(
                        {
                            "provider": provider,
                            "avg_tokens_per_second": round(row.avg_tps or 0, 2),
                            "avg_ttft": round(row.avg_ttft or 0, 3),
                            "avg_total_time": round(row.avg_total_time or 0, 3),
                            "total_runs": row.total_runs,
                            "total_tokens": row.total_tokens or 0,
                        }
                    )

            # Sort by tokens_per_second (descending)
            report["providers"].sort(
                key=lambda x: x["avg_tokens_per_second"], reverse=True
            )

            # Add rankings
            for idx, provider_data in enumerate(report["providers"], 1):
                provider_data["rank"] = idx

            return report

        except Exception as e:
            logger.error(f"Error generating comparison report: {e}", exc_info=True)
            raise

    async def export_metrics(
        self, format: str = "json", provider: Optional[str] = None, days: int = 30
    ) -> str:
        """
        Export metrics data in specified format.

        Args:
            format: Export format ('json', 'csv')
            provider: Optional provider filter
            days: Number of days to export

        Returns:
            Exported data as string
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            query = select(ProviderMetric).where(
                ProviderMetric.created_at >= cutoff_date
            )

            if provider:
                query = query.where(ProviderMetric.provider == provider)

            query = query.order_by(ProviderMetric.created_at)

            result = await self.db.execute(query)
            metrics = result.scalars().all()

            if format == "json":
                import json

                data = [
                    {
                        "id": m.id,
                        "provider": m.provider,
                        "model": m.model,
                        "ttft": m.ttft,
                        "total_time": m.total_time,
                        "tokens_per_second": m.tokens_per_second,
                        "total_tokens": m.total_tokens,
                        "success": m.success,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in metrics
                ]
                return json.dumps(data, indent=2)

            elif format == "csv":
                import csv
                import io

                output = io.StringIO()
                writer = csv.writer(output)

                # Header
                writer.writerow(
                    [
                        "id",
                        "provider",
                        "model",
                        "ttft",
                        "total_time",
                        "tokens_per_second",
                        "total_tokens",
                        "success",
                        "created_at",
                    ]
                )

                # Data rows
                for m in metrics:
                    writer.writerow(
                        [
                            m.id,
                            m.provider,
                            m.model,
                            m.ttft,
                            m.total_time,
                            m.tokens_per_second,
                            m.total_tokens,
                            m.success,
                            m.created_at.isoformat(),
                        ]
                    )

                return output.getvalue()

            else:
                raise ValueError(f"Unsupported format: {format}")

        except Exception as e:
            logger.error(f"Error exporting metrics: {e}", exc_info=True)
            raise
