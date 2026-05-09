"""
Tests for WebSocket Method Handlers
"""

import pytest
from app.api.ws_methods import health, chat, agents
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


def test_health_methods():
    """Test health method handlers"""
    methods = health.get_methods()
    assert "system.health" in methods
    assert "system.ready" in methods
    assert "system.live" in methods


@pytest.mark.asyncio
async def test_system_health_handler():
    """Test system.health handler"""
    result = await health.handle_system_health({})
    assert "status" in result
    assert result["status"] in ["healthy", "degraded"]
    assert "services" in result


@pytest.mark.asyncio
async def test_system_ready_handler():
    """Test system.ready handler"""
    result = await health.handle_system_ready({})
    assert result["status"] == "ready"


@pytest.mark.asyncio
async def test_system_live_handler():
    """Test system.live handler"""
    result = await health.handle_system_live({})
    assert result["status"] == "alive"


def test_chat_methods():
    """Test chat method handlers"""
    methods = chat.get_methods()
    assert "chat.completions" in methods
    assert "chat.providers" in methods


@pytest.mark.asyncio
async def test_chat_providers_handler():
    """Test chat.providers handler"""
    result = await chat.handle_chat_providers({})
    assert "providers" in result
    assert isinstance(result["providers"], list)


def test_agents_methods():
    """Test agents method handlers"""
    methods = agents.get_methods()
    assert "agents.list" in methods
    assert "agents.analyze" in methods


@pytest.mark.asyncio
async def test_agents_list_handler():
    """Test agents.list handler"""
    result = await agents.handle_agents_list({})
    assert "agents" in result
    assert isinstance(result["agents"], list)


@pytest.mark.asyncio
async def test_chat_completions_missing_message():
    """Test chat.completions with missing message"""
    with pytest.raises(JSONRPCError) as e:
        await chat.handle_chat_completions({})
    assert e.value.code == JSONRPCErrorCode.INVALID_PARAMS


@pytest.mark.asyncio
async def test_agents_analyze_missing_params():
    """Test agents.analyze with missing params"""
    with pytest.raises(JSONRPCError) as e:
        await agents.handle_agents_analyze({})
    assert e.value.code == JSONRPCErrorCode.INVALID_PARAMS

