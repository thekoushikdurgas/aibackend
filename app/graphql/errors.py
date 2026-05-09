"""Map JSON-RPC auth errors to GraphQL errors."""

from graphql import GraphQLError

from app.core.jsonrpc import JSONRPCError


def raise_jsonrpc_as_graphql(exc: JSONRPCError) -> None:
    raise GraphQLError(
        exc.message,
        extensions={
            "code": int(exc.code),
            "jsonrpc_code": int(exc.code),
        },
    ) from exc
