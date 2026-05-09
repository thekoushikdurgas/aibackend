"""
Benchmark Orchestrator Service
Handles execution of benchmark tests across providers
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import get_llm_provider, LLMConfig
from app.services.metrics.collector import MetricsCollector
from app.utils.helpers import generate_id

logger = logging.getLogger(__name__)


class BenchmarkOrchestrator:
    """Orchestrate benchmark execution across providers"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.metrics_collector = MetricsCollector(db)

    async def run_single_benchmark(
        self,
        provider: str,
        model: str,
        prompt: str,
        config: LLMConfig,
        streaming: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a benchmark test for a single provider/model.

        Returns:
            Dictionary with benchmark results
        """
        generate_id("benchmark")
        benchmark_run_id = await self.metrics_collector.create_benchmark_run(
            run_type="single",
            prompt=prompt,
            config={
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
            },
            streaming=streaming,
        )

        try:
            # Get provider instance
            llm_provider = get_llm_provider(provider)

            # Measure timing
            start_time = time.time()
            ttft = None
            first_chunk_time = None
            tokens_generated = 0
            prompt_tokens = 0
            total_tokens = 0
            error = None
            error_type = None
            success = True
            response_text = ""

            try:
                if streaming:
                    # Stream and measure TTFT
                    async for chunk in llm_provider.stream(
                        prompt=prompt, config=config, conversation_history=None
                    ):
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                            ttft = first_chunk_time - start_time

                        # Estimate tokens (rough: 1 token ≈ 4 chars)
                        tokens_generated += len(chunk) // 4
                        response_text += chunk
                else:
                    # Non-streaming
                    response = await llm_provider.generate(
                        prompt=prompt, config=config, conversation_history=None
                    )

                    response_text = response.text

                    # Extract token counts
                    if response.usage:
                        prompt_tokens = response.usage.get("prompt_tokens", 0)
                        tokens_generated = response.usage.get("completion_tokens", 0)
                        total_tokens = response.usage.get("total_tokens", 0)

                    # Estimate TTFT (rough: 10% of total time)
                    ttft = None  # Will be calculated after total_time

                total_time = time.time() - start_time

                # Calculate TTFT if not already measured
                if ttft is None:
                    ttft = total_time * 0.1  # Rough estimate

                # Calculate tokens per second
                tokens_per_second = (
                    tokens_generated / total_time if total_time > 0 else None
                )

            except Exception as e:
                success = False
                error = str(e)
                error_type = "api_error"
                total_time = time.time() - start_time
                logger.error(
                    f"Benchmark error for {provider}/{model}: {e}", exc_info=True
                )

            # Record metrics
            metric_id = await self.metrics_collector.record_benchmark(
                provider=provider,
                model=model,
                prompt=prompt,
                ttft=ttft,
                total_time=total_time,
                tokens_generated=tokens_generated,
                tokens_per_second=tokens_per_second,
                streaming=streaming,
                success=success,
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens or (prompt_tokens + tokens_generated),
                error=error,
                error_type=error_type,
                benchmark_run_id=benchmark_run_id,
            )

            # Complete benchmark run
            await self.metrics_collector.complete_benchmark_run(
                benchmark_run_id,
                status="completed" if success else "failed",
                error_message=error,
            )

            return {
                "run_id": benchmark_run_id,
                "metric_id": metric_id,
                "provider": provider,
                "model": model,
                "ttft": ttft,
                "total_time": total_time,
                "tokens_generated": tokens_generated,
                "tokens_per_second": tokens_per_second,
                "success": success,
                "error": error,
                "response_preview": response_text[:200] if response_text else None,
            }

        except Exception as e:
            logger.error(f"Benchmark orchestration error: {e}", exc_info=True)
            await self.metrics_collector.complete_benchmark_run(
                benchmark_run_id, status="failed", error_message=str(e)
            )
            raise

    async def run_comparative_benchmark(
        self,
        providers: List[str],
        prompt: str,
        config: LLMConfig,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run benchmark across multiple providers with the same prompt.

        Returns:
            Dictionary with comparative results
        """
        generate_id("benchmark")
        benchmark_run_id = await self.metrics_collector.create_benchmark_run(
            run_type="compare",
            prompt=prompt,
            config={
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
                "model": model,
            },
            streaming=False,
        )

        results = []
        tasks = []

        # Create benchmark tasks for all providers
        for provider in providers:
            task_config = LLMConfig(
                model=model or config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
            )

            task = self.run_single_benchmark(
                provider=provider,
                model=model or task_config.model or "default",
                prompt=prompt,
                config=task_config,
                streaming=False,
            )
            tasks.append(task)

        # Run all benchmarks concurrently
        try:
            benchmark_results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(benchmark_results):
                if isinstance(result, Exception):
                    logger.error(f"Benchmark failed for {providers[idx]}: {result}")
                    results.append(
                        {
                            "provider": providers[idx],
                            "model": model or "default",
                            "success": False,
                            "error": str(result),
                        }
                    )
                else:
                    results.append(result)

        except Exception as e:
            logger.error(f"Comparative benchmark error: {e}", exc_info=True)
            raise

        # Calculate rankings
        successful_results = [r for r in results if r.get("success", False)]

        # Rank by tokens_per_second (descending)
        successful_results.sort(
            key=lambda x: x.get("tokens_per_second") or 0, reverse=True
        )

        rankings = {}
        for rank, result in enumerate(successful_results, 1):
            rankings[result["provider"]] = rank

        # Find fastest and highest throughput
        fastest_provider = None
        highest_throughput = None

        if successful_results:
            # Fastest by total_time
            fastest = min(
                successful_results, key=lambda x: x.get("total_time", float("inf"))
            )
            fastest_provider = fastest["provider"]

            # Highest throughput by tokens_per_second
            highest = max(
                successful_results, key=lambda x: x.get("tokens_per_second") or 0
            )
            highest_throughput = highest["provider"]

        # Complete benchmark run
        await self.metrics_collector.complete_benchmark_run(
            benchmark_run_id, status="completed"
        )

        return {
            "run_id": benchmark_run_id,
            "prompt": prompt,
            "results": results,
            "fastest_provider": fastest_provider,
            "highest_throughput": highest_throughput,
            "rankings": rankings,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def run_stress_test(
        self,
        provider: str,
        model: str,
        prompt: str,
        concurrent_requests: int,
        duration_seconds: int,
        config: LLMConfig,
    ) -> Dict[str, Any]:
        """
        Run stress test with concurrent requests.

        Returns:
            Dictionary with stress test results
        """
        generate_id("benchmark")
        benchmark_run_id = await self.metrics_collector.create_benchmark_run(
            run_type="stress",
            prompt=prompt,
            config={
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
            },
            streaming=False,
        )

        try:
            llm_provider = get_llm_provider(provider)

            # Track results
            all_results = []
            errors = []
            start_time = time.time()
            end_time = start_time + duration_seconds

            # Semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(concurrent_requests)

            async def single_request():
                """Execute a single request"""
                async with semaphore:
                    if time.time() >= end_time:
                        return None

                    request_start = time.time()
                    try:
                        response = await llm_provider.generate(
                            prompt=prompt, config=config, conversation_history=None
                        )
                        request_time = time.time() - request_start

                        tokens = (
                            response.usage.get("completion_tokens", 0)
                            if response.usage
                            else 0
                        )

                        return {
                            "success": True,
                            "response_time": request_time,
                            "tokens": tokens,
                        }
                    except Exception as e:
                        request_time = time.time() - request_start
                        error_info = {
                            "error": str(e),
                            "response_time": request_time,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        errors.append(error_info)
                        return {
                            "success": False,
                            "response_time": request_time,
                            "error": str(e),
                        }

            # Run requests until duration is reached
            while time.time() < end_time:
                # Create batch of concurrent requests
                batch_tasks = [single_request() for _ in range(concurrent_requests)]
                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                for result in batch_results:
                    if isinstance(result, Exception):
                        errors.append({"error": str(result)})
                    elif result:
                        all_results.append(result)

                # Small delay to prevent overwhelming the API
                await asyncio.sleep(0.1)

            # Calculate statistics
            successful = [r for r in all_results if r.get("success", False)]
            failed = [r for r in all_results if not r.get("success", False)]

            total_requests = len(all_results)
            successful_requests = len(successful)
            failed_requests = len(failed)

            if successful:
                response_times = [r["response_time"] for r in successful]
                avg_response_time = sum(response_times) / len(response_times)
                min_response_time = min(response_times)
                max_response_time = max(response_times)

                sum(r.get("tokens", 0) for r in successful)
                actual_duration = time.time() - start_time
                requests_per_second = (
                    total_requests / actual_duration if actual_duration > 0 else 0
                )
            else:
                avg_response_time = 0
                min_response_time = 0
                max_response_time = 0
                requests_per_second = 0

            error_rate = (
                (failed_requests / total_requests * 100) if total_requests > 0 else 0
            )

            # Complete benchmark run
            await self.metrics_collector.complete_benchmark_run(
                benchmark_run_id, status="completed"
            )

            return {
                "run_id": benchmark_run_id,
                "provider": provider,
                "model": model,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "avg_response_time": round(avg_response_time, 3),
                "min_response_time": round(min_response_time, 3),
                "max_response_time": round(max_response_time, 3),
                "requests_per_second": round(requests_per_second, 2),
                "error_rate": round(error_rate, 2),
                "errors": errors[:10],  # Limit to first 10 errors
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Stress test error: {e}", exc_info=True)
            await self.metrics_collector.complete_benchmark_run(
                benchmark_run_id, status="failed", error_message=str(e)
            )
            raise
