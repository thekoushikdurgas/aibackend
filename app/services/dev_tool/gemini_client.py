"""Gemini HTTP client for Dev AI toolbox operations."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.services.dev_tool import prompts

logger = logging.getLogger(__name__)

MODEL_FLASH = "gemini-2.5-flash"
MODEL_PRO = "gemini-2.5-pro"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_HTML_CHARS = 120_000


def _api_key() -> str:
    key = settings.gemini_api_key
    if not key or any(p in key.lower() for p in ("placeholder", "your-api-key")):
        raise ValueError("Gemini API Key is not configured on the backend.")
    return key


def strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    m = re.match(r"^```[\w]*\n?(.*?)```\s*$", t, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return t


def truncate_html(html: str, max_chars: int = MAX_HTML_CHARS) -> str:
    if len(html) <= max_chars:
        return html
    return html[:max_chars] + "\n<!-- [truncated for model context] -->"


class DevToolGeminiClient:
    """Thin Gemini generateContent wrapper for dev-tool prompts."""

    def __init__(self, timeout: float = 90.0) -> None:
        self.timeout = timeout

    async def _generate(
        self,
        prompt: str,
        *,
        model: str = MODEL_FLASH,
        response_mime_type: Optional[str] = None,
        response_schema: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {},
        }
        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type
        if response_schema:
            payload["generationConfig"]["responseSchema"] = response_schema
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"{API_BASE}/{model}:generateContent?key={_api_key()}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return ""
        return (parts[0].get("text") or "").strip()

    async def minify_code(self, code: str, language: str) -> str:
        text = await self._generate(
            prompts.minify_prompt(code, language), model=MODEL_FLASH
        )
        return strip_code_fences(text)

    async def generate_cheatsheet(self, topic: str) -> str:
        return await self._generate(prompts.cheatsheet_prompt(topic), model=MODEL_FLASH)

    async def generate_and_explain_regex(self, description: str) -> Dict[str, str]:
        text = await self._generate(
            prompts.regex_generate_contents(description),
            model=MODEL_FLASH,
            response_mime_type="application/json",
            response_schema=prompts.REGEX_RESPONSE_SCHEMA,
        )
        try:
            parsed = json.loads(text)
            return {
                "regex": str(parsed.get("regex", "")),
                "explanation": str(parsed.get("explanation", "")),
            }
        except json.JSONDecodeError as e:
            logger.error("regex JSON parse failed: %s raw=%s", e, text[:500])
            raise ValueError("Failed to parse regex response from the model.") from e

    async def explain_regex(self, regex: str) -> str:
        return await self._generate(
            prompts.regex_explain_prompt(regex), model=MODEL_FLASH
        )

    async def generate_types(
        self, json_string: str, type_system: str, root_type_name: str
    ) -> str:
        text = await self._generate(
            prompts.json_to_type_prompt(json_string, type_system, root_type_name),
            model=MODEL_PRO,
        )
        return strip_code_fences(text)

    async def refactor_code(self, code: str, language: str, instructions: str) -> str:
        text = await self._generate(
            prompts.refactor_prompt(code, language, instructions),
            model=MODEL_PRO,
        )
        return strip_code_fences(text)

    async def generate_code_from_html(self, html: str) -> str:
        truncated = truncate_html(html)
        text = await self._generate(
            prompts.html_to_code_prompt(truncated), model=MODEL_PRO
        )
        return strip_code_fences(text)

    async def enhance_prompt(self, prompt: str) -> str:
        return await self._generate(
            prompts.enhance_prompt_text(prompt), model=MODEL_PRO
        )

    async def generate_memory_title(self, content: str, memory_type: str) -> str:
        text = await self._generate(
            prompts.memory_title_prompt(content, memory_type), model=MODEL_FLASH
        )
        return text.strip().strip("\"'")

    async def generate_ceto_prompts(self, topic: str) -> str:
        return await self._generate(prompts.ceto_prompts_text(topic), model=MODEL_PRO)
