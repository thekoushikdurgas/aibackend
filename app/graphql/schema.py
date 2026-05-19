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
from app.graphql.modules.runtime_settings.resolvers import (
    RuntimeSettingsMutation,
    RuntimeSettingsQuery,
)
from app.graphql.modules.google_photos.resolvers import GooglePhotosQuery
from app.graphql.modules.gmail.resolvers import GmailQuery
from app.graphql.modules.google_calendar.resolvers import GoogleCalendarQuery
from app.graphql.modules.google_people.resolvers import GooglePeopleQuery
from app.graphql.modules.google_drive.resolvers import GoogleDriveQuery
from app.graphql.modules.google_tasks.resolvers import (
    GoogleTasksMutation,
    GoogleTasksQuery,
)
from app.graphql.modules.todos.resolvers import TodosMutation, TodosQuery
from app.graphql.modules.storage.resolvers import StorageMutation, StorageQuery
from app.graphql.modules.tools.resolvers import ToolsMutation
from app.graphql.modules.vision.resolvers import VisionMutation
from app.graphql.modules.weather.resolvers import WeatherQuery
from app.graphql.modules.workflows.resolvers import WorkflowsMutation, WorkflowsQuery
from app.graphql.modules.installed_apps.resolvers import (
    InstalledAppsMutation,
    InstalledAppsQuery,
)
from app.graphql.modules.widgets.resolvers import WidgetsMutation, WidgetsQuery
from app.graphql.modules.linked_accounts.resolvers import (
    LinkedAccountsMutation,
    LinkedAccountsQuery,
)


@strawberry.type
class Query(
    AuthQuery,
    ChatQuery,
    AgentsQuery,
    RagQuery,
    StorageQuery,
    GooglePhotosQuery,
    GmailQuery,
    GoogleCalendarQuery,
    GooglePeopleQuery,
    GoogleDriveQuery,
    GoogleTasksQuery,
    TodosQuery,
    MetricsQuery,
    ProvidersQuery,
    HealthQuery,
    WeatherQuery,
    WorkflowsQuery,
    WidgetsQuery,
    InstalledAppsQuery,
    LinkedAccountsQuery,
    RuntimeSettingsQuery,
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
    WorkflowsMutation,
    WidgetsMutation,
    InstalledAppsMutation,
    LinkedAccountsMutation,
    RuntimeSettingsMutation,
    GoogleTasksMutation,
    TodosMutation,
):
    """Root GraphQL mutation (modular mix-ins)."""


schema = strawberry.Schema(query=Query, mutation=Mutation)
