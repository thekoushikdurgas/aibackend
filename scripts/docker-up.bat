@echo off
REM Bootstrap .env and start Docker Compose from ai.backend root.
REM
REM Usage (from ai.backend):
REM   scripts\docker-up.bat
REM   scripts\docker-up.bat dev
REM
REM Environment:
REM   SKIP_VALIDATE_ENV=1  — skip python scripts\validate_env.py before compose.
REM
REM compose.yaml uses Docker Compose v2.20+ (include:). Upgrade Compose if include: errors.

setlocal EnableExtensions

where docker >nul 2>&1
if errorlevel 1 (
  echo ERROR: docker not found on PATH. Install Docker Desktop or Docker Engine.
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo ERROR: docker compose is not available. Install the Docker Compose v2 plugin.
  exit /b 1
)

set "ROOT=%~dp0.."
cd /d "%ROOT%"

docker buildx version >nul 2>&1
if errorlevel 1 set "DOCKER_BUILDKIT=0"

if not exist ".env" (
  if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo Created .env from .env.example — edit JWT_SECRET_KEY, API_KEY, POSTGRES_PASSWORD before production.
  ) else (
    echo WARNING: No .env.example found; create .env manually.
  )
)

if /i not "%SKIP_VALIDATE_ENV%"=="1" (
  where python >nul 2>&1
  if not errorlevel 1 (
    python scripts\validate_env.py --docker 1>&2
    python scripts\validate_env.py
    if errorlevel 1 (
      echo ERROR: validate_env.py failed — fix .env or set SKIP_VALIDATE_ENV=1.
      exit /b 1
    )
  )
)

set "ENV_FILES=--env-file .env"

if /i "%~1"=="dev" (
  echo Starting development stack ^(compose.dev.yaml^)...
  docker compose %ENV_FILES% -f compose.dev.yaml up --build
) else (
  echo Starting production-style stack ^(compose.yaml^)...
  docker compose %ENV_FILES% -f compose.yaml up -d --build
)

if errorlevel 1 (
  echo ERROR: docker compose exited with a non-zero status.
  exit /b 1
)

echo Tip: curl -fsS http://localhost:8000/health

endlocal
