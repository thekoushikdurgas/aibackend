"""AI21 Labs WebSocket JSON-RPC handlers."""

import base64
import logging
from typing import Any, Dict, Optional

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.ai21.answer import AI21AnswerService
from app.services.ai21.completion import AI21CompletionService
from app.services.ai21.library import AI21LibraryService
from app.services.llm.ai21 import AI21Provider
from app.services.llm.base import LLMConfig

logger = logging.getLogger(__name__)


def _require_key() -> None:
    from app.config import settings

    if not settings.ai21_api_key:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "AI21 API key not configured (set ai21_api_key in config)",
        )


async def handle_ai21_complete(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        return await _ai21_complete_impl(params)
    except JSONRPCError:
        raise
    except Exception as e:
        logger.exception("ai21.complete failed")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            str(e),
        ) from e


async def _ai21_complete_impl(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Text completion (j2-ultra / j2-mid / j2-light) via AI21CompletionService,
    or chat-style completion via AI21Provider when use_chat=true.
    Params: prompt (required), model, max_tokens, temperature, top_p, num_results, use_chat (bool)
    """
    _require_key()
    prompt = (params or {}).get("prompt") or (params or {}).get("message")
    if not prompt or not str(prompt).strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Missing required parameter: prompt",
        )
    p = params or {}
    if p.get("use_chat"):
        provider = AI21Provider(model=p.get("model"))
        cfg = LLMConfig(
            model=p.get("model") or provider.default_model,
            temperature=float(p.get("temperature", 0.7)),
            max_tokens=int(p.get("max_tokens", 1024)),
        )
        resp = await provider.generate(
            str(prompt),
            cfg,
            context=p.get("context"),
            conversation_history=p.get("conversation_history"),
        )
        return {
            "text": resp.text,
            "model": resp.model,
            "provider": resp.provider,
            "usage": resp.usage,
        }
    svc = AI21CompletionService()
    result = await svc.complete(
        prompt=str(prompt),
        model=str(p.get("model") or "j2-mid"),
        num_results=int(p.get("num_results") or 1),
        max_tokens=int(p.get("max_tokens") or 256),
        min_tokens=int(p.get("min_tokens") or 0),
        temperature=float(p.get("temperature", 0.7)),
        top_p=float(p.get("top_p", 1.0)),
        stop_sequences=p.get("stop_sequences"),
        top_k_return=int(p.get("top_k_return") or 0),
    )
    return {"result": result}


async def handle_ai21_answer(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Q&A: single-document (context + question) or RAG (question + document_ids).
    Params: question (required); context + question for single-doc; document_ids + question for RAG.
    """
    _require_key()
    p = params or {}
    question = p.get("question") or p.get("query")
    if not question or not str(question).strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Missing required parameter: question",
        )
    svc = AI21AnswerService()
    doc_ids = p.get("document_ids") or p.get("documentIds")
    if doc_ids:
        if not isinstance(doc_ids, list):
            doc_ids = [str(doc_ids)]
        out = await svc.answer_rag(str(question), [str(x) for x in doc_ids])
        return out
    context = p.get("context") or ""
    if not str(context).strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Provide context (single-doc) or document_ids (RAG)",
        )
    out = await svc.answer_single_document(str(context), str(question))
    return out


async def handle_ai21_summarize(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Summarization via AI21 chat (long-form text in `text` or `content`)."""
    p = params or {}
    text = p.get("text") or p.get("content")
    if not text or not str(text).strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Missing required parameter: text or content",
        )
    prompt = f"Summarize the following in clear prose. Preserve key facts and structure.\n\n{str(text).strip()}"
    merged: Dict[str, Any] = {
        "prompt": prompt,
        "use_chat": True,
        "model": p.get("model"),
        "max_tokens": int(p.get("max_tokens", 1024) or 1024),
        "temperature": float(p.get("temperature", 0.3) or 0.3),
    }
    return await handle_ai21_complete(merged, user, connection_id)


async def handle_ai21_library(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Library operations. Params: action = list | search | upload | delete

    - list: no extra params
    - search: query, file_ids (optional)
    - upload: file_name, file_content (base64) or raw string in file_text
    - delete: file_id
    """
    _require_key()
    p = params or {}
    action = str(p.get("action") or "list").lower().strip()
    lib = AI21LibraryService()

    if action == "list":
        files = await lib.list_files()
        return {"files": files, "action": "list"}

    if action == "search":
        q = p.get("query") or p.get("q")
        if not q:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                "search requires query",
            )
        return await lib.search(str(q), p.get("file_ids") or p.get("fileIds"))

    if action == "upload":
        name = p.get("file_name") or p.get("filename") or "upload.txt"
        raw = p.get("file_content")
        text = p.get("file_text")
        if raw:
            try:
                data = base64.b64decode(raw) if isinstance(raw, str) else raw
            except Exception as e:
                raise JSONRPCError(
                    JSONRPCErrorCode.INVALID_PARAMS,
                    f"Invalid base64 file_content: {e}",
                ) from e
        elif text is not None:
            data = str(text).encode("utf-8")
        else:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                "upload requires file_content (base64) or file_text",
            )
        labels = p.get("labels")
        if labels and not isinstance(labels, list):
            labels = [str(labels)]
        return await lib.upload_file(data, str(name), labels=labels)

    if action == "delete":
        fid = p.get("file_id") or p.get("fileId")
        if not fid:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                "delete requires file_id",
            )
        ok = await lib.delete_file(str(fid))
        return {"deleted": ok, "file_id": fid}

    raise JSONRPCError(
        JSONRPCErrorCode.INVALID_PARAMS,
        f"Unknown library action: {action}. Use list, search, upload, delete.",
    )


def get_methods() -> Dict[str, Any]:
    return {
        "ai21.complete": handle_ai21_complete,
        "ai21.answer": handle_ai21_answer,
        "ai21.summarize": handle_ai21_summarize,
        "ai21.library": handle_ai21_library,
    }
