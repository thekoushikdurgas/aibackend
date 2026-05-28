"""Strawberry GraphQL layer (HTTP); WebSocket JSON-RPC remains primary for AI methods."""

from app.graphql.schema import schema

__all__ = ["schema"]
