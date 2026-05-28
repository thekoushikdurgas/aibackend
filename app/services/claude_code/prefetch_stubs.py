"""Minimal prefetch stubs for setup report."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrefetchResult:
    name: str
    detail: str


def start_project_scan() -> PrefetchResult:
    return PrefetchResult(
        name="project_scan", detail="skipped in DurgasAI backend port"
    )
