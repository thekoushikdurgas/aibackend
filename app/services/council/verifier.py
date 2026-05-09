"""
Per-claim verification against RAG chunks (and optional web search when enabled).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from html import unescape
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.services.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)


class ClaimStatus:
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


@dataclass
class VerifiedClaim:
    text: str
    status: str
    confidence: float
    evidence_snippet: str = ""
    source_url: str = ""
    source_id: str = ""


def _word_jaccard(a: str, b: str) -> float:
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    inter = len(wa & wb)
    union = len(wa | wb)
    return inter / union if union else 0.0


async def verify_claim_web(claim: str) -> Optional[VerifiedClaim]:
    """
    When `council_enable_web_verifier` is true, run a simple DuckDuckGo HTML search
    and heuristically link the first relevant results to the claim.
    """
    if not getattr(settings, "council_enable_web_verifier", False):
        return None
    if not (claim and str(claim).strip()):
        return None
    q = (claim or "").strip()[:300]
    url = (getattr(settings, "council_web_search_url", None) or "").strip() or (
        "https://html.duckduckgo.com/html"
    )
    timeout = float(getattr(settings, "council_web_search_timeout", 20.0) or 20.0)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DurgasAI-Council/1.0; +https://thekoushikdurgas.com)",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=timeout, headers=headers
        ) as client:
            resp = await client.post(url, data={"q": q, "b": ""})
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        logger.warning("council web search failed: %s", e)
        return None
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    # DuckDuckGo HTML: results often in .result or .web-result
    candidates: List[Tuple[str, str, str]] = []
    for sel in (".result", ".result__body", ".web-result", "div.links_main"):
        for el in soup.select(sel)[:12]:
            a = el.find("a", href=True)
            if not a or not a["href"] or a["href"].startswith("//duckduckgo.com"):
                continue
            href = a["href"].strip()
            if not href.startswith("http"):
                continue
            title = a.get_text(" ", strip=True) or ""
            snippet = el.get_text(" ", strip=True)[:500]
            candidates.append((href, title, snippet))
    if not candidates:
        for a in soup.find_all("a", href=True, limit=40):
            href = a["href"].strip()
            if not href.startswith("http") or "duckduckgo" in href:
                continue
            t = a.get_text(" ", strip=True)
            if len(t) < 5:
                continue
            candidates.append((href, t, t[:500]))
    if not candidates:
        return None
    # Pick best Jaccard overlap with claim or question terms
    best = _best_web_match(claim, candidates[:5])
    if not best:
        return None
    href, title, snippet, jac = best
    if jac < 0.08 and len(claim) > 20:
        return None
    status = ClaimStatus.SUPPORTED if jac >= 0.12 else ClaimStatus.UNSUPPORTED
    return VerifiedClaim(
        text=claim,
        status=status,
        confidence=min(0.85, 0.25 + 0.6 * jac),
        evidence_snippet=unescape(snippet)[:400],
        source_url=href,
        source_id=str(hash(href) % 10_000_000),
    )


def _best_web_match(
    claim: str, candidates: List[Tuple[str, str, str]]
) -> Optional[Tuple[str, str, str, float]]:
    if not claim or not candidates:
        return None
    best = None
    best_j = 0.0
    for href, title, snippet in candidates:
        blob = f"{title} {snippet}"
        j = _word_jaccard(claim, blob)
        if j > best_j:
            best = (href, title, snippet, j)
            best_j = j
    return best


# Backward-compatible name
verify_claim_web_stub = verify_claim_web


def verify_claim_rag(
    claim: str,
    retriever: RAGRetriever,
    min_score: float,
) -> VerifiedClaim:
    """
    Label a claim using vector similarity + lexical overlap with top retrieved chunks.
    """
    hits = retriever.retrieve(claim, k=8)
    if not hits:
        return VerifiedClaim(
            text=claim,
            status=ClaimStatus.UNSUPPORTED,
            confidence=0.0,
            evidence_snippet="",
        )
    best = max(hits, key=lambda h: float(h.get("score", 0)))
    score = float(best.get("score", 0))
    content = best.get("content") or ""
    meta = best.get("metadata") or {}
    jac = _word_jaccard(claim, content)
    combined = 0.65 * score + 0.35 * jac
    url = str(meta.get("url", "") or "")
    sid = str(best.get("id", "") or meta.get("chunk_index", ""))
    snippet = content[:400]
    if combined >= min_score:
        return VerifiedClaim(
            text=claim,
            status=ClaimStatus.SUPPORTED,
            confidence=min(1.0, combined),
            evidence_snippet=snippet,
            source_url=url,
            source_id=sid,
        )
    # Soft contradiction: strong chunk exists but contradicts claim (very rough heuristic)
    neg = (" not ", " false ", " incorrect ", " myth ", " never ")
    lowered = content.lower()
    cl = claim.lower()
    if (
        any(n in lowered for n in neg)
        and not any(n in cl for n in neg)
        and score > 0.55
    ):
        return VerifiedClaim(
            text=claim,
            status=ClaimStatus.CONTRADICTED,
            confidence=0.4,
            evidence_snippet=snippet,
            source_url=url,
            source_id=sid,
        )
    return VerifiedClaim(
        text=claim,
        status=ClaimStatus.UNSUPPORTED,
        confidence=combined,
        evidence_snippet=snippet,
        source_url=url,
        source_id=sid,
    )


def verify_claim_with_optional_web(
    claim: str,
    retriever: RAGRetriever,
    min_score: float,
    allow_web: bool,
) -> VerifiedClaim:
    """Sync path: web is not consulted (use async version from async code)."""
    return verify_claim_rag(claim, retriever, min_score)


async def verify_claim_with_optional_web_async(
    claim: str,
    retriever: RAGRetriever,
    min_score: float,
    allow_web: bool,
) -> VerifiedClaim:
    vc = verify_claim_rag(claim, retriever, min_score)
    if vc.status != ClaimStatus.UNSUPPORTED or not allow_web:
        return vc
    web = await verify_claim_web(claim)
    if web is not None and web.status == ClaimStatus.SUPPORTED:
        return web
    if web is not None and web.evidence_snippet:
        return web
    return vc


def claims_to_dict_list(claims: List[VerifiedClaim]) -> List[Dict[str, Any]]:
    return [
        {
            "text": c.text,
            "status": c.status,
            "confidence": round(c.confidence, 4),
            "evidence_snippet": c.evidence_snippet,
            "source_url": c.source_url,
            "source_id": c.source_id,
        }
        for c in claims
    ]
