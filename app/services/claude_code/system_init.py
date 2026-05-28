"""System init message (ported from reference, adapted)."""

from __future__ import annotations

from .commands_registry import built_in_command_names, get_commands
from .tool_executor import tool_spec_json
from .tools_registry import get_tools
from .workspace_setup import run_setup


def build_system_init_message(trusted: bool = True) -> str:
    setup = run_setup(trusted=trusted)
    commands = get_commands()
    tools = get_tools()
    specs = tool_spec_json()
    lines = [
        "# System Init",
        "",
        f"Trusted: {setup.trusted}",
        f"Built-in command names: {len(built_in_command_names())}",
        f"Loaded command entries: {len(commands)}",
        f"Loaded tool entries: {len(tools)}",
        f"Executable workspace tools: {len(specs)}",
        "",
        "Startup steps:",
        *(f"- {step}" for step in setup.setup.startup_steps()),
    ]
    return "\n".join(lines)
