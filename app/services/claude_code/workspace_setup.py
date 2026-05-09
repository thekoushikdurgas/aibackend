"""Workspace setup / startup report (adapted from claw-code-parity-main)."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from pathlib import Path

from .deferred_init_stubs import DeferredInitResult, run_deferred_init
from .prefetch_stubs import start_project_scan


@dataclass(frozen=True)
class WorkspaceSetup:
    python_version: str
    implementation: str
    platform_name: str
    test_command: str = "python -m pytest ai.backend/tests -q --tb=no"

    def startup_steps(self) -> tuple[str, ...]:
        return (
            "load mirrored command snapshot",
            "load mirrored tool snapshot",
            "prepare Claude Code engine",
            "apply trust-gated deferred init",
        )


@dataclass(frozen=True)
class SetupReport:
    setup: WorkspaceSetup
    prefetches: tuple[object, ...]
    deferred_init: DeferredInitResult
    trusted: bool
    cwd: Path

    def as_markdown(self) -> str:
        lines = [
            "# Setup Report",
            "",
            f"- Python: {self.setup.python_version} ({self.setup.implementation})",
            f"- Platform: {self.setup.platform_name}",
            f"- Trusted mode: {self.trusted}",
            f"- CWD: {self.cwd}",
            "",
        ]
        return "\n".join(lines)


def run_setup(trusted: bool = True) -> SetupReport:
    return SetupReport(
        setup=WorkspaceSetup(
            python_version=sys.version.split()[0],
            implementation=platform.python_implementation(),
            platform_name=platform.platform(),
        ),
        prefetches=(start_project_scan(),),
        deferred_init=run_deferred_init(trusted),
        trusted=trusted,
        cwd=Path.cwd(),
    )
