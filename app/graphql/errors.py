"""Map JSON-RPC errors to GraphQL errors with unified extension codes."""

from graphql import GraphQLError

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


def _extension_code_for_jsonrpc(code: int) -> str:
    """Align GraphQL extensions.code with docs/ARCHITECTURE.md unified catalog."""
    mapping = {
        int(JSONRPCErrorCode.PARSE_ERROR): "PARSE_ERROR",
        int(JSONRPCErrorCode.INVALID_REQUEST): "BAD_REQUEST",
        int(JSONRPCErrorCode.METHOD_NOT_FOUND): "METHOD_NOT_FOUND",
        int(JSONRPCErrorCode.INVALID_PARAMS): "BAD_USER_INPUT",
        int(JSONRPCErrorCode.INTERNAL_ERROR): "INTERNAL",
        int(JSONRPCErrorCode.AUTHENTICATION_ERROR): "UNAUTHENTICATED",
        int(JSONRPCErrorCode.AUTHORIZATION_ERROR): "FORBIDDEN",
        int(JSONRPCErrorCode.RATE_LIMIT_ERROR): "RATE_LIMITED",
        int(JSONRPCErrorCode.VALIDATION_ERROR): "VALIDATION_ERROR",
        int(JSONRPCErrorCode.PROVIDER_ERROR): "PROVIDER_ERROR",
        int(JSONRPCErrorCode.SERVICE_UNAVAILABLE): "SERVICE_UNAVAILABLE",
    }
    return mapping.get(int(code), "INTERNAL")


def raise_jsonrpc_as_graphql(exc: JSONRPCError) -> None:
    raise GraphQLError(
        exc.message,
        extensions={
            "code": _extension_code_for_jsonrpc(int(exc.code)),
            "jsonrpc_code": int(exc.code),
        },
    ) from exc
