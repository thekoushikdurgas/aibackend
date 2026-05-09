"""
Claude Code engine: LLM + workspace tools (extends QueryEnginePort from reference).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

from app.config import settings
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMConfig, LLMResponse

from .commands_registry import _handle_slash
from .models import (
    PermissionDenial,
    QueryEngineConfig,
    ToolError,
    TurnResult,
    UsageSummary,
)
from .permissions import ToolPermissionContext
from .port_manifest import PortManifest, build_port_manifest
from .tool_executor import default_context, execute_tool_async, tool_spec_json
from .tool_executor import ToolExecutorContext
from .transcript import TranscriptStore

logger = logging.getLogger(__name__)


def _parse_agent_action(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    if "```" in t:
        m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", t)
        if m:
            try:
                d = json.loads(m.group(1))
                if isinstance(d, dict) and d.get("durgas_action"):
                    return d
            except json.JSONDecodeError:
                pass
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        try:
            d = json.loads(t[start : end + 1])
            if isinstance(d, dict) and d.get("durgas_action"):
                return d
        except json.JSONDecodeError:
            pass
    return {"durgas_action": "answer", "text": t}


def _usage_from_response(usage: UsageSummary, resp: LLMResponse) -> UsageSummary:
    if not resp.usage:
        return usage.add_turn("", resp.text or "")
    it = int(resp.usage.get("input_tokens") or resp.usage.get("prompt_tokens") or 0)
    ot = int(
        resp.usage.get("output_tokens") or resp.usage.get("completion_tokens") or 0
    )
    if it + ot == 0:
        return usage.add_turn("", resp.text or "")
    return UsageSummary(
        input_tokens=usage.input_tokens + it,
        output_tokens=usage.output_tokens + ot,
    )


class ClaudeCodeEngine:
    """Stateful agent engine with real workspace tools and LLM provider."""

    def __init__(
        self,
        manifest: PortManifest,
        config: Optional[QueryEngineConfig] = None,
        session_id: Optional[str] = None,
        permission_context: Optional[ToolPermissionContext] = None,
        tool_ctx: Optional[ToolExecutorContext] = None,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.35,
    ) -> None:
        self.manifest = manifest
        self.config = config or QueryEngineConfig()
        self.session_id = session_id or uuid4().hex
        self.permission_denials: List[PermissionDenial] = []
        self.total_usage = UsageSummary()
        self.transcript_store = TranscriptStore()
        self.mutable_messages: List[str] = []
        self.permission_context = permission_context or ToolPermissionContext()
        self.tool_ctx = tool_ctx or default_context()
        self.conversation: List[Dict[str, str]] = []
        self.provider_name = provider_name
        self.model = model
        self.temperature = temperature

    @classmethod
    def from_workspace(
        cls,
        permission_context: Optional[ToolPermissionContext] = None,
        tool_ctx: Optional[ToolExecutorContext] = None,
        **kwargs: Any,
    ) -> "ClaudeCodeEngine":
        return cls(
            manifest=build_port_manifest(),
            permission_context=permission_context,
            tool_ctx=tool_ctx,
            **kwargs,
        )

    @classmethod
    def from_stored(
        cls,
        messages: tuple[str, ...],
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        **kwargs: Any,
    ) -> "ClaudeCodeEngine":
        eng = cls(session_id=session_id, **kwargs)
        eng.mutable_messages = list(messages)
        eng.total_usage = UsageSummary(input_tokens, output_tokens)
        eng.transcript_store = TranscriptStore(entries=list(messages), flushed=True)
        return eng

    def _system_text(
        self,
        matched_commands: tuple[str, ...],
        matched_tools: tuple[str, ...],
    ) -> str:
        specs = tool_spec_json()
        return (
            "You are Claude Code (DurgasAI). "
            "Answer by emitting ONE JSON object (optionally in a ```json fence).\n"
            'Use {"durgas_action":"tool","name":"<name>","input":{...}} to run a workspace tool, or '
            '{"durgas_action":"answer","text":"..."} for the final reply.\n\n'
            f"Routing hints — commands: {list(matched_commands)}, mirrored tools: {list(matched_tools)}.\n"
            f"Workspace tools (executable): {json.dumps(specs, indent=2)[:8000]}"
        )

    async def _call_llm(
        self,
        system_prompt: str,
    ) -> LLMResponse:
        if not self.conversation or self.conversation[-1].get("role") != "user":
            raise RuntimeError("claude_code: last message must be user")
        user_msg = self.conversation[-1]["content"]
        hist = self.conversation[:-1]
        prov = get_llm_provider(self.provider_name)
        model = (
            self.model or getattr(prov, "default_model", None) or settings.default_model
        )
        cfg = LLMConfig(
            model=model,
            temperature=self.temperature,
            max_tokens=4096,
            system_prompt=system_prompt,
        )
        return await prov.generate(user_msg, cfg, conversation_history=hist)

    async def _run_tool_loop(
        self,
        prompt: str,
        matched_commands: tuple[str, ...],
        matched_tools: tuple[str, ...],
        denied_tools: tuple[PermissionDenial, ...],
    ) -> tuple[str, List[Dict[str, Any]]]:
        slash = _handle_slash(prompt)
        if slash:
            return slash.message, [{"type": "slash_command", "message": slash.message}]

        self.conversation.append({"role": "user", "content": prompt})
        self.mutable_messages.append(prompt)
        self.transcript_store.append(prompt)

        sys = self._system_text(matched_commands, matched_tools)
        tool_events: List[Dict[str, Any]] = []
        final_text = ""
        last_raw = ""

        for _ in range(self.config.max_tool_rounds):
            if len(self.mutable_messages) > self.config.max_turns:
                final_text = (
                    f"Max internal turns: stopped before completing.\n{last_raw}"
                )
                break

            resp = await self._call_llm(sys)
            last_raw = resp.text or ""
            self.total_usage = _usage_from_response(self.total_usage, resp)
            act = _parse_agent_action(last_raw)
            if act.get("durgas_action") == "tool":
                name = str(act.get("name") or "").strip()
                inp = act.get("input")
                if not isinstance(inp, dict):
                    inp = {}
                if self.permission_context.blocks(name):
                    tool_events.append(
                        {"type": "permission_denial", "name": name, "reason": "policy"}
                    )
                    self.conversation.append({"role": "assistant", "content": last_raw})
                    self.conversation.append(
                        {
                            "role": "user",
                            "content": f"Tool {name} was denied by permission policy. Answer without it or use another tool.",
                        }
                    )
                    continue
                if denied_tools and any(
                    d.tool_name.lower() == name.lower() for d in denied_tools
                ):
                    tool_events.append(
                        {
                            "type": "permission_denial",
                            "name": name,
                            "reason": "runtime_deferred",
                        }
                    )
                    self.conversation.append({"role": "assistant", "content": last_raw})
                    self.conversation.append(
                        {
                            "role": "user",
                            "content": f"Tool {name} not allowed in this run.",
                        }
                    )
                    continue
                try:
                    out = await execute_tool_async(name, inp, self.tool_ctx)
                except ToolError as e:
                    out = f"ToolError: {e.message}"
                tool_events.append(
                    {
                        "type": "tool_result",
                        "name": name,
                        "input": inp,
                        "output": out[:20_000],
                    }
                )
                self.conversation.append({"role": "assistant", "content": last_raw})
                self.conversation.append(
                    {
                        "role": "user",
                        "content": f"Result of {name}:\n{out}\n\nSummarize to the user or call another tool.",
                    }
                )
                continue

            final_text = str(act.get("text") or last_raw)
            self.conversation.append({"role": "assistant", "content": final_text})
            break
        else:
            final_text = last_raw or "(no output)"

        return final_text, tool_events

    async def submit_message(
        self,
        prompt: str,
        matched_commands: tuple[str, ...] = (),
        matched_tools: tuple[str, ...] = (),
        denied_tools: tuple[PermissionDenial, ...] = (),
    ) -> TurnResult:
        if len(self.mutable_messages) >= self.config.max_turns:
            return TurnResult(
                prompt=prompt,
                output=f"Max turns reached before processing prompt: {prompt}",
                matched_commands=matched_commands,
                matched_tools=matched_tools,
                permission_denials=denied_tools,
                usage=self.total_usage,
                stop_reason="max_turns_reached",
            )

        out, ev = await self._run_tool_loop(
            prompt, matched_commands, matched_tools, denied_tools
        )
        self.permission_denials.extend(denied_tools)
        self.compact_messages_if_needed()
        stop_reason = "completed"
        if (
            self.total_usage.input_tokens + self.total_usage.output_tokens
            > self.config.max_budget_tokens
        ):
            stop_reason = "max_budget_reached"
        return TurnResult(
            prompt=prompt,
            output=out,
            matched_commands=matched_commands,
            matched_tools=matched_tools,
            permission_denials=denied_tools,
            usage=self.total_usage,
            stop_reason=stop_reason,
            tool_events=tuple(ev),
        )

    async def stream_submit_message(
        self,
        prompt: str,
        matched_commands: tuple[str, ...] = (),
        matched_tools: tuple[str, ...] = (),
        denied_tools: tuple[PermissionDenial, ...] = (),
    ) -> AsyncIterator[Dict[str, Any]]:
        yield {
            "type": "message_start",
            "session_id": self.session_id,
            "prompt": prompt,
        }
        if matched_commands:
            yield {"type": "command_match", "commands": matched_commands}
        if matched_tools:
            yield {"type": "tool_match", "tools": matched_tools}
        if denied_tools:
            yield {
                "type": "permission_denial",
                "denials": [d.tool_name for d in denied_tools],
            }

        result = await self.submit_message(
            prompt, matched_commands, matched_tools, denied_tools
        )
        yield {"type": "message_delta", "text": result.output}
        for te in result.tool_events:
            yield te
        yield {
            "type": "message_stop",
            "usage": {
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
            },
            "stop_reason": result.stop_reason,
            "transcript_size": len(self.transcript_store.entries),
        }

    def compact_messages_if_needed(self) -> None:
        if len(self.mutable_messages) > self.config.compact_after_turns:
            self.mutable_messages[:] = self.mutable_messages[
                -self.config.compact_after_turns :
            ]
        self.transcript_store.compact(self.config.compact_after_turns)

    def replay_user_messages(self) -> tuple[str, ...]:
        return self.transcript_store.replay()

    def flush_transcript(self) -> None:
        self.transcript_store.flush()

    async def persist_session(self, db: Any) -> str:
        self.flush_transcript()
        from .models import StoredSession
        from .session_store import save_session

        st = StoredSession(
            session_id=self.session_id,
            messages=tuple(self.mutable_messages),
            input_tokens=self.total_usage.input_tokens,
            output_tokens=self.total_usage.output_tokens,
        )
        await save_session(st, db)
        return self.session_id

    def render_summary(self) -> str:
        from .commands_registry import build_command_backlog
        from .tools_registry import build_tool_backlog

        command_backlog = build_command_backlog()
        tool_backlog = build_tool_backlog()
        sections = [
            "# Claude Code Engine Summary",
            "",
            self.manifest.to_markdown(),
            "",
            f"Command surface: {len(command_backlog.modules)} mirrored entries",
            *command_backlog.summary_lines()[:10],
            "",
            f"Tool surface: {len(tool_backlog.modules)} mirrored entries",
            *tool_backlog.summary_lines()[:10],
            "",
            f"Session id: {self.session_id}",
            f"Conversation turns stored: {len(self.mutable_messages)}",
            f"Permission denials tracked: {len(self.permission_denials)}",
            f"Usage totals: in={self.total_usage.input_tokens} out={self.total_usage.output_tokens}",
            f"Max turns: {self.config.max_turns}",
            f"Max budget tokens: {self.config.max_budget_tokens}",
            f"Transcript flushed: {self.transcript_store.flushed}",
        ]
        return "\n".join(sections)
