"""
Extract atomic factual claims from model text for verification.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from app.services.llm import LLMProviderFactory, LLMConfig

logger = logging.getLogger(__name__)

_MAX_CLAIMS = 20


@dataclass
class ClaimDraft:
    text: str


def heuristic_extract_claims(text: str) -> List[ClaimDraft]:
    """Deterministic sentence split; used as fallback when LLM extraction is unavailable."""
    if not text or not text.strip():
        return []
    # Split on sentence boundaries
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    out: List[ClaimDraft] = []
    for p in parts:
        s = p.strip()
        if len(s) < 12:
            continue
        out.append(ClaimDraft(text=s[:500]))
        if len(out) >= _MAX_CLAIMS:
            break
    return out


async def extract_claims_llm(
    text: str,
    provider_name: Optional[str] = None,
) -> List[ClaimDraft]:
    """
    Ask a single model to output JSON { "claims": [ {"text": "..."} ] }.
    Falls back to heuristic_extract_claims on any failure.
    """
    if not text or not text.strip():
        return []
    prompt = f"""Extract distinct factual claims from the assistant text below.
Return ONLY valid JSON with this exact shape:
{{"claims":[{{"text":"short claim sentence"}}]}}
Rules:
- At most {_MAX_CLAIMS} claims.
- Each claim should be one sentence.
- Skip pleasantries, hedging without content, and pure opinions unless they assert a fact.

TEXT:
{text[:12000]}
"""
    config = LLMConfig(
        temperature=0.1,
        max_tokens=1024,
        system_prompt="You output only JSON. No markdown fences.",
    )
    try:
        if not provider_name:
            from app.services.council.model_selector import ModelSelector

            provider_name = await ModelSelector.select_chairman_model()
        if not provider_name:
            return heuristic_extract_claims(text)
        provider = LLMProviderFactory.get_provider(provider_name)
        resp = await provider.generate(prompt=prompt, config=config)
        raw = (resp.text or "").strip()
        # Strip ```json fences if any
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        items = data.get("claims") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return heuristic_extract_claims(text)
        out: List[ClaimDraft] = []
        for it in items:
            if isinstance(it, dict) and it.get("text"):
                t = str(it["text"]).strip()
                if len(t) >= 8:
                    out.append(ClaimDraft(text=t[:500]))
            if len(out) >= _MAX_CLAIMS:
                break
        return out if out else heuristic_extract_claims(text)
    except Exception as e:
        logger.warning("LLM claim extraction failed, using heuristic: %s", e)
        return heuristic_extract_claims(text)
