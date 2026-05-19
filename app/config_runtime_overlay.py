"""
Runtime overlay for AI provider fields on top of pydantic Settings.

Keeps a stable `settings` object identity so `from app.config import settings` continues
to see updates after merging JSON-backed overrides.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _resolve_overrides_path(raw: str) -> Path:
    p = Path((raw or "").strip() or "./data/ai_provider_overrides.json")
    if not p.is_absolute():
        p = BACKEND_ROOT / p
    return p


class SettingsOverlayProxy:
    __slots__ = ("_base", "_path", "_overlay", "_lock")

    def __init__(self, base: Any):
        self._base = base
        raw_path = str(getattr(base, "ai_provider_overrides_path", "") or "").strip()
        if not raw_path:
            raw_path = "./data/ai_provider_overrides.json"
        self._path = _resolve_overrides_path(raw_path)
        self._overlay: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._load_disk()

    @property
    def overrides_path(self) -> Path:
        return self._path

    def _load_disk(self) -> None:
        with self._lock:
            if self._path.is_file():
                try:
                    with open(self._path, encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        self._overlay = {
                            k: v for k, v in data.items() if isinstance(k, str)
                        }
                        return
                except (json.JSONDecodeError, OSError, TypeError):
                    pass
            self._overlay = {}

    def _atomic_write(self, obj: Dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            suffix=".json", dir=str(self._path.parent), text=True
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(obj, f, indent=2, sort_keys=True)
            os.replace(tmp, self._path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def merge_overlay(self, partial: Dict[str, Any]) -> None:
        """Merge non-empty updates into overlay and persist."""
        with self._lock:
            for k, v in partial.items():
                if v is None:
                    continue
                if isinstance(v, str) and not v.strip():
                    continue
                self._overlay[k] = v
            self._atomic_write(dict(self._overlay))

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("_base", "_path", "_overlay", "_lock"):
            object.__setattr__(self, name, value)
            return
        raise AttributeError(
            f"{type(self).__name__} is read-only; use apply_ai_provider_updates() for AI fields"
        )

    def __getattr__(self, name: str) -> Any:
        with self._lock:
            if name in self._overlay:
                return self._overlay[name]
        return getattr(self._base, name)


def apply_ai_provider_updates(
    proxy: SettingsOverlayProxy, updates: Dict[str, Any]
) -> None:
    """Persist partial updates, refresh in-memory overlay, reset provider caches."""
    proxy.merge_overlay(updates)
    from app.services.llm.factory import LLMProviderFactory

    LLMProviderFactory.clear_cache()
    from app.services.rag import embeddings as emb

    emb.reset_embedding_service_singleton()
