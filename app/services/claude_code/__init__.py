"""
Claude Code agent harness (port of claw-code-parity-main) for DurgasAI backend.
"""

from .models import (
    QueryEngineConfig,
    RuntimeSession,
    StoredSession,
    ToolError,
    TurnResult,
)
from .parity_audit import ParityAuditResult, run_parity_audit
from .port_manifest import PortManifest, build_port_manifest
from .query_engine import ClaudeCodeEngine
from .runtime import PortRuntime
from .tool_executor import (
    TOOL_NAMES,
    ToolExecutorContext,
    default_context,
    execute_tool,
    execute_tool_async,
    tool_spec_json,
)

__all__ = [
    "ClaudeCodeEngine",
    "PortRuntime",
    "RuntimeSession",
    "TurnResult",
    "StoredSession",
    "QueryEngineConfig",
    "PortManifest",
    "build_port_manifest",
    "ToolError",
    "TOOL_NAMES",
    "ToolExecutorContext",
    "default_context",
    "execute_tool",
    "execute_tool_async",
    "tool_spec_json",
    "run_parity_audit",
    "ParityAuditResult",
]
