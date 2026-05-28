"""
Tests for JSON-RPC 2.0 Protocol
"""

import pytest
from app.core.jsonrpc import (
    create_request,
    create_response,
    create_error_response,
    parse_request,
    validate_request,
    JSONRPCError,
    JSONRPCErrorCode,
)


def test_create_request():
    """Test request creation"""
    request = create_request("test.method", {"param": "value"}, "req-1")
    assert request["jsonrpc"] == "2.0"
    assert request["method"] == "test.method"
    assert request["params"] == {"param": "value"}
    assert request["id"] == "req-1"


def test_create_response():
    """Test response creation"""
    response = create_response("req-1", {"result": "data"})
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "req-1"
    assert response["result"] == {"result": "data"}


def test_create_error_response():
    """Test error response creation"""
    error = create_error_response("req-1", -32601, "Method not found")
    assert error["jsonrpc"] == "2.0"
    assert error["id"] == "req-1"
    assert error["error"]["code"] == -32601
    assert error["error"]["message"] == "Method not found"


def test_validate_request():
    """Test request validation"""
    # Valid request
    valid_request = {
        "jsonrpc": "2.0",
        "method": "test.method",
        "params": {},
        "id": "req-1",
    }
    validate_request(valid_request)  # Should not raise

    # Invalid jsonrpc version
    invalid_request = {"jsonrpc": "1.0", "method": "test.method", "id": "req-1"}
    with pytest.raises(JSONRPCError) as e:
        validate_request(invalid_request)
    assert e.value.code == JSONRPCErrorCode.INVALID_REQUEST

    # Missing method
    invalid_request = {"jsonrpc": "2.0", "id": "req-1"}
    with pytest.raises(JSONRPCError) as e:
        validate_request(invalid_request)
    assert e.value.code == JSONRPCErrorCode.INVALID_REQUEST


def test_parse_request():
    """Test request parsing"""
    json_str = '{"jsonrpc":"2.0","method":"test.method","params":{},"id":"req-1"}'
    request = parse_request(json_str)
    assert request["method"] == "test.method"
    assert request["id"] == "req-1"

    # Invalid JSON
    with pytest.raises(JSONRPCError) as e:
        parse_request("invalid json")
    assert e.value.code == JSONRPCErrorCode.PARSE_ERROR
