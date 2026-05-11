@echo off
REM Bootstrap .env and start Docker Compose from ai.backend root.
REM Usage (from ai.backend):
REM   scripts\docker-up.bat
REM   scripts\docker-up.bat dev

setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"

docker buildx version >nul 2>&1
if errorlevel 1 set "DOCKER_BUILDKIT=0"

if not exist ".env" (
  if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo Created .env from .env.example — edit secrets before production.
  ) else (
    echo WARNING: No .env.example found; create .env manually.
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

endlocal
