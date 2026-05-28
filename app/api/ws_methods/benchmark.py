"""Benchmark method handlers."""

from typing import Dict, Any, Optional
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.database import AsyncSessionLocal
from app.services.llm import LLMConfig
from app.services.benchmark.orchestrator import BenchmarkOrchestrator


async def handle_benchmark_run(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = params.get("prompt")
    if not prompt:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing prompt")
    run_type = params.get("type", "single")
    if run_type == "latency":
        from app.services.benchmark.latency_suite import run_latency_suite

        return await run_latency_suite(
            providers=params.get("providers"),
            stream_off=bool(params.get("stream_off", True)),
            stream_on=bool(params.get("stream_on", True)),
        )

    config = LLMConfig(
        model=params.get("model"),
        temperature=float(params.get("temperature", 0.7)),
        max_tokens=int(params.get("max_tokens", 512)),
        top_p=float(params.get("top_p", 0.9)),
    )
    async with AsyncSessionLocal() as session:
        orchestrator = BenchmarkOrchestrator(session)
        if run_type == "compare":
            providers = params.get("providers") or []
            if not providers:
                raise JSONRPCError(
                    JSONRPCErrorCode.INVALID_PARAMS, "providers required for compare"
                )
            return await orchestrator.run_comparative_benchmark(
                providers=providers,
                prompt=prompt,
                config=config,
                model=params.get("model"),
            )
        provider = params.get("provider", "ollama")
        model = params.get("model", "default")
        return await orchestrator.run_single_benchmark(
            provider=provider,
            model=model,
            prompt=prompt,
            config=config,
            streaming=bool(params.get("stream", False)),
        )


def get_methods() -> Dict[str, Any]:
    return {"benchmark.run": handle_benchmark_run}
