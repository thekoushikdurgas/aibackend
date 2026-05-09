"""Merged Strawberry GraphQL schema (single `/graphql` HTTP endpoint)."""

from __future__ import annotations

import strawberry

from app.graphql.modules.agents.resolvers import AgentsMutation, AgentsQuery
from app.graphql.modules.auth.resolvers import AuthMutation, AuthQuery
from app.graphql.modules.chat.resolvers import ChatMutation, ChatQuery
from app.graphql.modules.council.resolvers import CouncilMutation
from app.graphql.modules.health.resolvers import HealthQuery
from app.graphql.modules.media.resolvers import MediaMutation
from app.graphql.modules.metrics.resolvers import MetricsQuery
from app.graphql.modules.multimodal.resolvers import MultimodalMutation
from app.graphql.modules.providers.resolvers import ProvidersMutation, ProvidersQuery
from app.graphql.modules.rag.resolvers import RagMutation, RagQuery
from app.graphql.modules.storage.resolvers import StorageMutation, StorageQuery
from app.graphql.modules.tools.resolvers import ToolsMutation
from app.graphql.modules.vision.resolvers import VisionMutation


@strawberry.type
class Query(
    AuthQuery,
    ChatQuery,
    AgentsQuery,
    RagQuery,
    StorageQuery,
    MetricsQuery,
    ProvidersQuery,
    HealthQuery,
):
    """Root GraphQL query (modular mix-ins)."""


@strawberry.type
class Mutation(
    AuthMutation,
    ChatMutation,
    AgentsMutation,
    RagMutation,
    StorageMutation,
    VisionMutation,
    MultimodalMutation,
    CouncilMutation,
    ProvidersMutation,
    MediaMutation,
    ToolsMutation,
):
    """Root GraphQL mutation (modular mix-ins)."""


schema = strawberry.Schema(query=Query, mutation=Mutation)
