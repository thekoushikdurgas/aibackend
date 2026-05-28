"""Deferred init stub."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeferredInitResult:
    applied: bool
    note: str


def run_deferred_init(trusted: bool) -> DeferredInitResult:
    return DeferredInitResult(applied=trusted, note="deferred init noop in DurgasAI")
