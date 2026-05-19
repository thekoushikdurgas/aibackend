"""Map JSON-RPC errors to GraphQL errors with unified extension codes."""

from typing import cast

from graphql import GraphQLError

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


def _extension_code_for_jsonrpc(code: int) -> str:
    """Align GraphQL extensions.code with docs/ARCHITECTURE.md unified catalog."""
    mapping = {
        JSONRPCErrorCode.PARSE_ERROR: "PARSE_ERROR",
        JSONRPCErrorCode.INVALID_REQUEST: "BAD_REQUEST",
        JSONRPCErrorCode.METHOD_NOT_FOUND: "METHOD_NOT_FOUND",
        JSONRPCErrorCode.INVALID_PARAMS: "BAD_USER_INPUT",
        JSONRPCErrorCode.INTERNAL_ERROR: "INTERNAL",
        JSONRPCErrorCode.AUTHENTICATION_ERROR: "UNAUTHENTICATED",
        JSONRPCErrorCode.AUTHORIZATION_ERROR: "FORBIDDEN",
        JSONRPCErrorCode.RATE_LIMIT_ERROR: "RATE_LIMITED",
        JSONRPCErrorCode.VALIDATION_ERROR: "VALIDATION_ERROR",
        JSONRPCErrorCode.PROVIDER_ERROR: "PROVIDER_ERROR",
        JSONRPCErrorCode.SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(cast(JSONRPCErrorCode, code), "INTERNAL")


def raise_jsonrpc_as_graphql(exc: JSONRPCError) -> None:
    raise GraphQLError(
        exc.message,
        extensions={
            "code": _extension_code_for_jsonrpc(exc.code),
            "jsonrpc_code": exc.code,
        },
    ) from exc
