import json
from typing import Any, cast

import pytest

from app.api.ws_gateway import WebSocketGateway


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_gateway_streams_async_generator_handler() -> None:
    async def stream_handler(params, user=None, connection_id=None):
        yield {"type": "notification", "value": params["value"]}

    gateway = WebSocketGateway()
    gateway.methods = {"test.stream": stream_handler}
    websocket = FakeWebSocket()

    await gateway.handle_message(
        cast(Any, websocket),
        "conn-test",
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "req-1",
                "method": "test.stream",
                "params": {"value": 42},
            }
        ),
    )

    assert websocket.sent == [
        {
            "jsonrpc": "2.0",
            "result": {"type": "notification", "value": 42},
            "id": "req-1",
        }
    ]


@pytest.mark.asyncio
async def test_gateway_streams_async_handler_returning_generator() -> None:
    """Async handlers (e.g. chat.completions with stream=true) return generators after await."""

    async def stream_handler(params, user=None, connection_id=None):
        async def _gen():
            yield {"type": "chunk", "content": params["message"]}

        return _gen()

    gateway = WebSocketGateway()
    gateway.methods = {"chat.completions": stream_handler}
    websocket = FakeWebSocket()

    await gateway.handle_message(
        cast(Any, websocket),
        "conn-test",
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "req-2",
                "method": "chat.completions",
                "params": {"message": "hello"},
            }
        ),
    )

    assert websocket.sent == [
        {
            "jsonrpc": "2.0",
            "result": {"type": "chunk", "content": "hello"},
            "id": "req-2",
        }
    ]
