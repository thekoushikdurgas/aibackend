@echo off
REM Bootstrap .env and start Docker Compose from ai.backend root.
REM Usage (from ai.backend):
REM   scripts\docker-up.bat
REM   scripts\docker-up.bat dev

setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"

if not exist ".env" (
  if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo Created .env from .env.example — edit secrets before production.
  ) else (
    echo WARNING: No .env.example found; create .env manually.
  )
)

if not exist "docker\supabase\supabase.env" (
  if exist "docker\supabase\supabase.env.example" (
    copy /y "docker\supabase\supabase.env.example" "docker\supabase\supabase.env" >nul
    echo Created docker\supabase\supabase.env from supabase.env.example — edit before docker compose.
  )
)

REM Compose interpolates ${VAR} from env files here — supabase.env supplies POSTGRES_*, JWT_SECRET, ANON_KEY, etc.
set "ENV_FILES=--env-file .env --env-file docker\supabase\supabase.env"

if /i "%~1"=="dev" (
  echo Starting development stack ^(compose.dev.yaml^)...
  docker compose %ENV_FILES% -f compose.dev.yaml up --build
) else (
  echo Starting production-style stack ^(compose.yaml^)...
  docker compose %ENV_FILES% -f compose.yaml up -d --build
)

endlocal
