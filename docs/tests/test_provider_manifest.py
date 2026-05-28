"""Tests for provider manifest and OpenAI-compatible base."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_MANIFEST = (
    Path(__file__).resolve().parent.parent.parent / "config" / "provider_manifest.json"
)


def test_manifest_loads():
    data = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert data["version"] == 1
    providers = data["providers"]
    assert len(providers) >= 30
    ids = {p["id"] for p in providers}
    assert "openai" in ids
    assert "groq" in ids
    assert "postman_tools" in ids
    disabled = [p for p in providers if p.get("implementation") == "disabled"]
    assert any(p["id"] == "postman_tools" for p in disabled)


def test_openai_compat_build_messages():
    from app.services.llm.openai_compat import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(
        provider_name="test",
        api_key="sk-test",
        default_model="m",
        base_url="https://example.com/v1",
    )
    msgs = p._build_messages("hi", context="ctx", conversation_history=None)
    assert msgs[-1]["content"] == "hi"
    assert any("ctx" in str(m.get("content", "")) for m in msgs)


@pytest.mark.asyncio
async def test_factory_lists_manifest_providers():
    from app.services.llm.factory import LLMProviderFactory

    names = LLMProviderFactory.list_providers()
    assert "openai" in names
    assert "deepseek" in names
    assert "ollama" in names
