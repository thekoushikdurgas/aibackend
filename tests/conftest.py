"""Shared pytest configuration for ai.backend tests."""

from __future__ import annotations

import os

# Must run before test modules import app.main (settings reads ENVIRONMENT at import).
os.environ.setdefault("ENVIRONMENT", "test")
