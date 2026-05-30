"""
Preflight: ensure app settings load from environment / .env.

Run from ai.backend root, for example:
  python scripts/validate_env.py
  python scripts/validate_env.py -v
  python scripts/validate_env.py --docker
  python scripts/validate_env.py --strict
  python scripts/validate_env.py --import-app

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


def _read_dotenv_lines(path: Path) -> tuple[list[str], str | None]:
    """Read .env lines; return (lines, error_message) on permission or I/O failure."""
    if not path.is_file():
        return [], None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except PermissionError:
        return [], (
            f"permission denied reading {path}. "
            "Do not use sudo on .env — fix: sudo chown $USER:$USER .env && chmod 600 .env"
        )
    except OSError as exc:
        return [], f"cannot read {path}: {exc}"
    return text.splitlines(), None


def _dotenv_keys(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE parse (no multiline values). Used for Compose-only vars."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    lines, err = _read_dotenv_lines(path)
    if err:
        raise PermissionError(err)
    for raw in lines:
        line = raw.strip()
        # Bracketed-paste corruption from SSH/nano (e.g. [200~# header)
        if re.match(r"^\[\d+~", line):
            line = re.sub(r"^\[\d+~", "", line).lstrip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        out[key] = val
    return out


_PUBLISH_HOST_KEYS = (
    "POSTGRES_PUBLISH_HOST",
    "REDIS_PUBLISH_HOST",
    "OLLAMA_PUBLISH_HOST",
    "CHROMA_PUBLISH_HOST",
)


def _dotenv_corruption_issues(path: Path) -> list[str]:
    """Detect terminal paste artifacts that break Docker Compose env-file parsing."""
    issues: list[str] = []
    if not path.is_file():
        return issues
    lines, err = _read_dotenv_lines(path)
    if err:
        issues.append(err)
        return issues
    for raw in lines:
        if re.match(r"^\[\d+~", raw.strip()):
            issues.append(
                ".env contains bracketed-paste junk (e.g. [200~ at line start). "
                "Re-create .env: cp .env.example .env && nano, or paste without bracketed mode."
            )
            break
    return issues


def _docker_publish_host_issues(env_keys: dict[str, str]) -> list[str]:
    """Reject binding Docker ports to a public IP (common EC2 mistake)."""
    issues: list[str] = []
    allowed = {"127.0.0.1", "0.0.0.0", "localhost", ""}
    for key in _PUBLISH_HOST_KEYS:
        val = (env_keys.get(key) or "").strip()
        if not val or val in allowed:
            continue
        if val.startswith("54.") or val.count(".") == 3:
            issues.append(
                f"{key}={val!r} — do not use a public EC2 IP for Docker port bind. "
                "Production compose does not publish db/redis/ollama/chroma ports; "
                "remove this line or set 127.0.0.1 only for local dev overrides."
            )
        elif val not in allowed:
            issues.append(
                f"{key}={val!r} — use 127.0.0.1 or 0.0.0.0 if you need host ports "
                "(production stack uses internal network only)."
            )
    return issues


def _docker_preflight(env_keys: dict[str, str], *, production: bool) -> list[str]:
    """Warnings for docker compose (see docker/docker-compose.yml)."""
    issues: list[str] = []
    issues.extend(_docker_publish_host_issues(env_keys))
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


def _strict_preflight_from_keys(env_keys: dict[str, str]) -> list[str]:
    """Production checks using raw .env keys (no pydantic import)."""
    issues: list[str] = []
    env = (env_keys.get("ENVIRONMENT") or env_keys.get("environment") or "").strip()
    if env.lower() != "production":
        return issues

    jwt = (env_keys.get("JWT_SECRET_KEY") or "").strip()
    api = (env_keys.get("API_KEY") or "").strip()

    if not jwt or len(jwt) < 32:
        issues.append(
            "production: JWT_SECRET_KEY must be set and at least 32 characters."
        )
    elif (
        "change-in-production" in jwt.lower()
        or jwt == "your-super-secret-jwt-key-change-in-production"
    ):
        issues.append(
            "production: JWT_SECRET_KEY still looks like a development placeholder."
        )

    if not api or api == "your-api-key-for-extension":
        issues.append("production: API_KEY must be set to a non-default value.")
    elif "generate_a_random" in api.lower():
        issues.append(
            "production: API_KEY still looks like a template from .env.example."
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
        issues.append(
            "production: JWT_SECRET_KEY must be set and at least 32 characters."
        )
    elif (
        "change-in-production" in jwt.lower()
        or jwt == "your-super-secret-jwt-key-change-in-production"
    ):
        issues.append(
            "production: JWT_SECRET_KEY still looks like a development placeholder."
        )

    if not api or api == "your-api-key-for-extension":
        issues.append("production: API_KEY must be set to a non-default value.")
    elif "generate_a_random" in api.lower():
        issues.append(
            "production: API_KEY still looks like a template from .env.example."
        )

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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print non-secret resolved paths and URLs.",
    )
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
    parser.add_argument(
        "--dotenv-only",
        action="store_true",
        help="Parse .env only (no app imports). Use on EC2 host before Docker build.",
    )
    parser.add_argument(
        "--import-app",
        action="store_true",
        help="Import app.main after settings load (catches missing pip deps before uvicorn).",
    )
    args = parser.parse_args(argv)

    if args.dotenv_only:
        if not _DOTENV.is_file():
            print(f"validate_env: .env not found at {_DOTENV}", file=sys.stderr)
            return 1
        _, read_err = _read_dotenv_lines(_DOTENV)
        if read_err:
            print(f"validate_env: {read_err}", file=sys.stderr)
            return 1
        try:
            keys = _dotenv_keys(_DOTENV)
        except PermissionError as exc:
            print(f"validate_env: {exc}", file=sys.stderr)
            return 1
        production = (keys.get("ENVIRONMENT") or "").lower() == "production"
        for msg in _dotenv_corruption_issues(_DOTENV):
            print(f"validate_env: {msg}", file=sys.stderr)
            return 1
        if args.docker:
            for msg in _docker_preflight(keys, production=production):
                print(f"validate_env: warning: {msg}", file=sys.stderr)
            publish_bad = _docker_publish_host_issues(keys)
            for msg in publish_bad:
                print(f"validate_env: {msg}", file=sys.stderr)
            if publish_bad and production:
                return 1
        if args.strict:
            bad = _strict_preflight_from_keys(keys)
            for msg in bad:
                print(f"validate_env: {msg}", file=sys.stderr)
            if bad:
                return 1
        print("validate_env: OK - .env preflight (dotenv-only)")
        return 0

    try:
        from app.config import clear_base_settings_cache, _base_settings_singleton
    except ModuleNotFoundError as exc:
        name = getattr(exc, "name", None) or str(exc)
        print(
            "validate_env: missing dependency module "
            f"'{name}'. Install the project first, e.g.\n"
            "  python3 -m venv venv && ./venv/bin/pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    clear_base_settings_cache()
    try:
        # Read fresh pydantic Settings from env (not the runtime proxy used by the API).
        settings = _base_settings_singleton()
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
        try:
            keys = _dotenv_keys(_DOTENV)
        except PermissionError as exc:
            print(f"validate_env: {exc}", file=sys.stderr)
            return 1
        for msg in _docker_preflight(keys, production=settings.is_production):
            print(f"validate_env: warning: {msg}", file=sys.stderr)
        publish_bad = _docker_publish_host_issues(keys)
        for msg in publish_bad:
            print(f"validate_env: {msg}", file=sys.stderr)
        if publish_bad and settings.is_production:
            return 1

    if args.import_app:
        try:
            import app.main  # noqa: F401
        except ModuleNotFoundError as exc:
            name = getattr(exc, "name", None) or str(exc)
            hint = "Add it to requirements.txt and rebuild the Docker image."
            if name == "jwt":
                hint = "Add PyJWT to requirements.txt (provides `import jwt`), then rebuild."
            print(
                f"validate_env: app.main import failed — missing module '{name}'. {hint}",
                file=sys.stderr,
            )
            return 1
        except Exception as exc:
            print(f"validate_env: app.main import failed: {exc}", file=sys.stderr)
            return 1

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
