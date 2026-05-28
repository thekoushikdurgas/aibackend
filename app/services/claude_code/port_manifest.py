"""
Port manifest — scan Python files under the Claude Code service package.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .models import Subsystem

DEFAULT_SRC_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PortManifest:
    src_root: Path
    total_python_files: int
    top_level_modules: tuple[Subsystem, ...]

    def to_markdown(self) -> str:
        lines = [
            f"Port root: `{self.src_root}`",
            f"Total Python files: **{self.total_python_files}**",
            "",
            "Top-level Python modules:",
        ]
        for module in self.top_level_modules:
            lines.append(
                f"- `{module.name}` ({module.file_count} files) — {module.notes}"
            )
        return "\n".join(lines)


def build_port_manifest(src_root: Path | None = None) -> PortManifest:
    root = src_root or DEFAULT_SRC_ROOT
    files = [path for path in root.rglob("*.py") if path.is_file()]
    counter: Counter[str] = Counter()
    for path in files:
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root)
        name = rel.parts[0] if len(rel.parts) > 1 else path.name
        counter[name] += 1
    notes = {
        "__init__.py": "package export surface",
        "models.py": "shared dataclasses",
        "query_engine.py": "Claude Code agent engine",
        "tool_executor.py": "real workspace tools",
    }
    modules = tuple(
        Subsystem(
            name=name,
            path=f"src/{name}",
            file_count=count,
            notes=notes.get(name, "claude_code support module"),
        )
        for name, count in counter.most_common()
    )
    return PortManifest(
        src_root=root, total_python_files=len(files), top_level_modules=modules
    )
