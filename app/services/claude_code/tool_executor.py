"""
Real workspace tool executor (MVP set aligned with Rust mvp_tool_specs in claw-code rust port).
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List

import httpx

from app.config import settings

from .models import ToolError

# ---------------------------------------------------------------------------
# Public tool registry
# ---------------------------------------------------------------------------

TOOL_NAMES = frozenset(
    {
        "bash",
        "read_file",
        "write_file",
        "edit_file",
        "glob_search",
        "grep_search",
        "WebFetch",
        "web_fetch",
        "WebSearch",
        "web_search",
        "TodoWrite",
        "todo_write",
    }
)


@dataclass
class SessionTodos:
    items: List[Dict[str, Any]] = field(default_factory=list)

    def write(self, payload: str | Dict[str, Any]) -> str:
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                return f"Invalid JSON for todos: {payload[:200]}"
        else:
            data = payload
        todos = data.get("todos") or data.get("items") or []
        if isinstance(todos, list):
            self.items = [
                t if isinstance(t, dict) else {"content": str(t)} for t in todos
            ]
        return f"Updated todos ({len(self.items)} items)."


@dataclass
class ToolExecutorContext:
    """Per-session state for tools (e.g. todos)."""

    workspace_root: Path
    bash_read_only: bool
    bash_timeout: int
    max_file_bytes: int = 512_000
    todos: SessionTodos = field(default_factory=SessionTodos)


def _norm_name(name: str) -> str:
    n = (name or "").strip()
    mapping = {
        "web_fetch": "WebFetch",
        "web_search": "WebSearch",
        "todo_write": "TodoWrite",
    }
    return mapping.get(n.lower(), n)


def _safe_path(root: Path, rel: str) -> Path:
    if not rel or rel.strip() in (".", ""):
        return root
    p = (root / rel).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError as exc:
        raise ToolError(f"Path escapes workspace: {rel}") from exc
    return p


def _read_file_sync(path: Path, offset: int = 0, limit: int | None = None) -> str:
    if not path.is_file():
        raise ToolError(f"Not a file: {path}")
    raw = path.read_bytes()
    if len(raw) > settings.claude_code_max_file_bytes:
        raise ToolError("File too large; increase claude_code_max_file_bytes in config")
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    if offset:
        lines = lines[offset:]
    if limit is not None:
        lines = lines[:limit]
    return "".join(lines)


def _write_file_sync(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {path}"


def _edit_file_sync(path: Path, old: str, new: str) -> str:
    if not path.is_file():
        raise ToolError(f"Not a file: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if old not in text:
        raise ToolError("old_string not found in file")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"Replaced 1 occurrence in {path.name}"


def _glob_search(root: Path, pattern: str) -> str:
    matches: List[str] = []
    for p in root.rglob("*"):
        if p.is_file() and fnmatch(p.relative_to(root).as_posix(), pattern):
            matches.append(p.relative_to(root).as_posix())
            if len(matches) >= 200:
                break
    return "\n".join(sorted(matches)[:200]) or "(no matches)"


def _grep_search(
    root: Path, pattern: str, glob_pat: str = "*", max_hits: int = 200
) -> str:
    try:
        rx = re.compile(pattern)
    except re.error as e:
        raise ToolError(f"Invalid regex: {e}") from e
    lines_out: List[str] = []
    for path in root.rglob(glob_pat):
        if (
            not path.is_file()
            or path.stat().st_size > settings.claude_code_max_file_bytes
        ):
            continue
        try:
            data = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(data.splitlines(), 1):
            if rx.search(line):
                rel = path.relative_to(root)
                lines_out.append(f"{rel}:{i}:{line[:500]}")
                if len(lines_out) >= max_hits:
                    return "\n".join(lines_out)
    return "\n".join(lines_out) or "(no matches)"


_RO_BASH = frozenset(
    {
        "ls",
        "dir",
        "cat",
        "type",
        "head",
        "tail",
        "more",
        "find",
        "pwd",
        "cd",
        "echo",
        "where",
        "which",
        "git",
    }
)


def _bash_allowed(cmd: str) -> bool:
    if not settings.claude_code_bash_read_only:
        return True
    for bad in (";", "&&", "||", "|", ">", ">>", "<", "`", "$("):
        if bad in cmd:
            return False
    first = cmd.strip().split()[0].lower() if cmd.strip() else ""
    if first in {"/b/bash", "bash", "sh", "cmd", "powershell", "pwsh"}:
        return False
    base = first.replace("\\", "/").split("/")[-1]
    if "." in base:
        base = base.split(".")[0]
    return base in _RO_BASH or first.startswith("git")


def _run_bash(cwd: Path, command: str, timeout: int) -> str:
    if settings.claude_code_bash_read_only and not _bash_allowed(command):
        raise ToolError(
            "Command blocked in read-only bash mode (claude_code_bash_read_only=true)"
        )
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise ToolError(f"bash timeout after {timeout}s") from e
    out = (proc.stdout or "") + (proc.stderr or "")
    if len(out) > 50_000:
        return out[:50_000] + "\n...[truncated]"
    return out or f"(exit {proc.returncode})"


def _web_fetch_sync(url: str, max_chars: int = 32_000) -> str:
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ToolError("URL must be http(s)")
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        r = client.get(url, headers={"User-Agent": "DurgasAI-ClaudeCode/1.0"})
    text = r.text
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return f"Status {r.status_code}\n\n{text}"


async def _web_fetch(url: str, max_chars: int = 32_000) -> str:
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ToolError("URL must be http(s)")
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        r = await client.get(url, headers={"User-Agent": "DurgasAI-ClaudeCode/1.0"})
    text = r.text
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return f"Status {r.status_code}\n\n{text}"


def _web_search_sync(query: str) -> str:
    """DuckDuckGo HTML lite (best-effort, no API key)."""
    q = (query or "").strip()
    if not q:
        raise ToolError("empty search query")
    url = "https://html.duckduckgo.com/html/"
    with httpx.Client(follow_redirects=True, timeout=20.0) as client:
        r = client.post(
            url,
            data={"q": q},
            headers={"User-Agent": "DurgasAI-ClaudeCode/1.0"},
        )
    html = r.text
    links = re.findall(r'class="result__a"[^>]+href="([^"]+)"', html)
    snippets = re.findall(r'class="result__snippet"[^>]+>([^<]+)', html)
    lines = [f"Query: {q!r}", f"Status: {r.status_code}", ""]
    for i in range(min(10, max(len(links), len(snippets), 0))):
        h = links[i] if i < len(links) else ""
        s = snippets[i] if i < len(snippets) else ""
        lines.append(f"- {h}\n  {s.strip()}")
    if len(lines) <= 3:
        return f"Query: {q!r}\n(No result links parsed. Try a more specific query or use WebFetch.)\n"
    return "\n".join(lines)


async def _web_search(query: str) -> str:
    return await asyncio.to_thread(_web_search_sync, query)


def execute_tool(
    name: str,
    raw_input: str | Dict[str, Any],
    ctx: ToolExecutorContext,
) -> str:
    tool = _norm_name(name)
    payload: Dict[str, Any] = raw_input if isinstance(raw_input, dict) else {}
    if isinstance(raw_input, str) and raw_input.strip().startswith("{"):
        try:
            payload = json.loads(raw_input)
        except json.JSONDecodeError:
            payload = {"raw": raw_input}
    if isinstance(raw_input, str) and not payload:
        payload = {"value": raw_input}

    if tool in ("read_file",):
        p = _safe_path(
            ctx.workspace_root, payload.get("path") or payload.get("file", "")
        )
        return _read_file_sync(
            p,
            int(payload.get("offset") or 0),
            int(payload["limit"]) if payload.get("limit") is not None else None,
        )
    if tool in ("write_file",):
        p = _safe_path(
            ctx.workspace_root, payload.get("path") or payload.get("file", "")
        )
        content = str(payload.get("content") or "")
        return _write_file_sync(p, content)
    if tool in ("edit_file",):
        p = _safe_path(
            ctx.workspace_root, payload.get("path") or payload.get("file", "")
        )
        return _edit_file_sync(
            p,
            str(payload.get("old_string") or payload.get("old", "")),
            str(payload.get("new_string") or payload.get("new", "")),
        )
    if tool in ("bash",):
        cmd = str(payload.get("command") or payload.get("script") or raw_input)
        return _run_bash(
            ctx.workspace_root,
            cmd,
            int(payload.get("timeout") or settings.claude_code_bash_timeout_seconds),
        )
    if tool in ("glob_search",):
        pat = str(payload.get("pattern") or payload.get("glob", "**/*"))
        return _glob_search(ctx.workspace_root, pat)
    if tool in ("grep_search",):
        return _grep_search(
            ctx.workspace_root,
            str(payload.get("pattern") or payload.get("regex", ".*")),
            str(payload.get("glob") or "*"),
        )
    if tool in ("WebFetch",):
        return _web_fetch_sync(str(payload.get("url") or raw_input))
    if tool in ("WebSearch",):
        return _web_search_sync(str(payload.get("query") or raw_input))
    if tool in ("TodoWrite",):
        return ctx.todos.write(
            raw_input if isinstance(raw_input, (str, dict)) else json.dumps(payload)
        )

    raise ToolError(f"Unknown tool: {name}")


# Async variants for use inside async engine (no run_until_complete)
async def execute_tool_async(
    name: str,
    raw_input: str | Dict[str, Any],
    ctx: ToolExecutorContext,
) -> str:
    tool = _norm_name(name)
    if tool in ("WebFetch", "web_fetch"):
        payload: Dict[str, Any] = raw_input if isinstance(raw_input, dict) else {}
        if isinstance(raw_input, str) and raw_input.strip().startswith("{"):
            try:
                payload = json.loads(raw_input)
            except json.JSONDecodeError:
                pass
        url = str(payload.get("url") or raw_input)
        return await _web_fetch(url)
    if tool in ("WebSearch", "web_search"):
        payload = raw_input if isinstance(raw_input, dict) else {}
        if isinstance(raw_input, str) and raw_input.strip().startswith("{"):
            try:
                payload = json.loads(raw_input)
            except json.JSONDecodeError:
                pass
        return await _web_search(str(payload.get("query") or raw_input))
    return await asyncio.to_thread(execute_tool, name, raw_input, ctx)


def tool_spec_json() -> List[Dict[str, Any]]:
    return [
        {
            "name": "read_file",
            "description": "Read a file under the workspace (UTF-8).",
            "input": {"path": "string", "offset": "int?", "limit": "int?"},
        },
        {
            "name": "write_file",
            "description": "Write text to a file under the workspace.",
            "input": {"path": "string", "content": "string"},
        },
        {
            "name": "edit_file",
            "description": "Replace old_string with new_string once in a file.",
            "input": {"path": "string", "old_string": "string", "new_string": "string"},
        },
        {
            "name": "bash",
            "description": "Run a shell command in the workspace; read-only mode restricts dangerous patterns.",
            "input": {"command": "string"},
        },
        {
            "name": "glob_search",
            "description": "List files under workspace matching a glob (max 200).",
            "input": {"pattern": "string"},
        },
        {
            "name": "grep_search",
            "description": "Regex search across text files in workspace (max 200 hits).",
            "input": {"pattern": "string", "glob": "string?"},
        },
        {
            "name": "WebFetch",
            "description": "GET an HTTP/HTTPS URL and return body text (truncated).",
            "input": {"url": "string"},
        },
        {
            "name": "WebSearch",
            "description": "Web search (DuckDuckGo HTML, best effort).",
            "input": {"query": "string"},
        },
        {
            "name": "TodoWrite",
            "description": "Update session todo list (JSON: {todos: [...]}).",
            "input": {"todos": "array"},
        },
    ]


def default_context() -> ToolExecutorContext:
    root = settings.claude_code_workspace_root
    path = Path(root).resolve() if root else Path.cwd().resolve()
    return ToolExecutorContext(
        workspace_root=path,
        bash_read_only=settings.claude_code_bash_read_only,
        bash_timeout=settings.claude_code_bash_timeout_seconds,
        max_file_bytes=settings.claude_code_max_file_bytes,
    )
