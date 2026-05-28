"""
PortRuntime — token routing, bootstrap, turn loop (ported from reference, async engine).
"""

from __future__ import annotations


from .commands_registry import PORTED_COMMANDS
from .context import build_port_context, render_context
from .execution_registry import build_execution_registry
from .history import HistoryLog
from .models import (
    PermissionDenial,
    PortingModule,
    QueryEngineConfig,
    RuntimeSession,
    RoutedMatch,
    TurnResult,
)
from .query_engine import ClaudeCodeEngine
from .system_init import build_system_init_message
from .tools_registry import PORTED_TOOLS


class PortRuntime:
    def route_prompt(self, prompt: str, limit: int = 5) -> list[RoutedMatch]:
        tokens = {
            t.lower() for t in prompt.replace("/", " ").replace("-", " ").split() if t
        }
        by_kind = {
            "command": self._collect_matches(tokens, PORTED_COMMANDS, "command"),
            "tool": self._collect_matches(tokens, PORTED_TOOLS, "tool"),
        }
        selected: list[RoutedMatch] = []
        for kind in ("command", "tool"):
            if by_kind[kind]:
                selected.append(by_kind[kind].pop(0))
        leftovers = sorted(
            [m for matches in by_kind.values() for m in matches],
            key=lambda item: (-item.score, item.kind, item.name),
        )
        selected.extend(leftovers[: max(0, limit - len(selected))])
        return selected[:limit]

    @staticmethod
    def _collect_matches(
        tokens: set[str], modules: tuple[PortingModule, ...], kind: str
    ) -> list[RoutedMatch]:
        matches: list[RoutedMatch] = []
        for module in modules:
            score = PortRuntime._score(tokens, module)
            if score > 0:
                matches.append(
                    RoutedMatch(
                        kind=kind,
                        name=module.name,
                        source_hint=module.source_hint,
                        score=score,
                    )
                )
        matches.sort(key=lambda item: (-item.score, item.name))
        return matches

    @staticmethod
    def _score(tokens: set[str], module: PortingModule) -> int:
        haystacks = [
            module.name.lower(),
            module.source_hint.lower(),
            module.responsibility.lower(),
        ]
        return sum(1 for t in tokens if any(t in h for h in haystacks))

    def _infer_permission_denials(
        self, matches: list[RoutedMatch]
    ) -> list[PermissionDenial]:
        out: list[PermissionDenial] = []
        for m in matches:
            if m.kind == "tool" and "bash" in m.name.lower():
                out.append(
                    PermissionDenial(
                        tool_name=m.name,
                        reason="destructive shell execution may be gated (mirrored name match)",
                    )
                )
        return out

    async def bootstrap_session(
        self,
        prompt: str,
        limit: int = 5,
        engine: ClaudeCodeEngine | None = None,
    ) -> RuntimeSession:
        ctx = build_port_context()
        eng = engine or ClaudeCodeEngine.from_workspace()
        history = HistoryLog()
        history.add(
            "context",
            f"python_files={ctx.python_file_count}, archive={ctx.archive_available}",
        )
        history.add(
            "registry", f"commands={len(PORTED_COMMANDS)}, tools={len(PORTED_TOOLS)}"
        )
        matches = self.route_prompt(prompt, limit=limit)
        registry = build_execution_registry()
        command_execs: list[str] = []
        for m in matches:
            if m.kind == "command":
                c = registry.command(m.name)
                if c:
                    command_execs.append(c.execute(prompt))
        tool_execs: list[str] = []
        for m in matches:
            if m.kind == "tool":
                t = registry.tool(m.name)
                if t:
                    tool_execs.append(t.execute(prompt))
        denials = tuple(self._infer_permission_denials(matches))
        mc = tuple(x.name for x in matches if x.kind == "command")
        mt = tuple(x.name for x in matches if x.kind == "tool")
        turn_result = await eng.submit_message(
            prompt,
            matched_commands=mc,
            matched_tools=mt,
            denied_tools=denials,
        )
        stream_events: list[dict] = [
            {"type": "message_start", "session_id": eng.session_id, "prompt": prompt},
        ]
        if turn_result.tool_events:
            for te in turn_result.tool_events:
                stream_events.append(te)
        stream_events.append({"type": "message_delta", "text": turn_result.output})
        stream_events.append(
            {
                "type": "message_stop",
                "usage": {
                    "input_tokens": turn_result.usage.input_tokens,
                    "output_tokens": turn_result.usage.output_tokens,
                },
                "stop_reason": turn_result.stop_reason,
            }
        )
        from .workspace_setup import run_setup

        setup_report = run_setup(trusted=True)
        return RuntimeSession(
            prompt=prompt,
            context_markdown=render_context(ctx),
            setup_markdown=setup_report.as_markdown(),
            system_init_message=build_system_init_message(trusted=True),
            history_markdown=history.as_markdown(),
            routed_matches=matches,
            turn_result=turn_result,
            command_execution_messages=tuple(command_execs),
            tool_execution_messages=tuple(tool_execs),
            stream_events=tuple(stream_events),
            persisted_session_path=eng.session_id,
        )

    async def run_turn_loop(
        self,
        prompt: str,
        limit: int = 5,
        max_turns: int = 3,
        engine: ClaudeCodeEngine | None = None,
    ) -> list[TurnResult]:
        eng = engine or ClaudeCodeEngine.from_workspace()
        eng.config = QueryEngineConfig(
            max_turns=max_turns * 2,
            compact_after_turns=eng.config.compact_after_turns,
        )
        matches = self.route_prompt(prompt, limit=limit)
        command_names = tuple(m.name for m in matches if m.kind == "command")
        tool_names = tuple(m.name for m in matches if m.kind == "tool")
        results: list[TurnResult] = []
        for turn in range(max_turns):
            turn_prompt = prompt if turn == 0 else f"{prompt} [turn {turn + 1}]"
            result = await eng.submit_message(
                turn_prompt, command_names, tool_names, ()
            )
            results.append(result)
            if result.stop_reason != "completed":
                break
        return results
