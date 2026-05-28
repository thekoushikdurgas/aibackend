#!/usr/bin/env python3
"""
Extract provider_manifest.json from docs/ai_provider Postman collections.

Run from ai.backend root:
  python scripts/postman_to_manifest.py
  python scripts/postman_to_manifest.py --write
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
_POSTMAN_DIR = _REPO / "docs" / "ai_provider"
_OUT = _BACKEND / "config" / "provider_manifest.json"

# Manual overrides: postman filename stem -> backend id / implementation
_ID_OVERRIDES: dict[str, str] = {
    "📌 Ollama API (Localhost & Cloud).postman_collection": "ollama",
    "📌 Ollama API (Localhost & Cloud).postman_collection (1)": "ollama",
    "📌 Amazon Bedrock API.postman_collection": "bedrock",
    "📌 Amazon Bedrock API.postman_collection (1)": "bedrock",
    "📌 Google Gemini API & Vertex AI API.postman_collection": "gemini",
    "📌 OctoAI API [NVIDIA].postman_collection": "nvidia",
    "📌 Hugging Face API.postman_collection": "huggingface",
    "📌 Deep Infra API.postman_collection": "deepinfra",
    "📌 Cerebras API ⚡.postman_collection": "cerebras",
    "📌 Groq API ⚡.postman_collection": "groq",
    "📌 SambaNova API ⚡.postman_collection": "sambanova",
    "⚡ LLM API Latency.postman_collection": "latency_benchmark",
    "🛠️ Postman Tool Generation API.postman_collection": "postman_tools",
    "📌 Alibaba Cloud (Aliyun).postman_collection": "dashscope",
    "📌 IBM watsonx.ai API.postman_collection": "watsonx",
    "📌 Docker Model Runner API (Localhost).postman_collection": "docker_model_runner",
    "📌 GitHub AI API.postman_collection": "github_ai",
    "📌 AI21 Labs API.postman_collection": "ai21",
    "📌 OpenAI API.postman_collection": "openai",
    "📌 DeepSeek API.postman_collection": "deepseek",
    "📌 Mistral AI API.postman_collection": "mistral",
    "📌 Together AI API.postman_collection": "together",
    "📌 Perplexity AI API.postman_collection": "perplexity",
    "📌 xAI API.postman_collection": "xai",
    "📌 OpenRouter API.postman_collection": "openrouter",
    "📌 NVIDIA AI API.postman_collection": "nvidia",
    "📌 Fireworks AI API.postman_collection": "fireworks",
    "📌 Cohere API.postman_collection": "cohere",
    "📌 Hyperbolic API.postman_collection": "hyperbolic",
    "📌 Reka AI API.postman_collection": "reka",
    "📌 Anyscale API.postman_collection": "anyscale",
    "📌 fal.ai API.postman_collection": "fal",
    "📌 Deepgram API.postman_collection": "deepgram",
    "📌 ElevenLabs API.postman_collection": "elevenlabs",
    "📌 Stability AI API.postman_collection": "stability",
    "📌 Replicate API.postman_collection": "replicate",
    "📌 Eden AI API.postman_collection": "eden",
    "📌 Novita API.postman_collection": "novita",
    "📌 Nebius AI API.postman_collection": "nebius",
    "📌 kluster.ai API.postman_collection": "kluster",
    "📌 Lamini API [OOB].postman_collection": "lamini",
    "📌 Lepton AI API [OOB].postman_collection": "lepton",
}

_IMPL_OVERRIDES: dict[str, str] = {
    "ollama": "native",
    "huggingface": "native",
    "gemini": "native",
    "vertex": "native",
    "ai21": "native",
    "cohere": "native",
    "nvidia": "native",
    "bedrock": "native",
    "dashscope": "native",
    "watsonx": "native",
    "deepgram": "ws_only",
    "elevenlabs": "ws_only",
    "fal": "ws_only",
    "stability": "ws_only",
    "replicate": "ws_only",
    "eden": "native",
    "latency_benchmark": "benchmark",
    "postman_tools": "disabled",
    "openai": "openai_compat",
    "deepseek": "openai_compat",
    "mistral": "openai_compat",
    "together": "openai_compat",
    "perplexity": "openai_compat",
    "xai": "openai_compat",
    "sambanova": "openai_compat",
    "github_ai": "openai_compat",
    "docker_model_runner": "openai_compat",
    "novita": "openai_compat",
    "nebius": "openai_compat",
    "kluster": "openai_compat",
    "lamini": "openai_compat",
    "lepton": "openai_compat",
}

_CATEGORY_MAP: dict[str, str] = {
    "deepgram": "audio",
    "elevenlabs": "audio",
    "fal": "image",
    "stability": "image",
    "replicate": "image",
    "eden": "aggregator",
    "latency_benchmark": "benchmark",
}


def _slugify(name: str) -> str:
    s = name.strip()
    if s.startswith("📌 "):
        s = s[3:]
    if s.startswith("⚡ "):
        s = s[2:]
    if s.startswith("🛠️ "):
        s = s[2:]
    s = re.sub(r"\s+API.*$", "", s, flags=re.I)
    s = re.sub(r"\s*\[.*?\]\s*", " ", s)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "unknown"


def _walk_requests(items: list[Any], paths: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if "request" in it:
            req = it["request"]
            url = req.get("url")
            raw = ""
            if isinstance(url, dict):
                raw = url.get("raw") or ""
                if not raw and url.get("path"):
                    raw = "/".join(str(p) for p in url["path"])
            elif isinstance(url, str):
                raw = url
            out.append(
                {"name": it.get("name", ""), "method": req.get("method"), "url": raw}
            )
        if "item" in it:
            out.extend(_walk_requests(it["item"], paths + [it.get("name", "")]))
    return out


def _detect_capabilities(
    requests: list[dict[str, Any]], collection_name: str
) -> list[str]:
    caps: set[str] = set()
    joined = " ".join(r.get("url", "") for r in requests).lower()
    if "chat/completions" in joined or "completions" in joined:
        caps.add("chat")
    if "embed" in joined:
        caps.add("embed")
    if any(x in joined for x in ("images", "image/generations", "flux", "stable")):
        caps.add("image")
    if any(x in joined for x in ("audio", "speech", "transcri", "tts")):
        caps.add("audio")
    if "video" in joined or "veo" in joined:
        caps.add("video")
    if not caps:
        low = collection_name.lower()
        if "deepgram" in low or "eleven" in low:
            caps.add("audio")
        elif "stability" in low or "replicate" in low or "fal" in low:
            caps.add("image")
        elif "latency" in low:
            caps.add("benchmark")
        else:
            caps.add("chat")
    return sorted(caps)


def _latency_tier(provider_id: str) -> str:
    if provider_id in ("groq", "cerebras", "sambanova"):
        return "fast"
    return "normal"


def _parse_collection(path: Path) -> dict[str, Any] | None:
    stem = path.name.replace(".json", "")
    if stem in _ID_OVERRIDES:
        provider_id = _ID_OVERRIDES[stem]
    else:
        provider_id = _slugify(path.stem.replace(".postman_collection", ""))

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    info = data.get("info") or {}
    display_name = info.get("name", path.stem)
    variables = {
        v.get("key"): v.get("value") for v in data.get("variable") or [] if v.get("key")
    }
    base_url = variables.get("baseUrl") or variables.get("base_url") or ""

    auth = data.get("auth") or {}
    auth_type = auth.get("type", "bearer")

    requests = _walk_requests(data.get("item") or [], [])
    capabilities = _detect_capabilities(requests, display_name)

    implementation = _IMPL_OVERRIDES.get(provider_id)
    if not implementation:
        if "chat/completions" in " ".join(r.get("url", "") for r in requests).lower():
            implementation = "openai_compat"
        elif provider_id in ("gemini",):
            implementation = "native"
        else:
            implementation = "openai_compat"

    category = _CATEGORY_MAP.get(provider_id, "chat")
    if capabilities == ["benchmark"]:
        category = "benchmark"

    api_key_env = f"{provider_id.upper()}_API_KEY".replace("-", "_")
    base_url_env = f"{provider_id.upper()}_BASE_URL".replace("-", "_")
    model_env = f"{provider_id.upper()}_MODEL".replace("-", "_")

    postman_link = (info.get("_collection_link") or "").strip()

    return {
        "id": provider_id,
        "display_name": display_name,
        "postman_file": path.name,
        "postman_link": postman_link,
        "implementation": implementation,
        "category": category,
        "capabilities": capabilities,
        "latency_tier": _latency_tier(provider_id),
        "auth_type": auth_type,
        "api_key_env": api_key_env,
        "base_url_env": base_url_env,
        "model_env": model_env,
        "default_base_url": base_url or None,
        "requires_api_key": implementation not in ("disabled", "benchmark")
        and provider_id != "ollama",
        "enabled": implementation != "disabled",
    }


def build_manifest() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(_POSTMAN_DIR.glob("*.postman_collection*.json")):
        entry = _parse_collection(path)
        if not entry:
            continue
        pid = entry["id"]
        if pid in seen:
            continue
        seen.add(pid)
        entries.append(entry)
    entries.sort(key=lambda e: e["id"])
    return {
        "version": 1,
        "generated_from": "docs/ai_provider",
        "providers": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write", action="store_true", help="Write config/provider_manifest.json"
    )
    args = parser.parse_args()
    manifest = build_manifest()
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        _OUT.parent.mkdir(parents=True, exist_ok=True)
        _OUT.write_text(text, encoding="utf-8")
        print(f"Wrote {_OUT} ({len(manifest['providers'])} providers)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
