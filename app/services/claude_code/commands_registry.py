"""
Mirrored command inventory + slash helpers (ported from claw-code-parity-main).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .models import PortingBacklog, PortingModule
from .tools_registry import render_tool_index

SNAPSHOT_PATH = (
    Path(__file__).resolve().parent / "reference_data" / "commands_snapshot.json"
)


@dataclass(frozen=True)
class CommandExecution:
    name: str
    source_hint: str
    prompt: str
    handled: bool
    message: str


@lru_cache(maxsize=1)
def load_command_snapshot() -> tuple[PortingModule, ...]:
    raw_entries = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    return tuple(
        PortingModule(
            name=entry["name"],
            responsibility=entry["responsibility"],
            source_hint=entry["source_hint"],
            status="mirrored",
        )
        for entry in raw_entries
    )


PORTED_COMMANDS = load_command_snapshot()


@lru_cache(maxsize=1)
def built_in_command_names() -> frozenset[str]:
    return frozenset(m.name for m in PORTED_COMMANDS)


def build_command_backlog() -> PortingBacklog:
    return PortingBacklog(title="Command surface", modules=list(PORTED_COMMANDS))


def command_names() -> list[str]:
    return [m.name for m in PORTED_COMMANDS]


def get_command(name: str) -> PortingModule | None:
    needle = name.lower()
    for module in PORTED_COMMANDS:
        if module.name.lower() == needle:
            return module
    return None


def get_commands(
    cwd: str | None = None,
    include_plugin_commands: bool = True,
    include_skill_commands: bool = True,
) -> tuple[PortingModule, ...]:
    commands = list(PORTED_COMMANDS)
    if not include_plugin_commands:
        commands = [m for m in commands if "plugin" not in m.source_hint.lower()]
    if not include_skill_commands:
        commands = [m for m in commands if "skills" not in m.source_hint.lower()]
    return tuple(commands)


def find_commands(query: str, limit: int = 20) -> list[PortingModule]:
    needle = query.lower()
    return [
        m
        for m in PORTED_COMMANDS
        if needle in m.name.lower() or needle in m.source_hint.lower()
    ][:limit]


def _handle_slash(prompt: str) -> CommandExecution | None:
    p = (prompt or "").strip()
    if not p.startswith("/"):
        return None
    first = p.split()[0].lower().lstrip("/")
    rest = p[len(p.split()[0]) :].strip()
    if first in ("help", "?"):
        return CommandExecution(
            name="help",
            source_hint="slash",
            prompt=p,
            handled=True,
            message=(
                "DurgasAI Claude Code slash:\n"
                "  /help /session /git /clear /tools /permissions\n"
                f"  Mirrored command entries: {len(PORTED_COMMANDS)}"
            ),
        )
    if first == "session":
        return CommandExecution(
            name="session",
            source_hint="slash",
            prompt=p,
            handled=True,
            message="Session: use WebSocket claude_code.session.* methods to load/flush; "
            "engine keeps transcript in memory between turns.",
        )
    if first == "git":
        return CommandExecution(
            name="git",
            source_hint="slash",
            prompt=p,
            handled=True,
            message="Git: run via bash tool, e.g. `git status` (subject to read-only mode).",
        )
    if first == "clear":
        return CommandExecution(
            name="clear",
            source_hint="slash",
            prompt=p,
            handled=True,
            message="clear: start a new session by omitting session_id on next claude_code.run or "
            "call session.load with a new id.",
        )
    if first == "tools":
        idx = render_tool_index(limit=30, query=rest or None)
        return CommandExecution(
            name="tools",
            source_hint="slash",
            prompt=p,
            handled=True,
            message=idx,
        )
    if first == "permissions":
        return CommandExecution(
            name="permissions",
            source_hint="slash",
            prompt=p,
            handled=True,
            message="Set deny_tool and deny_prefix on claude_code.run params; see ToolPermissionContext.",
        )
    return None


def execute_command(name: str, prompt: str = "") -> CommandExecution:
    if prompt and prompt.strip().startswith("/"):
        slash = _handle_slash(prompt)
        if slash:
            return slash
    module = get_command(name)
    if module is None:
        return CommandExecution(
            name=name,
            source_hint="",
            prompt=prompt,
            handled=False,
            message=f"Unknown mirrored command: {name}",
        )
    action = f"Mirrored command '{module.name}' from {module.source_hint} would handle prompt {prompt!r}."
    return CommandExecution(
        name=module.name,
        source_hint=module.source_hint,
        prompt=prompt,
        handled=True,
        message=action,
    )


def render_command_index(limit: int = 20, query: str | None = None) -> str:
    modules = find_commands(query, limit) if query else list(PORTED_COMMANDS[:limit])
    lines = [f"Command entries: {len(PORTED_COMMANDS)}", ""]
    if query:
        lines.append(f"Filtered by: {query}")
        lines.append("")
    lines.extend(f"- {m.name} — {m.source_hint}" for m in modules)
    return "\n".join(lines)
