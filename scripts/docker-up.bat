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

REM Empty supabase.env breaks Compose interpolation (warnings + supabase-db unhealthy). Same logic as docker-up.sh / remote-deploy.sh.
set "SUPABASE_ENV_OK="
if exist "docker\supabase\supabase.env" for %%I in ("docker\supabase\supabase.env") do if not %%~zI==0 set "SUPABASE_ENV_OK=1"
if not defined SUPABASE_ENV_OK if exist "docker\supabase\supabase.env.example" (
  if not exist "docker\supabase" mkdir "docker\supabase"
  copy /y "docker\supabase\supabase.env.example" "docker\supabase\supabase.env" >nul
  echo Created docker\supabase\supabase.env from supabase.env.example — edit secrets before docker compose.
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
