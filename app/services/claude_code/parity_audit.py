"""
Parity audit vs optional local TypeScript archive (ported from reference).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ARCHIVE_ROOT = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "archive"
    / "claude_code_ts_snapshot"
    / "src"
)
CURRENT_ROOT = Path(__file__).resolve().parent
REFERENCE_SURFACE_PATH = (
    CURRENT_ROOT / "reference_data" / "archive_surface_snapshot.json"
)


def _json_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


COMMAND_SNAPSHOT_PATH = CURRENT_ROOT / "reference_data" / "commands_snapshot.json"
TOOL_SNAPSHOT_PATH = CURRENT_ROOT / "reference_data" / "tools_snapshot.json"

ARCHIVE_ROOT_FILES = {
    "QueryEngine.ts": "query_engine.py",
    "Task.ts": "task.py",
    "Tool.ts": "Tool.py",
    "commands.ts": "commands.py",
    "context.ts": "context.py",
    "cost-tracker.ts": "cost_tracker.py",
    "costHook.py": "costHook.py",
    "dialogLaunchers.tsx": "dialogLaunchers.py",
    "history.ts": "history.py",
    "ink.py": "ink.py",
    "interactiveHelpers.tsx": "interactiveHelpers.py",
    "main.tsx": "main.py",
    "projectOnboardingState.py": "projectOnboardingState.py",
    "query.py": "query.py",
    "replLauncher.tsx": "replLauncher.py",
    "setup.py": "setup.py",
    "tasks.py": "tasks.py",
    "tools.py": "tools.py",
}

ARCHIVE_DIR_MAPPINGS = {
    "assistant": "assistant",
    "bootstrap": "bootstrap",
    "bridge": "bridge",
    "buddy": "buddy",
    "cli": "cli",
    "commands": "commands.py",
    "components": "components",
    "coordinator": "coordinator",
    "hooks": "hooks",
    "plugins": "plugins",
    "schemas": "schemas",
    "skills": "skills",
    "tools": "tools.py",
}


@dataclass(frozen=True)
class ParityAuditResult:
    archive_present: bool
    root_file_coverage: tuple[int, int]
    directory_coverage: tuple[int, int]
    total_file_ratio: tuple[int, int]
    command_entry_ratio: tuple[int, int]
    tool_entry_ratio: tuple[int, int]
    missing_root_targets: tuple[str, ...]
    missing_directory_targets: tuple[str, ...]

    def to_markdown(self) -> str:
        lines: list[str] = ["# Parity Audit (Claude Code service)"]
        if not self.archive_present:
            lines.append(
                "Local archive unavailable; parity audit cannot compare against the original snapshot."
            )
            return "\n".join(lines)

        lines.extend(
            [
                "",
                f"Root file coverage: **{self.root_file_coverage[0]}/{self.root_file_coverage[1]}**",
                f"Directory coverage: **{self.directory_coverage[0]}/{self.directory_coverage[1]}**",
                f"Total Python files vs archived TS-like files: **{self.total_file_ratio[0]}/{self.total_file_ratio[1]}**",
                f"Command entry coverage: **{self.command_entry_ratio[0]}/{self.command_entry_ratio[1]}**",
                f"Tool entry coverage: **{self.tool_entry_ratio[0]}/{self.tool_entry_ratio[1]}**",
                "",
                "Missing root targets:",
            ]
        )
        if self.missing_root_targets:
            lines.extend(f"- {item}" for item in self.missing_root_targets)
        else:
            lines.append("- none")

        lines.extend(["", "Missing directory targets:"])
        if self.missing_directory_targets:
            lines.extend(f"- {item}" for item in self.missing_directory_targets)
        else:
            lines.append("- none")
        return "\n".join(lines)


def _reference_surface() -> dict[str, object]:
    if not REFERENCE_SURFACE_PATH.is_file():
        return {
            "total_ts_like_files": 0,
            "command_entry_count": 0,
            "tool_entry_count": 0,
        }
    return json.loads(REFERENCE_SURFACE_PATH.read_text(encoding="utf-8"))


def _snapshot_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return len(json.loads(path.read_text(encoding="utf-8")))


def run_parity_audit() -> ParityAuditResult:
    current_entries = {
        path.name for path in CURRENT_ROOT.iterdir() if path.is_dir() or path.is_file()
    }
    root_hits = [
        target for target in ARCHIVE_ROOT_FILES.values() if target in current_entries
    ]
    dir_hits = [
        target for target in ARCHIVE_DIR_MAPPINGS.values() if target in current_entries
    ]
    missing_roots = tuple(
        t for t in ARCHIVE_ROOT_FILES.values() if t not in current_entries
    )
    missing_dirs = tuple(
        t for t in set(ARCHIVE_DIR_MAPPINGS.values()) if t not in current_entries
    )
    current_python_files = sum(
        1 for path in CURRENT_ROOT.rglob("*.py") if path.is_file()
    )
    reference = _reference_surface()
    return ParityAuditResult(
        archive_present=ARCHIVE_ROOT.exists(),
        root_file_coverage=(len(root_hits), len(ARCHIVE_ROOT_FILES)),
        directory_coverage=(len(dir_hits), len(ARCHIVE_DIR_MAPPINGS)),
        total_file_ratio=(
            current_python_files,
            _json_int(reference.get("total_ts_like_files"), 0),
        ),
        command_entry_ratio=(
            _snapshot_count(COMMAND_SNAPSHOT_PATH),
            _json_int(reference.get("command_entry_count"), 0) or 1,
        ),
        tool_entry_ratio=(
            _snapshot_count(TOOL_SNAPSHOT_PATH),
            _json_int(reference.get("tool_entry_count"), 0) or 1,
        ),
        missing_root_targets=missing_roots,
        missing_directory_targets=missing_dirs,
    )
