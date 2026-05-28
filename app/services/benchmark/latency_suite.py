"""
LLM API latency suite (Postman LLM API Latency collection methodology).
Same prompt, stream on/off, measure TTFT and total latency.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.services.llm import LLMConfig, get_llm_provider

LATENCY_PROMPT = "Explain the importance of low latency LLMs in two short paragraphs."

# Subset from Postman latency collection (fast + common hosts)
LATENCY_PROVIDER_IDS = [
    "groq",
    "cerebras",
    "sambanova",
    "deepinfra",
    "fireworks",
    "openrouter",
    "together",
    "openai",
]


async def run_latency_probe(
    provider_id: str,
    *,
    model: Optional[str] = None,
    stream: bool = False,
    prompt: str = LATENCY_PROMPT,
    config: Optional[LLMConfig] = None,
) -> Dict[str, Any]:
    cfg = config or LLMConfig(
        model=model,
        temperature=0.5,
        max_tokens=256,
        top_p=1.0,
    )
    if model:
        cfg.model = model

    start = time.perf_counter()
    ttft_ms: Optional[float] = None
    chars = 0
    error: Optional[str] = None

    try:
        prov = get_llm_provider(provider_id)
        if stream:
            first = True
            async for chunk in prov.stream(
                prompt=prompt, config=cfg, conversation_history=None
            ):
                if first:
                    ttft_ms = (time.perf_counter() - start) * 1000
                    first = False
                chars += len(chunk)
        else:
            resp = await prov.generate(
                prompt=prompt, config=cfg, conversation_history=None
            )
            chars = len(resp.text)
    except Exception as e:
        error = str(e)

    total_ms = (time.perf_counter() - start) * 1000
    return {
        "provider": provider_id,
        "model": cfg.model,
        "stream": stream,
        "ttft_ms": ttft_ms,
        "total_ms": round(total_ms, 2),
        "chars": chars,
        "success": error is None,
        "error": error,
    }


async def run_latency_suite(
    providers: Optional[List[str]] = None,
    *,
    stream_off: bool = True,
    stream_on: bool = True,
) -> Dict[str, Any]:
    ids = providers or LATENCY_PROVIDER_IDS
    results: List[Dict[str, Any]] = []
    for pid in ids:
        if stream_off:
            results.append(await run_latency_probe(pid, stream=False))
        if stream_on:
            results.append(await run_latency_probe(pid, stream=True))
    return {"prompt": LATENCY_PROMPT, "results": results}
