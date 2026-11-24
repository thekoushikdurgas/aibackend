"""Tests for settings.ai_providers WebSocket handlers."""

from __future__ import annotations

import pytest

from app.api.ws_methods import settings_ai_providers
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


def test_settings_ai_providers_methods_registered():
    methods = settings_ai_providers.get_methods()
    assert "settings.ai_providers.get" in methods
    assert "settings.ai_providers.update" in methods


@pytest.mark.asyncio
async def test_get_returns_sections_and_values(monkeypatch, tmp_path):
    from app.config_runtime_overlay import SettingsOverlayProxy
    from app import config as config_mod

    class _Base:
        api_key = None
        nvidia_api_key = None
        nvidia_base_url = "https://integrate.api.nvidia.com/v1"
        nvidia_genai_base_url = "https://ai.api.nvidia.com/v1"
        nvidia_nim_base_url = ""
        nvidia_chat_model = "nvidia/llama-3.3-nemotron-super-49b-v1"
        ai_provider_overrides_path = str(tmp_path / "overrides.json")

        def __getattr__(self, name: str):
            return None

    proxy = SettingsOverlayProxy(_Base())
    monkeypatch.setattr(settings_ai_providers, "settings", proxy)
    monkeypatch.setattr(config_mod, "settings", proxy)

    result = await settings_ai_providers.handle_settings_ai_providers_get({})
    assert "sections" in result
    assert "values" in result
    assert any(s.get("id") == "nvidia" for s in result["sections"])
    nv = result["values"].get("nvidia_api_key")
    assert isinstance(nv, dict)
    assert nv.get("set") is False


@pytest.mark.asyncio
async def test_update_nvidia_key_and_empty_does_not_wipe(monkeypatch, tmp_path):
    from app.config_runtime_overlay import SettingsOverlayProxy
    from app import config as config_mod
    from app.services.llm.factory import LLMProviderFactory

    class _Base:
        api_key = None
        nvidia_api_key = None
        nvidia_base_url = "https://integrate.api.nvidia.com/v1"
        nvidia_genai_base_url = "https://ai.api.nvidia.com/v1"
        nvidia_nim_base_url = ""
        nvidia_chat_model = "nvidia/llama-3.3-nemotron-super-49b-v1"
        ai_provider_overrides_path = str(tmp_path / "overrides.json")

        def __getattr__(self, name: str):
            return None

    proxy = SettingsOverlayProxy(_Base())
    monkeypatch.setattr(settings_ai_providers, "settings", proxy)
    monkeypatch.setattr(config_mod, "settings", proxy)
    monkeypatch.setattr(LLMProviderFactory, "clear_cache", staticmethod(lambda: None))

    def _apply(proxy_arg, updates):
        proxy_arg.merge_overlay(updates)
        LLMProviderFactory.clear_cache()

    monkeypatch.setattr(
        settings_ai_providers, "apply_ai_provider_updates", _apply
    )

    out = await settings_ai_providers.handle_settings_ai_providers_update(
        {"updates": {"nvidia_api_key": "nvapi-test-secret-key"}}
    )
    assert out["ok"] is True
    assert out["applied"] == 1
    assert proxy.nvidia_api_key == "nvapi-test-secret-key"

    out2 = await settings_ai_providers.handle_settings_ai_providers_update(
        {"updates": {"nvidia_api_key": "   "}}
    )
    assert out2["applied"] == 0
    assert proxy.nvidia_api_key == "nvapi-test-secret-key"


@pytest.mark.asyncio
async def test_update_rejects_unknown_keys(monkeypatch, tmp_path):
    from app.config_runtime_overlay import SettingsOverlayProxy

    class _Base:
        api_key = None
        ai_provider_overrides_path = str(tmp_path / "overrides.json")

        def __getattr__(self, name: str):
            return None

    proxy = SettingsOverlayProxy(_Base())
    monkeypatch.setattr(settings_ai_providers, "settings", proxy)

    with pytest.raises(JSONRPCError) as exc:
        await settings_ai_providers.handle_settings_ai_providers_update(
            {"updates": {"not_a_real_field": "x"}}
        )
    assert exc.value.code == JSONRPCErrorCode.INVALID_PARAMS
