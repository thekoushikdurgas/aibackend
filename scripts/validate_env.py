"""
Preflight check: ensure app settings load from environment / .env.
Run from repository root: python scripts/validate_env.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def main() -> int:
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        get_settings()
    except Exception as exc:
        print(f"validate_env: failed to load settings: {exc}", file=sys.stderr)
        return 1
    print("validate_env: OK - settings load successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
