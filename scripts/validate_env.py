"""
Preflight: ensure app settings load from environment / .env.

Run from ai.backend root, for example:
  python scripts/validate_env.py
  python scripts/validate_env.py -v
  python scripts/validate_env.py --docker
  python scripts/validate_env.py --strict

Run with --help for option descriptions.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_DOTENV = _BACKEND / ".env"

if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _mask_database_url(url: str) -> str:
    """Hide credentials in SQLAlchemy-style URLs for logs."""
    if not url:
        return ""
    # postgresql+asyncpg://user:password@host:port/db
    m = re.match(r"^((?:[\w+]+)://[^:]+:)([^@]+)(@.+)$", url)
    if m:
        return f"{m.group(1)}***{m.group(3)}"
    return url


def _dotenv_keys(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE parse (no multiline values). Used for Compose-only vars."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        out[key] = val
    return out


def _docker_preflight(env_keys: dict[str, str], *, production: bool) -> list[str]:
    """Warnings for docker compose (see docker/docker-compose.yml)."""
    issues: list[str] = []
    pwd = (env_keys.get("POSTGRES_PASSWORD") or "").strip()
    if not pwd:
        issues.append(
            "POSTGRES_PASSWORD is missing or empty in .env — "
            "Postgres in docker/docker-compose.yml will use the default 'postgres'."
        )
    elif production and pwd == "postgres":
        issues.append(
            "POSTGRES_PASSWORD is still 'postgres' while ENVIRONMENT=production — "
            "set a strong password in .env for the db service."
        )
    return issues


def _strict_preflight(settings: object) -> list[str]:
    """Block obviously unsafe production configuration."""
    issues: list[str] = []
    env = getattr(settings, "environment", "") or ""
    if str(env).lower() != "production":
        return issues

    jwt = (getattr(settings, "jwt_secret_key", "") or "").strip()
    api = (getattr(settings, "api_key", "") or "").strip()

    if not jwt or len(jwt) < 32:
        issues.append("production: JWT_SECRET_KEY must be set and at least 32 characters.")
    elif "change-in-production" in jwt.lower() or jwt == "your-super-secret-jwt-key-change-in-production":
        issues.append("production: JWT_SECRET_KEY still looks like a development placeholder.")

    if not api or api == "your-api-key-for-extension":
        issues.append("production: API_KEY must be set to a non-default value.")
    elif "generate_a_random" in api.lower():
        issues.append("production: API_KEY still looks like a template from .env.example.")

    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate ai.backend environment / settings load.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Compose-only variables (e.g. POSTGRES_PASSWORD) are not pydantic Settings fields; "
            "use --docker to lint them from .env. Root compose.yaml needs Docker Compose v2.20+ (include:)."
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Print non-secret resolved paths and URLs.")
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Check .env for Docker Compose variables (e.g. POSTGRES_PASSWORD).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="In ENVIRONMENT=production, reject placeholder JWT / API keys.",
    )
    args = parser.parse_args(argv)

    from app.config import get_settings

    get_settings.cache_clear()
    try:
        settings = get_settings()
    except Exception as exc:
        print(f"validate_env: failed to load settings: {exc}", file=sys.stderr)
        return 1

    if args.strict:
        bad = _strict_preflight(settings)
        for msg in bad:
            print(f"validate_env: {msg}", file=sys.stderr)
        if bad:
            return 1

    if args.docker:
        keys = _dotenv_keys(_DOTENV)
        for msg in _docker_preflight(keys, production=settings.is_production):
            print(f"validate_env: warning: {msg}", file=sys.stderr)

    if args.verbose:
        db = getattr(settings, "database_url", "")
        print(f"  environment: {getattr(settings, 'environment', '')}")
        print(f"  database_url: {_mask_database_url(str(db))}")
        print(f"  storage_root: {getattr(settings, 'storage_root', '')}")
        print(f"  storage_url_prefix: {getattr(settings, 'storage_url_prefix', '')}")
        print(f"  socketio_mount_path: {getattr(settings, 'socketio_mount_path', '')}")
        print(f"  chroma_persist_dir: {getattr(settings, 'chroma_persist_dir', '')}")
        print(f"  use_redis: {getattr(settings, 'use_redis', '')}")

    print("validate_env: OK - settings load successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
