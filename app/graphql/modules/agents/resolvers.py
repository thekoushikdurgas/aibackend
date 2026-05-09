"""Agents GraphQL module."""

from __future__ import annotations

from typing import Optional

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import agents as agents_handlers
from app.graphql.modules.util import run_ws


@strawberry.type
class AgentsQuery:
    @strawberry.field
    async def list_agents(self, info: Info) -> JSON:
        return await run_ws(agents_handlers.handle_agents_list, {}, info)


@strawberry.type
class AgentsMutation:
    @strawberry.mutation
    async def analyze_agent(
        self,
        info: Info,
        agent_type: str,
        page_data: JSON,
        query: Optional[str] = None,
        options: Optional[JSON] = None,
    ) -> JSON:
        params: dict = {
            "agent_type": agent_type,
            "page_data": page_data,
            "query": query,
            "options": options,
        }
        return await run_ws(agents_handlers.handle_agents_analyze, params, info)

    @strawberry.mutation
    async def auto_analyze(
        self,
        info: Info,
        page_data: JSON,
        query: str,
    ) -> JSON:
        return await run_ws(
            agents_handlers.handle_agents_auto_analyze,
            {"page_data": page_data, "query": query},
            info,
        )

    @strawberry.mutation
    async def batch_analyze(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(agents_handlers.handle_agents_batch_analyze, p, info)

    @strawberry.mutation
    async def agents_quick_seo(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(agents_handlers.handle_agents_quick_seo, p, info)

    @strawberry.mutation
    async def agents_summarize(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(agents_handlers.handle_agents_summarize, p, info)
