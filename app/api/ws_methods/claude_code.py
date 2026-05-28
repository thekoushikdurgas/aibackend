"""
JSON-RPC: Claude Code agent (claude_code.*).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.database import AsyncSessionLocal
from app.services.claude_code.models import QueryEngineConfig
from app.services.claude_code.parity_audit import run_parity_audit
from app.services.claude_code.permissions import ToolPermissionContext
from app.services.claude_code.port_manifest import build_port_manifest
from app.services.claude_code.query_engine import ClaudeCodeEngine
from app.services.claude_code.runtime import PortRuntime
from app.services.claude_code.session_store import load_session_db
from app.services.claude_code.tool_executor import ToolExecutorContext, default_context
from app.config import settings
from app.services.claude_code import commands_registry as cr
from app.services.claude_code import tools_registry as tr

logger = logging.getLogger(__name__)


def _perm_ctx(params: Dict[str, Any]) -> ToolPermissionContext:
    return ToolPermissionContext.from_iterables(
        list(params.get("deny_tool") or []),
        list(params.get("deny_prefix") or []),
    )


def _tool_ctx(params: Dict[str, Any]) -> ToolExecutorContext:
    root = params.get("workspace_root") or settings.claude_code_workspace_root
    path = Path(root).resolve() if root else default_context().workspace_root
    base = default_context()
    return ToolExecutorContext(
        workspace_root=path,
        bash_read_only=bool(
            params.get("bash_read_only", settings.claude_code_bash_read_only)
        ),
        bash_timeout=int(
            params.get("bash_timeout") or settings.claude_code_bash_timeout_seconds
        ),
        max_file_bytes=int(
            params.get("max_file_bytes") or settings.claude_code_max_file_bytes
        ),
        todos=base.todos,
    )


async def handle_claude_code_run(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = (params or {}).get("prompt") or (params or {}).get("message")
    if not prompt or not str(prompt).strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Missing required parameter: prompt",
        )
    p = params or {}
    eng = ClaudeCodeEngine.from_workspace(
        permission_context=_perm_ctx(p),
        tool_ctx=_tool_ctx(p),
        provider_name=p.get("provider"),
        model=p.get("model"),
        temperature=float(p.get("temperature", 0.35)),
    )
    if p.get("session_id"):
        eng.session_id = str(p["session_id"])
    cfg = QueryEngineConfig(
        max_turns=int(p.get("max_turns", 8)),
        max_budget_tokens=int(p.get("max_budget_tokens", 2000)),
        compact_after_turns=int(p.get("compact_after_turns", 12)),
        max_tool_rounds=int(p.get("max_tool_rounds", 8)),
    )
    eng.config = cfg
    rt = PortRuntime()
    limit = int(p.get("route_limit", 5))
    matches = rt.route_prompt(str(prompt), limit=limit)
    mc = tuple(m.name for m in matches if m.kind == "command")
    mt = tuple(m.name for m in matches if m.kind == "tool")
    turn = await eng.submit_message(str(prompt), mc, mt, ())
    return {
        "session_id": eng.session_id,
        "output": turn.output,
        "matched_commands": list(turn.matched_commands),
        "matched_tools": list(turn.matched_tools),
        "stop_reason": turn.stop_reason,
        "usage": {
            "input_tokens": turn.usage.input_tokens,
            "output_tokens": turn.usage.output_tokens,
        },
        "tool_events": list(turn.tool_events),
    }


async def handle_claude_code_bootstrap(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = (params or {}).get("prompt", "")
    p = params or {}
    eng = ClaudeCodeEngine.from_workspace(
        permission_context=_perm_ctx(p),
        tool_ctx=_tool_ctx(p),
        provider_name=p.get("provider"),
        model=p.get("model"),
    )
    if p.get("session_id"):
        eng.session_id = str(p["session_id"])
    sess = await PortRuntime().bootstrap_session(
        str(prompt), limit=int(p.get("limit", 5)), engine=eng
    )
    return {"markdown": sess.as_markdown(), "session_id": eng.session_id}


async def handle_claude_code_turn_loop(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = (params or {}).get("prompt")
    if not prompt:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: prompt"
        )
    p = params or {}
    eng = ClaudeCodeEngine.from_workspace(
        permission_context=_perm_ctx(p),
        tool_ctx=_tool_ctx(p),
        provider_name=p.get("provider"),
        model=p.get("model"),
    )
    if p.get("session_id"):
        eng.session_id = str(p["session_id"])
    results = await PortRuntime().run_turn_loop(
        str(prompt),
        limit=int(p.get("limit", 5)),
        max_turns=int(p.get("max_turns", 3)),
        engine=eng,
    )
    return {
        "session_id": eng.session_id,
        "turns": [
            {
                "output": r.output,
                "stop_reason": r.stop_reason,
                "usage": {
                    "input_tokens": r.usage.input_tokens,
                    "output_tokens": r.usage.output_tokens,
                },
                "tool_events": list(r.tool_events),
            }
            for r in results
        ],
    }


async def handle_claude_code_route(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = (params or {}).get("prompt", "")
    matches = PortRuntime().route_prompt(
        str(prompt), limit=int((params or {}).get("limit", 5))
    )
    return {
        "matches": [
            {
                "kind": m.kind,
                "name": m.name,
                "score": m.score,
                "source_hint": m.source_hint,
            }
            for m in matches
        ]
    }


async def handle_claude_code_tools_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    p = params or {}
    tools: list[Any] = list(
        tr.get_tools(
            simple_mode=bool(p.get("simple_mode", False)),
            include_mcp=not bool(p.get("no_mcp", False)),
            permission_context=_perm_ctx(p),
        )
    )
    q = p.get("query")
    if q:
        tools = tr.find_tools(str(q), limit=int(p.get("limit", 50)))
    else:
        tools = list(tools[: int(p.get("limit", 50))])
    return {
        "count": len(tr.PORTED_TOOLS),
        "items": [
            {
                "name": t.name,
                "source_hint": t.source_hint,
                "responsibility": t.responsibility,
            }
            for t in tools
        ],
        "index_text": tr.render_tool_index(
            int(p.get("limit", 20)), str(q) if q else None
        ),
    }


async def handle_claude_code_commands_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    p = params or {}
    cmds: list[Any] = list(
        cr.get_commands(
            include_plugin_commands=not p.get("no_plugin_commands", False),
            include_skill_commands=not p.get("no_skill_commands", False),
        )
    )
    if p.get("query"):
        cmds = cr.find_commands(str(p.get("query")), int(p.get("limit", 50)))
    else:
        cmds = list(cmds[: int(p.get("limit", 50))])
    return {
        "count": len(cr.PORTED_COMMANDS),
        "items": [
            {
                "name": c.name,
                "source_hint": c.source_hint,
                "responsibility": c.responsibility,
            }
            for c in cmds
        ],
    }


async def handle_claude_code_session_load(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    sid = (params or {}).get("session_id")
    if not sid:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing session_id")
    async with AsyncSessionLocal() as db:
        row = await load_session_db(str(sid), db)
    if row is None:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, f"Session not found: {sid}")
    return {
        "session_id": row.session_id,
        "messages": list(row.messages),
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
    }


async def handle_claude_code_session_flush(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    p = params or {}
    prompt = p.get("prompt", "")
    eng = ClaudeCodeEngine.from_workspace(
        permission_context=_perm_ctx(p),
        tool_ctx=_tool_ctx(p),
    )
    if p.get("session_id"):
        eng.session_id = str(p["session_id"])
    if prompt:
        rt = PortRuntime()
        m = rt.route_prompt(str(prompt), limit=int(p.get("limit", 5)))
        mc = tuple(x.name for x in m if x.kind == "command")
        mt = tuple(x.name for x in m if x.kind == "tool")
        await eng.submit_message(str(prompt), mc, mt, ())
    async with AsyncSessionLocal() as db:
        await eng.persist_session(db)
        await db.commit()
    return {
        "session_id": eng.session_id,
        "flushed": eng.transcript_store.flushed,
    }


async def handle_claude_code_manifest(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    m = build_port_manifest()
    return {"markdown": m.to_markdown()}


async def handle_claude_code_parity_audit(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    r = run_parity_audit()
    return {"markdown": r.to_markdown()}


def get_methods() -> Dict[str, Any]:
    return {
        "claude_code.run": handle_claude_code_run,
        "claude_code.bootstrap": handle_claude_code_bootstrap,
        "claude_code.turn_loop": handle_claude_code_turn_loop,
        "claude_code.route": handle_claude_code_route,
        "claude_code.tools.list": handle_claude_code_tools_list,
        "claude_code.commands.list": handle_claude_code_commands_list,
        "claude_code.session.load": handle_claude_code_session_load,
        "claude_code.session.flush": handle_claude_code_session_flush,
        "claude_code.manifest": handle_claude_code_manifest,
        "claude_code.parity_audit": handle_claude_code_parity_audit,
    }
