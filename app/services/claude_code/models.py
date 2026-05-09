"""
Data models ported from claw-code-parity-main (Python porting workspace).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class Subsystem:
    name: str
    path: str
    file_count: int
    notes: str


@dataclass(frozen=True)
class PortingModule:
    name: str
    responsibility: str
    source_hint: str
    status: str = "planned"


@dataclass(frozen=True)
class PermissionDenial:
    tool_name: str
    reason: str


@dataclass(frozen=True)
class UsageSummary:
    input_tokens: int = 0
    output_tokens: int = 0

    def add_turn(self, prompt: str, output: str) -> "UsageSummary":
        return UsageSummary(
            input_tokens=self.input_tokens + len(prompt.split()),
            output_tokens=self.output_tokens + len(output.split()),
        )


@dataclass
class PortingBacklog:
    title: str
    modules: List[PortingModule] = field(default_factory=list)

    def summary_lines(self) -> List[str]:
        return [
            f"- {module.name} [{module.status}] — {module.responsibility} (from {module.source_hint})"
            for module in self.modules
        ]


@dataclass(frozen=True)
class StoredSession:
    session_id: str
    messages: Tuple[str, ...]
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class TurnResult:
    prompt: str
    output: str
    matched_commands: Tuple[str, ...]
    matched_tools: Tuple[str, ...]
    permission_denials: Tuple[PermissionDenial, ...]
    usage: UsageSummary
    stop_reason: str
    tool_events: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RoutedMatch:
    kind: str
    name: str
    source_hint: str
    score: int


@dataclass(frozen=True)
class QueryEngineConfig:
    max_turns: int = 8
    max_budget_tokens: int = 2000
    compact_after_turns: int = 12
    structured_output: bool = False
    structured_retry_limit: int = 2
    max_tool_rounds: int = 8


@dataclass
class RuntimeSession:
    prompt: str
    context_markdown: str
    setup_markdown: str
    system_init_message: str
    history_markdown: str
    routed_matches: List[RoutedMatch]
    turn_result: TurnResult
    command_execution_messages: Tuple[str, ...]
    tool_execution_messages: Tuple[str, ...]
    stream_events: Tuple[Dict[str, Any], ...]
    persisted_session_path: str

    def as_markdown(self) -> str:
        lines = [
            "# Runtime Session",
            "",
            f"Prompt: {self.prompt}",
            "",
            "## Context",
            self.context_markdown,
            "",
            "## Setup",
            self.setup_markdown,
            "",
            "## System Init",
            self.system_init_message,
            "",
            "## Routed Matches",
        ]
        if self.routed_matches:
            lines.extend(
                f"- [{m.kind}] {m.name} ({m.score}) — {m.source_hint}"
                for m in self.routed_matches
            )
        else:
            lines.append("- none")
        lines.extend(
            [
                "",
                "## Command Execution",
                *(self.command_execution_messages or ("none",)),
                "",
                "## Tool Execution",
                *(self.tool_execution_messages or ("none",)),
                "",
                "## Stream Events",
                *(f"- {e.get('type')}: {e}" for e in self.stream_events),
                "",
                "## Turn Result",
                self.turn_result.output,
                "",
                f"Persisted session path: {self.persisted_session_path}",
                "",
                self.history_markdown,
            ]
        )
        return "\n".join(lines)


class ToolError(Exception):
    """Raised when a workspace tool fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
