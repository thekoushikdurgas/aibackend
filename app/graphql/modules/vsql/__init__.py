"""VSQL GraphQL module integration."""

from app.graphql.modules.vsql.resolvers import Query as VsqlQuery
from app.graphql.modules.vsql.resolvers import Mutation as VsqlMutation

__all__ = ["VsqlQuery", "VsqlMutation"]
