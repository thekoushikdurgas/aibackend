"""Utility tools GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import batch, benchmark, cohere, embeddings, nlp, scraper
from app.graphql.modules.util import run_ws


@strawberry.type
class ToolsMutation:
    @strawberry.mutation
    async def process_nlp(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(nlp.handle_nlp_process, p, info)

    @strawberry.mutation
    async def scrape(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(scraper.handle_scraper_scrape, p, info)

    @strawberry.mutation
    async def run_benchmark(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(benchmark.handle_benchmark_run, p, info)

    @strawberry.mutation
    async def batch_process(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(batch.handle_batch_process, p, info)

    @strawberry.mutation
    async def embeddings_gemini(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(embeddings.handle_embeddings_gemini, p, info)

    @strawberry.mutation
    async def cohere_summarize(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(cohere.handle_cohere_summarize, p, info)

    @strawberry.mutation
    async def cohere_embed(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(cohere.handle_cohere_embed, p, info)

    @strawberry.mutation
    async def cohere_classify(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(cohere.handle_cohere_classify, p, info)
