"""
Instrumentation decorator for automatic metrics collection
"""

import time
import functools
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def measure_latency(
    record_metrics: Optional[Callable] = None, capture_response: bool = False
):
    """
    Decorator to automatically measure latency and token metrics for LLM provider calls.

    Args:
        record_metrics: Optional callback function to record metrics.
                       Should accept: provider, model, prompt, ttft, total_time,
                       tokens_generated, tokens_per_second, streaming, success, error
        capture_response: Whether to capture full response data

    Usage:
        @measure_latency(record_metrics=my_metrics_collector.record_benchmark)
        async def generate(self, prompt, config, ...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract provider and model from args/kwargs
            provider_name = None
            model_name = None
            prompt_text = None
            streaming = kwargs.get("stream", False) or kwargs.get("streaming", False)

            # Try to get provider from self (for class methods)
            if args and hasattr(args[0], "provider_name"):
                provider_name = args[0].provider_name

            # Try to get model from config
            config = kwargs.get("config")
            if config and hasattr(config, "model"):
                model_name = config.model

            # Try to get prompt
            prompt_text = kwargs.get("prompt") or (args[1] if len(args) > 1 else None)

            start_time = time.time()
            ttft = None
            first_chunk_time = None
            tokens_generated = 0
            error = None
            success = True
            response_data = None

            try:
                if streaming:
                    # For streaming, measure TTFT and count tokens
                    async for chunk in func(*args, **kwargs):
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                            ttft = first_chunk_time - start_time

                        # Try to extract token count from chunk
                        if isinstance(chunk, dict):
                            if "tokens" in chunk:
                                tokens_generated += chunk.get("tokens", 0)
                            elif "delta" in chunk and "content" in chunk["delta"]:
                                # Estimate tokens (rough: 1 token ≈ 4 chars)
                                content = chunk["delta"].get("content", "")
                                tokens_generated += len(content) // 4

                        yield chunk

                    total_time = time.time() - start_time
                else:
                    # For non-streaming, measure total time
                    result = await func(*args, **kwargs)
                    total_time = time.time() - start_time

                    # Try to extract metrics from result
                    if hasattr(result, "usage"):
                        usage = result.usage or {}
                        tokens_generated = usage.get(
                            "completion_tokens", 0
                        ) or usage.get("total_tokens", 0)
                    elif isinstance(result, dict):
                        if "usage" in result:
                            usage = result["usage"]
                            tokens_generated = usage.get(
                                "completion_tokens", 0
                            ) or usage.get("total_tokens", 0)
                        elif "tokens" in result:
                            tokens_generated = result["tokens"]

                    # Calculate TTFT (for non-streaming, it's approximately 0 or very small)
                    ttft = total_time * 0.1  # Rough estimate: 10% of total time

                    if capture_response:
                        if hasattr(result, "dict"):
                            response_data = result.dict()
                        elif isinstance(result, dict):
                            response_data = result

                    # Calculate tokens per second for non-streaming
                    tokens_per_second = (
                        tokens_generated / total_time if total_time > 0 else None
                    )

                    # Yield the result instead of returning (since this is an async generator)
                    yield result
                    return

                # Calculate tokens per second for streaming
                tokens_per_second = (
                    tokens_generated / total_time if total_time > 0 else None
                )

            except Exception as e:
                success = False
                error = str(e)
                total_time = time.time() - start_time
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                raise

            finally:
                # Record metrics if callback provided
                if record_metrics and provider_name and model_name:
                    try:
                        await record_metrics(
                            provider=provider_name,
                            model=model_name,
                            prompt=prompt_text or "",
                            ttft=ttft,
                            total_time=total_time,
                            tokens_generated=tokens_generated,
                            tokens_per_second=tokens_per_second,
                            streaming=streaming,
                            success=success,
                            error=error,
                            response_data=response_data if capture_response else None,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record metrics: {e}")

        # Handle both async and sync functions
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    time.time() - start_time
                    # Record sync metrics if needed
                    return result
                except Exception as e:
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                    raise

            return sync_wrapper

    return decorator


class TimingContext:
    """Context manager for timing code blocks"""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        return False

    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return time.time() - self.start_time
        return self.duration
