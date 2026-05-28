"""
JSON-RPC 2.0 Protocol Implementation
"""

import inspect
import json
import logging
from collections.abc import AsyncIterator
from enum import IntEnum
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class JSONRPCErrorCode(IntEnum):
    """JSON-RPC 2.0 Error Codes"""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # Custom error codes (outside -32768 to -32000 range)
    AUTHENTICATION_ERROR = -32001
    AUTHORIZATION_ERROR = -32002
    RATE_LIMIT_ERROR = -32003
    VALIDATION_ERROR = -32004
    PROVIDER_ERROR = -32005
    SERVICE_UNAVAILABLE = -32006


class JSONRPCError(Exception):
    """JSON-RPC 2.0 Error"""

    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"JSON-RPC Error {code}: {message}")


def create_request(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    request_id: Optional[Union[str, int]] = None,
    auth: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a JSON-RPC 2.0 request

    Args:
        method: Method name (e.g., "chat.completions")
        params: Method parameters
        request_id: Request ID (auto-generated if None)
        auth: Authentication data

    Returns:
        JSON-RPC request dictionary
    """
    request: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}

    if params is not None:
        request["params"] = params

    if request_id is not None:
        request["id"] = request_id

    if auth is not None:
        request["auth"] = auth

    return request


def create_response(
    request_id: Optional[Union[str, int]], result: Any
) -> Dict[str, Any]:
    """
    Create a JSON-RPC 2.0 success response

    Args:
        request_id: Request ID from original request
        result: Result data

    Returns:
        JSON-RPC response dictionary
    """
    response: Dict[str, Any] = {"jsonrpc": "2.0", "result": result}

    if request_id is not None:
        response["id"] = request_id

    return response


def create_error_response(
    request_id: Optional[Union[str, int]],
    code: int,
    message: str,
    data: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Create a JSON-RPC 2.0 error response

    Args:
        request_id: Request ID from original request
        code: Error code
        message: Error message
        data: Additional error data

    Returns:
        JSON-RPC error response dictionary
    """
    error = {"code": code, "message": message}

    if data is not None:
        error["data"] = data

    response: Dict[str, Any] = {"jsonrpc": "2.0", "error": error}

    if request_id is not None:
        response["id"] = request_id

    return response


def validate_request(request: Dict[str, Any]) -> None:
    """
    Validate a JSON-RPC 2.0 request

    Args:
        request: Request dictionary

    Raises:
        JSONRPCError: If request is invalid
    """
    # Check jsonrpc version
    if request.get("jsonrpc") != "2.0":
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_REQUEST, "Invalid JSON-RPC version. Must be '2.0'"
        )

    # Check method
    if "method" not in request:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_REQUEST, "Missing 'method' field")

    if not isinstance(request["method"], str):
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_REQUEST, "Field 'method' must be a string"
        )

    # Check params (optional but must be object or array if present)
    if "params" in request:
        if not isinstance(request["params"], (dict, list)):
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                "Field 'params' must be an object or array",
            )

    # Check id (optional but must be string, number, or null if present)
    if "id" in request:
        if not isinstance(request["id"], (str, int, type(None))):
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                "Field 'id' must be a string, number, or null",
            )


def parse_request(data: Union[str, bytes]) -> Dict[str, Any]:
    """
    Parse and validate a JSON-RPC request from raw data

    Args:
        data: Raw JSON string or bytes

    Returns:
        Parsed and validated request dictionary

    Raises:
        JSONRPCError: If parsing or validation fails
    """
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        request = json.loads(data)
    except json.JSONDecodeError as e:
        raise JSONRPCError(JSONRPCErrorCode.PARSE_ERROR, f"Parse error: {str(e)}")
    except Exception as e:
        raise JSONRPCError(JSONRPCErrorCode.PARSE_ERROR, f"Parse error: {str(e)}")

    if not isinstance(request, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_REQUEST, "Request must be a JSON object"
        )

    validate_request(request)
    return request


def is_notification(request: Dict[str, Any]) -> bool:
    """
    Check if a request is a notification (no ID)

    Args:
        request: Request dictionary

    Returns:
        True if notification, False otherwise
    """
    return "id" not in request or request["id"] is None


def is_streaming_result(result: Any) -> bool:
    """
    Check if result is an async generator (streaming response)

    Args:
        result: Result to check

    Returns:
        True if async generator, False otherwise
    """
    return inspect.isasyncgen(result) or isinstance(result, AsyncIterator)
