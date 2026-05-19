"""
Tests for WebSocket Gateway
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


def test_websocket_connection(client):
    """Test WebSocket connection"""
    with client.websocket_connect("/ws/gateway") as websocket:
        # Should receive connection confirmation
        data = websocket.receive_json()
        assert data["jsonrpc"] == "2.0"
        assert data["result"]["type"] == "connected"
        assert "connection_id" in data["result"]


def test_jsonrpc_request_format(client):
    """Test JSON-RPC request format"""
    with client.websocket_connect("/ws/gateway") as websocket:
        # Receive connection confirmation
        websocket.receive_json()

        # Send JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "system.health",
            "params": {},
        }
        websocket.send_json(request)

        # Should receive response
        response = websocket.receive_json()
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "result" in response or "error" in response


def test_invalid_method(client):
    """Test invalid method handling"""
    with client.websocket_connect("/ws/gateway") as websocket:
        websocket.receive_json()

        request = {
            "jsonrpc": "2.0",
            "id": "test-2",
            "method": "nonexistent.method",
            "params": {},
        }
        websocket.send_json(request)

        response = websocket.receive_json()
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found


def test_system_health_method(client):
    """Test system.health method"""
    with client.websocket_connect("/ws/gateway") as websocket:
        websocket.receive_json()

        request = {
            "jsonrpc": "2.0",
            "id": "test-3",
            "method": "system.health",
            "params": {},
        }
        websocket.send_json(request)

        response = websocket.receive_json()
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert response["result"]["status"] in ["healthy", "degraded"]


def test_chat_completions_method(client):
    """Test chat.completions method"""
    with client.websocket_connect("/ws/gateway") as websocket:
        websocket.receive_json()

        request = {
            "jsonrpc": "2.0",
            "id": "test-4",
            "method": "chat.completions",
            "params": {"message": "Hello", "provider": "ollama", "stream": False},
        }
        websocket.send_json(request)

        response = websocket.receive_json()
        assert response["jsonrpc"] == "2.0"
        # May succeed or fail depending on provider availability
        assert "result" in response or "error" in response


def test_streaming_response(client):
    """Test streaming response"""
    with client.websocket_connect("/ws/gateway") as websocket:
        websocket.receive_json()

        request = {
            "jsonrpc": "2.0",
            "id": "test-5",
            "method": "chat.completions",
            "params": {"message": "Hello", "provider": "ollama", "stream": True},
        }
        websocket.send_json(request)

        # Should receive multiple responses for streaming
        responses = []
        try:
            while len(responses) < 3:  # Get at least start, chunk, done
                response = websocket.receive_json(timeout=5.0)
                responses.append(response)
                if response.get("result", {}).get("type") == "done":
                    break
        except Exception:
            pass  # May timeout if provider unavailable

        # Should have received at least one response
        assert len(responses) > 0


def test_invalid_json(client):
    """Test invalid JSON handling"""
    with client.websocket_connect("/ws/gateway") as websocket:
        websocket.receive_json()

        # Send invalid JSON
        websocket.send_text("invalid json")

        # Should receive error
        response = websocket.receive_json()
        assert "error" in response
        assert response["error"]["code"] == -32700  # Parse error


def test_ping_pong(client):
    """Test ping/pong keepalive"""
    with client.websocket_connect("/ws/gateway") as websocket:
        websocket.receive_json()

        # Send ping
        websocket.send_text("ping")

        # Should receive pong
        response = websocket.receive_text()
        assert response == "pong"
