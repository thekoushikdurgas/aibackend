"""
IDE-oriented code helpers (Void-style apply / inline complete).
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.ai_service import ai_service
from app.services.llm import LLMConfig, get_llm_provider

logger = logging.getLogger(__name__)

_FAST_APPLY_SYSTEM = """You are a precise coding assistant. Apply the user's instruction to the given source code.

Output ONLY one or more search/replace blocks in this exact format:

<<<<<<< ORIGINAL
(lines copied EXACTLY from the source — must match byte-for-byte including whitespace)
=======
(replacement lines)
>>>>>>> UPDATED

Rules:
- Each ORIGINAL block must appear verbatim in the source file.
- Prefer minimal ORIGINAL regions that uniquely identify the edit location.
- If replacing the whole file is clearer, use one block where ORIGINAL is the entire source.
- Do not wrap output in markdown code fences unless the instruction asks for prose.
- Do not add commentary outside the blocks."""

_CTRLK_SYSTEM = """You are a precise coding assistant. The user selected a region to edit inline.

Output ONLY search/replace blocks in this exact format:

<<<<<<< ORIGINAL
(selected snippet exactly as provided — must match)
=======
(replacement)
>>>>>>> UPDATED

If the change spans beyond the selection, you may include minimal surrounding lines in ORIGINAL
so it still matches the full file, but keep ORIGINAL as small as practical."""

_FIM_USER_TEMPLATE = """Complete the missing code between prefix and suffix. Output ONLY the middle text (no markdown fences, no explanation).

<prefix>
{prefix}
</prefix>

<suffix>
{suffix}
</suffix>
"""


def _build_apply_context(
    source: str,
    path: Optional[str],
    language: Optional[str],
    selection: Optional[str],
    mode: Optional[str],
) -> str:
    parts: List[str] = []
    if path:
        parts.append(f"File path: {path}")
    if language:
        parts.append(f"Language: {language}")
    parts.append("<source_file>")
    parts.append(source)
    parts.append("</source_file>")
    if selection and selection.strip():
        parts.append("")
        parts.append("<selection>")
        parts.append(selection.strip())
        parts.append("</selection>")
    if mode:
        parts.append("")
        parts.append(f"Mode: {mode}")
    return "\n".join(parts)


async def handle_ide_code_apply(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """Stream code edits as Void-style ORIGINAL/UPDATED blocks."""
    source = params.get("source")
    if not isinstance(source, str):
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing or invalid parameter: source"
        )

    instruction = params.get("instruction", "")
    if not isinstance(instruction, str) or not instruction.strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing or invalid parameter: instruction"
        )

    mode = params.get("mode")
    if mode is not None and not isinstance(mode, str):
        mode = None

    selection = params.get("selection")
    if selection is not None and not isinstance(selection, str):
        selection = None

    path = params.get("path")
    if path is not None and not isinstance(path, str):
        path = None

    language = params.get("language")
    if language is not None and not isinstance(language, str):
        language = None

    provider_name = params.get("provider")
    model = params.get("model")
    temperature = float(params.get("temperature", 0.2))
    max_tokens = int(params.get("max_tokens", 8192))
    stream = bool(params.get("stream", True))

    context_body = _build_apply_context(source, path, language, selection, mode)
    system = _CTRLK_SYSTEM if mode == "ctrlk" else _FAST_APPLY_SYSTEM
    full_context = f"{system}\n\n{context_body}"

    config = LLMConfig(
        model=model or None,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    try:
        get_llm_provider(provider_name)
    except Exception as e:
        raise JSONRPCError(JSONRPCErrorCode.PROVIDER_ERROR, f"Provider error: {str(e)}")

    if stream:
        return _stream_ide_apply(provider_name, config, instruction, full_context)

    try:
        provider = get_llm_provider(provider_name)
        response = await provider.generate(
            prompt=instruction,
            config=config,
            context=full_context,
            conversation_history=[],
        )
        return {
            "message": response.text,
            "provider": response.provider,
            "model": response.model,
        }
    except Exception as e:
        logger.error("ide.code.apply (non-stream) error: %s", e, exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"ide.code.apply failed: {str(e)}"
        )


async def _stream_ide_apply(
    provider_name: Optional[str],
    config: LLMConfig,
    message: str,
    context: str,
) -> AsyncGenerator[Dict[str, Any], None]:
    try:
        async for chunk_data in ai_service.stream_response(
            prompt=message,
            provider_name=provider_name,
            model=config.model,
            config=config,
            context=context,
            conversation_history=[],
            enable_token_counting=True,
            enable_buffering=True,
        ):
            if chunk_data["type"] == "chunk":
                yield {
                    "type": "chunk",
                    "content": chunk_data["content"],
                    "index": chunk_data.get("index", 0),
                    "provider": chunk_data.get("provider"),
                    "model": chunk_data.get("model"),
                }
            elif chunk_data["type"] == "complete":
                full_response = chunk_data.get("full_content", "")
                yield {
                    "type": "done",
                    "full_response": full_response,
                    "stats": chunk_data.get("stats", {}),
                    "provider": chunk_data.get("provider"),
                    "model": chunk_data.get("model"),
                }
            elif chunk_data["type"] == "error":
                yield {
                    "type": "error",
                    "error": chunk_data.get("error", "Unknown error"),
                }
    except Exception as e:
        logger.error("ide.code.apply stream error: %s", e, exc_info=True)
        yield {"type": "error", "error": str(e)}


async def handle_ide_code_complete(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """Fill-in-middle style completion (prefix + suffix)."""
    prefix = params.get("prefix", "")
    suffix = params.get("suffix", "")
    if not isinstance(prefix, str):
        prefix = ""
    if not isinstance(suffix, str):
        suffix = ""

    provider_name = params.get("provider")
    model = params.get("model")
    temperature = float(params.get("temperature", 0.1))
    max_tokens = int(params.get("max_tokens", 256))
    stream = bool(params.get("stream", False))

    user_prompt = _FIM_USER_TEMPLATE.format(prefix=prefix, suffix=suffix)
    system_ctx = (
        "You complete code in the middle. Output only the inserted code, "
        "no markdown, no backticks."
    )

    config = LLMConfig(
        model=model or None,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    try:
        get_llm_provider(provider_name)
    except Exception as e:
        raise JSONRPCError(JSONRPCErrorCode.PROVIDER_ERROR, f"Provider error: {str(e)}")

    if stream:
        return _stream_ide_apply(provider_name, config, user_prompt, system_ctx)

    try:
        provider = get_llm_provider(provider_name)
        response = await provider.generate(
            prompt=user_prompt,
            config=config,
            context=system_ctx,
            conversation_history=[],
        )
        return {
            "completion": response.text.strip(),
            "provider": response.provider,
            "model": response.model,
        }
    except Exception as e:
        logger.error("ide.code.complete error: %s", e, exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"ide.code.complete failed: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    return {
        "ide.code.apply": handle_ide_code_apply,
        "ide.code.complete": handle_ide_code_complete,
    }
