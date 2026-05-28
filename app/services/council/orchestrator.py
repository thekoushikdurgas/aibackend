"""
Council Orchestrator - 3-stage deliberation with optional v2 anti-hallucination pipeline.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.schemas import PageData
from app.services.llm import LLMProviderFactory, LLMConfig
from app.services.rag.retriever import RAGRetriever
from .model_selector import ModelSelector
from .policy import CouncilPolicy, CouncilRunOptions, parse_council_options
from .prompts import (
    build_stage1_prompt,
    build_stage1_grounded_prompt,
    build_stage2_ranking_prompt,
    build_stage2_verified_overlap_prompt,
    build_stage3_chairman_prompt,
    build_stage3_chairman_verified_prompt,
    format_sources_for_prompt,
)
from .parser import parse_ranking_from_text
from .claim_extractor import extract_claims_llm
from .verifier import (
    ClaimStatus,
    VerifiedClaim,
    claims_to_dict_list,
    verify_claim_with_optional_web_async,
)
from app.services.metrics.council_metrics import council_metrics

logger = logging.getLogger(__name__)


def _page_context_str(page_data: Optional[PageData]) -> str:
    if not page_data:
        return ""
    parts = []
    if page_data.url:
        parts.append(f"URL: {page_data.url}")
    if page_data.title:
        parts.append(f"Title: {page_data.title}")
    if page_data.domain:
        parts.append(f"Domain: {page_data.domain}")
    return "\n".join(parts)


class CouncilOrchestrator:
    """Orchestrates the 3-stage council deliberation process."""

    def __init__(
        self,
        council_models: Optional[List[str]] = None,
        chairman_model: Optional[str] = None,
        council_options: Optional[CouncilRunOptions] = None,
    ):
        self.council_models = council_models
        self.chairman_model = chairman_model
        self.council_options = council_options or CouncilRunOptions()

    async def _ensure_models(self) -> None:
        if not self.council_models:
            self.council_models = await ModelSelector.select_council_models()
        if not self.chairman_model:
            self.chairman_model = await ModelSelector.select_chairman_model()

    async def stage1_collect_responses(
        self,
        query: str,
        page_data: Optional[PageData] = None,
        use_grounding: bool = False,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        await self._ensure_models()
        if not self.council_models:
            logger.error("No council models available")
            return []
        if len(self.council_models) < 3:
            logger.warning(
                "Only %s models; minimum 3 recommended", len(self.council_models)
            )

        page_context = _page_context_str(page_data)
        if use_grounding and sources is not None:
            block = format_sources_for_prompt(sources)
            strict = self.council_options.policy == CouncilPolicy.VERIFIED
            prompt = build_stage1_grounded_prompt(
                query, block, page_context=page_context, strict=strict
            )
            temp = float(getattr(settings, "council_grounded_temperature", 0.2))
            system_prompt = "You are a research assistant. Cite sources with [S#] and never assert facts without a citation from SOURCE PASSAGES."
        else:
            prompt = build_stage1_prompt(query, page_context)
            temp = float(getattr(settings, "council_open_temperature", 0.7))
            system_prompt = "You are a helpful AI assistant. Provide clear, accurate, and helpful responses."

        config = LLMConfig(
            temperature=temp,
            max_tokens=2048,
            system_prompt=system_prompt,
        )

        async def query_model(provider_name: str) -> Optional[Dict[str, Any]]:
            try:
                provider = LLMProviderFactory.get_provider(provider_name)
                response = await asyncio.wait_for(
                    provider.generate(prompt=prompt, config=config),
                    timeout=60.0,
                )
                return {"model": provider_name, "response": response.text}
            except Exception as e:
                logger.error("Model %s failed in Stage 1: %s", provider_name, e)
                return None

        tasks = [query_model(m) for m in self.council_models]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        out: List[Dict[str, Any]] = []
        for response in responses:
            if isinstance(response, dict) and response:
                out.append(response)
        logger.info("Stage 1 completed: %s/%s", len(out), len(self.council_models))
        return out

    async def stage2_collect_rankings(
        self,
        user_query: str,
        stage1_results: List[Dict[str, Any]],
        page_data: Optional[PageData] = None,
        verification_stats: str = "",
        use_verified_prompt: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        if not stage1_results:
            return [], {}
        await self._ensure_models()
        labels = [chr(65 + i) for i in range(len(stage1_results))]
        label_to_model = {
            f"Response {lb}": r["model"] for lb, r in zip(labels, stage1_results)
        }
        responses_text = "\n\n".join(
            f"Response {lb}:\n{r['response']}" for lb, r in zip(labels, stage1_results)
        )
        page_context = _page_context_str(page_data)
        if use_verified_prompt and verification_stats:
            ranking_prompt = build_stage2_verified_overlap_prompt(
                user_query, responses_text, verification_stats, page_context
            )
        else:
            ranking_prompt = build_stage2_ranking_prompt(
                user_query, responses_text, page_context
            )

        temp = float(
            getattr(
                settings,
                "council_ranking_temperature",
                0.4 if use_verified_prompt else 0.5,
            )
        )
        config = LLMConfig(
            temperature=temp,
            max_tokens=2048,
            system_prompt="You are an expert evaluator. Follow the ranking output format exactly.",
        )

        async def query_ranking(provider_name: str) -> Optional[Dict[str, Any]]:
            try:
                provider = LLMProviderFactory.get_provider(provider_name)
                response = await asyncio.wait_for(
                    provider.generate(prompt=ranking_prompt, config=config),
                    timeout=90.0,
                )
                full_text = response.text
                parsed = parse_ranking_from_text(full_text)
                return {
                    "model": provider_name,
                    "ranking": full_text,
                    "parsed_ranking": parsed,
                }
            except Exception as e:
                logger.error("Model %s failed in Stage 2: %s", provider_name, e)
                return None

        if not self.council_models:
            return [], label_to_model
        tasks = [query_ranking(m) for m in self.council_models]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        out: List[Dict[str, Any]] = []
        for response in responses:
            if isinstance(response, dict) and response:
                out.append(response)
        return out, label_to_model

    async def stage3_synthesize_final(
        self,
        user_query: str,
        stage1_results: List[Dict[str, Any]],
        stage2_results: List[Dict[str, Any]],
        page_data: Optional[PageData] = None,
        verification_ledger: str = "",
        use_verified_chair: bool = False,
        abstain: bool = False,
    ) -> Dict[str, Any]:
        await self._ensure_models()
        if not self.chairman_model:
            return {
                "model": "error",
                "response": "Error: Unable to generate final synthesis - no chairman model available.",
            }
        stage1_text = "\n\n".join(
            f"Model: {r['model']}\nResponse: {r['response']}" for r in stage1_results
        )
        stage2_text = "\n\n".join(
            f"Model: {r['model']}\nRanking: {r['ranking']}" for r in stage2_results
        )
        page_context = _page_context_str(page_data)
        if abstain:
            msg = (
                "This question could not be verified against available sources. "
                "The retrieved passages did not support a confident, cited answer."
            )
            return {"model": self.chairman_model, "response": msg}

        if use_verified_chair:
            chair_prompt = build_stage3_chairman_verified_prompt(
                user_query,
                stage1_text,
                stage2_text,
                verification_ledger,
                page_context,
                citation_only=True,
            )
            t = float(getattr(settings, "council_chairman_grounded_temp", 0.3))
        else:
            chair_prompt = build_stage3_chairman_prompt(
                user_query, stage1_text, stage2_text, page_context
            )
            t = float(getattr(settings, "council_chairman_open_temp", 0.7))
        config = LLMConfig(
            temperature=t,
            max_tokens=4096,
            system_prompt="You are the Chairman. Obey the prompt constraints on citations and unknowns.",
        )
        try:
            provider = LLMProviderFactory.get_provider(self.chairman_model)
            response = await asyncio.wait_for(
                provider.generate(prompt=chair_prompt, config=config),
                timeout=120.0,
            )
            return {"model": self.chairman_model, "response": response.text}
        except Exception as e:
            logger.error("Chairman model %s failed: %s", self.chairman_model, e)
            return {
                "model": self.chairman_model,
                "response": f"Error: Unable to generate final synthesis. {e!s}",
            }

    def calculate_aggregate_rankings(
        self,
        stage2_results: List[Dict[str, Any]],
        label_to_model: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        model_positions: Dict[str, List[int]] = defaultdict(list)
        for ranking in stage2_results:
            parsed = ranking.get("parsed_ranking") or []
            for pos, label in enumerate(parsed, start=1):
                if label in label_to_model:
                    model_positions[label_to_model[label]].append(pos)
        agg: List[Dict[str, Any]] = []
        for model, positions in model_positions.items():
            if positions:
                avg = sum(positions) / len(positions)
                agg.append(
                    {
                        "model": model,
                        "average_rank": round(avg, 2),
                        "rankings_count": len(positions),
                    }
                )
        agg.sort(key=lambda x: x["average_rank"])
        return agg

    def _resolve_sources(
        self, query: str, page_data: Optional[PageData]
    ) -> Tuple[List[Dict[str, Any]], RAGRetriever]:
        retriever = RAGRetriever()
        raw: List[Dict[str, Any]] = []
        if page_data and (page_data.html or page_data.body_html):
            try:
                retriever.ingest_page(page_data)
            except Exception as e:
                logger.warning("RAG ingest_page skipped: %s", e)
        k = int(getattr(settings, "council_rag_retrieve_k", 12))
        fk = int(getattr(settings, "council_rag_mmr_k", 6))
        q = (query or "").strip()
        if not q and page_data:
            q = (page_data.url or page_data.title or "page").strip()
        if not q:
            q = "context"
        try:
            raw = retriever.retrieve_mmr(q, k=k, final_k=fk)
        except Exception as e:
            logger.warning("retrieve_mmr failed, falling back: %s", e)
            raw = retriever.retrieve(q, k=fk) if q else []
        th = float(getattr(settings, "rag_similarity_threshold", 0.25))
        filtered = [r for r in raw if float(r.get("score", 0)) >= th]
        use_list = (
            filtered if filtered else (raw[: max(1, min(3, len(raw)))] if raw else [])
        )
        if not use_list and page_data:
            use_list = retriever.bootstrap_page_sources(page_data)
        return use_list, retriever

    async def _verify_stage1_async(
        self,
        stage1: List[Dict[str, Any]],
        retriever: RAGRetriever,
        thresh: float,
        allow_web: bool,
    ) -> Tuple[Dict[str, List[VerifiedClaim]], str, str, float, int]:
        per_model: Dict[str, List[VerifiedClaim]] = {}
        stat_lines: List[str] = []
        ledger_all: List[str] = []
        label = "A"
        total_claims = 0
        total_supported = 0
        for r in stage1:
            m = r["model"]
            drafts = await extract_claims_llm(
                r.get("response") or "", self.chairman_model
            )
            vcs: List[VerifiedClaim] = []
            for d in drafts:
                vc = await verify_claim_with_optional_web_async(
                    d.text, retriever, thresh, allow_web
                )
                vcs.append(vc)
                ledger_all.append(
                    f"- model={m} | {vc.status} | conf={vc.confidence:.2f} | {vc.text[:200]}"
                )
                council_metrics.record_claim(vc.status)
            per_model[m] = vcs
            sup = sum(1 for x in vcs if x.status == ClaimStatus.SUPPORTED)
            total_claims += len(vcs)
            total_supported += sup
            stat_lines.append(
                f"Response {label}: supported {sup}/{len(vcs) if vcs else 0} (model={m})"
            )
            label = chr(ord(label) + 1)
        coverage = (total_supported / total_claims) if total_claims else 0.0
        council_metrics.record_coverage(coverage)
        return (
            per_model,
            "\n".join(stat_lines),
            "\n".join(ledger_all),
            coverage,
            total_claims,
        )

    async def run_full_council(
        self,
        query: str,
        page_data: Optional[PageData] = None,
    ) -> Tuple[List[Dict], List[Dict], Dict[str, Any], Dict[str, Any]]:
        opts = self.council_options
        if opts.policy == CouncilPolicy.OPEN:
            return await self._run_open(query, page_data)
        return await self._run_grounded_or_verified(query, page_data)

    async def _run_open(
        self,
        query: str,
        page_data: Optional[PageData] = None,
    ) -> Tuple[List[Dict], List[Dict], Dict[str, Any], Dict[str, Any]]:
        stage1 = await self.stage1_collect_responses(
            query, page_data, use_grounding=False, sources=None
        )
        if not stage1:
            return (
                [],
                [],
                {
                    "model": "error",
                    "response": "All models failed to respond. Please try again.",
                },
                {},
            )
        stage2, lmap = await self.stage2_collect_rankings(
            query, stage1, page_data, use_verified_prompt=False
        )
        agg = self.calculate_aggregate_rankings(stage2, lmap)
        stage3 = await self.stage3_synthesize_final(
            query, stage1, stage2, page_data, use_verified_chair=False
        )
        co = self.council_options
        meta = {
            "label_to_model": lmap,
            "aggregate_rankings": agg,
            "models_used": self.council_models or [],
            "chairman": self.chairman_model or "unknown",
            "council_v2": {
                "schema_version": co.schema_version,
                "policy": CouncilPolicy.OPEN.value,
                "abstained": False,
                "unverified": True,
            },
        }
        return stage1, stage2, stage3, meta

    async def _run_grounded_or_verified(
        self,
        query: str,
        page_data: Optional[PageData] = None,
    ) -> Tuple[List[Dict], List[Dict], Dict[str, Any], Dict[str, Any]]:
        opts = self.council_options
        sources, retriever = self._resolve_sources(query, page_data)
        if not sources:
            council_metrics.record_abstain("no_sources")
            return (
                [],
                [],
                {
                    "model": self.chairman_model or "council",
                    "response": (
                        "This question could not be verified against available sources. "
                        "No text could be loaded from the page or the knowledge index."
                    ),
                },
                {
                    "council_v2": {
                        "schema_version": opts.schema_version,
                        "policy": opts.policy.value,
                        "abstained": True,
                        "claims": [],
                        "coverage": 0.0,
                    }
                },
            )

        stage1 = await self.stage1_collect_responses(
            query, page_data, use_grounding=True, sources=sources
        )
        if not stage1:
            return (
                [],
                [],
                {
                    "model": "error",
                    "response": "All models failed in grounded stage 1.",
                },
                {},
            )
        await self._ensure_models()
        thresh = opts.effective_verify_threshold()
        per_model, stats_text, ledger, coverage, n_claims = (
            await self._verify_stage1_async(
                stage1, retriever, thresh, opts.allow_web_tool
            )
        )
        use_ver = True
        floor = float(getattr(settings, "council_abstain_coverage_floor", 0.15))
        abstain = opts.policy == CouncilPolicy.VERIFIED and (
            coverage < floor or n_claims == 0
        )
        if abstain:
            council_metrics.record_abstain("low_coverage")

        stage2, lmap = await self.stage2_collect_rankings(
            query,
            stage1,
            page_data,
            verification_stats=stats_text,
            use_verified_prompt=use_ver,
        )
        agg = self.calculate_aggregate_rankings(stage2, lmap)
        stage3 = await self.stage3_synthesize_final(
            query,
            stage1,
            stage2,
            page_data,
            verification_ledger=ledger,
            use_verified_chair=True,
            abstain=abstain,
        )
        all_claims: List[Dict[str, Any]] = []
        for m, vcs in per_model.items():
            for c in vcs:
                d = claims_to_dict_list([c])[0]
                d["model"] = m
                all_claims.append(d)
        meta = {
            "label_to_model": lmap,
            "aggregate_rankings": agg,
            "models_used": self.council_models or [],
            "chairman": self.chairman_model or "unknown",
            "council_v2": {
                "schema_version": opts.schema_version,
                "policy": opts.policy.value,
                "abstained": abstain,
                "claims": all_claims,
                "coverage": round(coverage, 4),
                "sources": self._source_summary(sources),
            },
        }
        return stage1, stage2, stage3, meta

    def _source_summary(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for i, s in enumerate(sources, 1):
            meta = s.get("metadata") or {}
            out.append(
                {
                    "index": i,
                    "id": s.get("id", ""),
                    "url": meta.get("url", ""),
                    "title": meta.get("title", ""),
                    "score": float(s.get("score", 0)),
                }
            )
        return out

    @property
    def opts(self) -> CouncilRunOptions:
        return self.council_options


async def run_full_council(
    query: str,
    page_data: Optional[PageData] = None,
    council_models: Optional[List[str]] = None,
    chairman_model: Optional[str] = None,
    council_options: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict], List[Dict], Dict[str, Any], Dict[str, Any]]:
    opts = parse_council_options(council_options)
    orchestrator = CouncilOrchestrator(
        council_models=council_models,
        chairman_model=chairman_model,
        council_options=opts,
    )
    return await orchestrator.run_full_council(query, page_data)
