@echo off
REM Save as UTF-8 without BOM. A leading BOM makes CMD fail on the first line (mojibake before @echo).
REM Use setlocal EnableDelayedExpansion below. Wrong spelling breaks this script on Windows CMD.
setlocal EnableDelayedExpansion

REM ========================================
REM DURGASAI BACKEND (FASTAPI) - CODEBASE STATE CHECK
REM ========================================
REM Run from ai.backend: double-click or run codebase.bat from this directory.
REM
REM Pattern follows contact360.io API codebase.bat (10 steps + summary + optional dev server)
REM but uses Python tooling aligned with .github/workflows/api-ci.yml:
REM   0 Source inventory (reports\durgasai-source-inventory.txt)
REM   0b Optional Docker Compose hints
REM   1 pip install (requirements.txt + requirements-dev.txt)
REM   2 Environment validation (scripts\validate_env.py)
REM   3 mypy (typecheck) app/
REM   3b pyrefly check --summarize-errors (Meta static analysis)
REM   4 black --check
REM   4b Prettier via npm run format:check (matches CI)
REM   5 ruff check
REM   6 pytest tests/
REM   6b coverage if RUN_TEST_COVERAGE=1
REM   7 scripts\check_best_practices.py (.api-checker-config.json optional)
REM   8 black (final format write)
REM   9 pip check + import smoke (pip check skipped on Windows Python 3.13+ unless FORCE_PIP_CHECK=1)
REM
REM Optional environment variables:
REM SKIP_CSS_INVENTORY=1       Skip step 0 source inventory
REM SKIP_DOCKER_HINT=1         Skip step 0b Docker hints
REM SKIP_PIP_INSTALL=1         Skip step 1
REM SKIP_CODEGEN=1             Skip step 2 (validate_env.py)
REM ENV_VALIDATE_NO_FAIL=1     validate_env failures -> warning only (no ERROR_COUNT / no goto summary)
REM SKIP_MYPY=1                Skip step 3
REM MYPY_STRICT=1              mypy failure increments ERROR_COUNT (default: warning only)
REM SKIP_PYREFLY=1             Skip step 3b (pyrefly)
REM PYREFLY_NO_FAIL=1         pyrefly failure -> warning only (default: counts as error)
REM SKIP_FORMAT_CHECK=1        Skip step 4 black --check
REM SKIP_LINT=1                Skip step 5 ruff
REM SKIP_TESTS=1               Skip step 6
REM RUN_TEST_COVERAGE=1        Step 6b: pytest --cov=app (matches CI)
REM SKIP_BEST_PRACTICES=1      Skip step 7
REM BEST_PRACTICES_NO_FAIL=1   Pass --no-fail to check_best_practices.py
REM BEST_PRACTICES_THRESHOLD=N  --threshold (optional; script defaults to score-only + issues)
REM BEST_PRACTICES_FORMAT=text or json or both
REM SKIP_FINAL_FORMAT=1      Skip step 8 black write
REM SKIP_BUILD=1             Skip step 9 pip check / import smoke
REM SKIP_PIP_CHECK=1           Always skip pip check (but still run import smoke)
REM FORCE_PIP_CHECK=1          On Win/py3.13+, run pip check anyway
REM SKIP_PRETTIER=1            Skip step 4b Prettier
REM SKIP_DEV_SERVER=1          Do not prompt to start uvicorn (also: NO_PROMPT=1, or CI / GITHUB_ACTIONS)
REM ========================================

set "API_DIR=%~dp0"
set "ERROR_COUNT=0"
set "WARNING_COUNT=0"
set "START_TIME=%TIME%"
set "SECTION6_COVERAGE_STATUS=SKIPPED"

set "ESC="
for /f "delims=" %%A in ('powershell -NoProfile -Command "Write-Output ([char]27)" 2^>nul') do set "ESC=%%A"
set "GREEN=%ESC%[92m"
set "RED=%ESC%[91m"
set "YELLOW=%ESC%[93m"
set "BLUE=%ESC%[94m"
set "CYAN=%ESC%[96m"

goto :main

:color_echo
setlocal EnableDelayedExpansion
set "_ce_c=%~1"
set "_ce_t=x%~2"
set "_ce_t=!_ce_t:~1!"
echo !_ce_c!!_ce_t!
endlocal
goto :eof

:main
echo.
call :color_echo "%CYAN%" "========================================"
call :color_echo "%CYAN%" "  DURGASAI BACKEND (FASTAPI) STATE CHECK"
call :color_echo "%CYAN%" "========================================"
echo.

if not exist "%API_DIR%app\main.py" (
    call :color_echo "%RED%" "ERROR: app\main.py not found under: %API_DIR%"
    exit /b 1
)

cd /d "%API_DIR%"
call :color_echo "%BLUE%" "Current directory: %CD%"
set "PY_EXTRA="
set "PY=python"
if exist "venv\Scripts\python.exe" (
  set "PY=!CD!\venv\Scripts\python.exe"
  "!PY!" -c "import sys" 2>nul
  if not errorlevel 1 (
    call :color_echo "%BLUE%" "Using venv Python: !PY!"
    goto :py_ready
  )
  call :color_echo "%YELLOW%" "venv\Scripts\python.exe failed import check. Recreate: python -m venv venv"
)
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys" 2>nul
  if not errorlevel 1 (
    set "PY=py"
    set "PY_EXTRA=-3"
    call :color_echo "%BLUE%" "Using Python launcher: py -3"
    goto :py_ready
  )
)
set "PY=python"
set "PY_EXTRA="
call :color_echo "%YELLOW%" "No working venv Python; using PATH python"
:py_ready
echo.

set "SECTION0_STATUS=SKIPPED"
set "SECTION0B_STATUS=SKIPPED"
set "SECTION1_STATUS=SKIPPED"
set "SECTION2_STATUS=SKIPPED"
set "SECTION3_STATUS=SKIPPED"
set "SECTION_PYREFLY_STATUS=SKIPPED"
set "SECTION4_STATUS=SKIPPED"
set "SECTION5_STATUS=SKIPPED"
set "SECTION6_STATUS=SKIPPED"
set "SECTION7_STATUS=SKIPPED"
set "SECTION8_STATUS=SKIPPED"
set "SECTION9_STATUS=SKIPPED"
set "SECTION4P_STATUS=SKIPPED"

if /i "%SKIP_CSS_INVENTORY%"=="1" (
  call :color_echo "%YELLOW%" "[0] Source inventory skipped (SKIP_CSS_INVENTORY=1)"
  set "SECTION0_STATUS=SKIPPED"
  echo.
) else (
  call :color_echo "%CYAN%" "[0] Python source inventory (app / scripts / tests)..."
  echo ----------------------------------------
  if not exist "reports" mkdir reports
  call :color_echo "%BLUE%" "  Output: reports\durgasai-source-inventory.txt"
  (
    echo DURGASAI BACKEND - Python modules under app\, scripts\, tests\
    echo Generated: %DATE% %TIME%
    echo.
    echo === app ===
    dir /s /b app\*.py 2>nul
    echo.
    echo === scripts ===
    dir /s /b scripts\*.py 2>nul
    echo.
    echo === tests ===
    dir /s /b tests\*.py 2>nul
  ) > "reports\durgasai-source-inventory.txt" 2>&1
  call :color_echo "%GREEN%" "  OK Inventory written"
  set "SECTION0_STATUS=PASSED"
  echo.
)

if /i "%SKIP_DOCKER_HINT%"=="1" (
  set "SECTION0B_STATUS=SKIPPED"
) else (
  call :color_echo "%CYAN%" "[0b] Docker Compose (optional)"
  echo ----------------------------------------
  call :color_echo "%BLUE%" "  Copy .env.example to .env; set POSTGRES_PASSWORD, JWT_SECRET_KEY, API_KEY."
  call :color_echo "%BLUE%" "  Start: docker compose --env-file .env -f compose.yaml up -d --build"
  call :color_echo "%BLUE%" "  See docker\README.md and scripts\docker-up.bat"
  set "SECTION0B_STATUS=DONE"
  echo.
)

call :color_echo "%CYAN%" "[1/10] Dependencies (pip)..."
echo ----------------------------------------
if /i "%SKIP_PIP_INSTALL%"=="1" (
  call :color_echo "%YELLOW%" "  Skipped (SKIP_PIP_INSTALL=1)"
  set "SECTION1_STATUS=SKIPPED"
) else (
  call :color_echo "%YELLOW%" "  Running: !PY! !PY_EXTRA! -m pip install --upgrade pip"
  call "%PY%" %PY_EXTRA% -m pip install --upgrade pip
  if errorlevel 1 (
    set /a WARNING_COUNT+=1
    call :color_echo "%YELLOW%" "  ! pip upgrade warning"
  )
  call :color_echo "%YELLOW%" "  Running: !PY! !PY_EXTRA! -m pip install --no-warn-script-location -r requirements.txt -r requirements-dev.txt"
  call "%PY%" %PY_EXTRA% -m pip install --no-warn-script-location -r requirements.txt -r requirements-dev.txt
  if errorlevel 1 (
    set /a ERROR_COUNT+=1
    set "SECTION1_STATUS=FAILED"
    call :color_echo "%RED%" "  X pip install failed"
    call :color_echo "%BLUE%" "  Fix venv: remove venv folder, then: python -m venv venv"
    goto :summary
  ) else (
    set "SECTION1_STATUS=PASSED"
    call :color_echo "%GREEN%" "  OK Dependencies installed"
  )
)
echo.

call :color_echo "%CYAN%" "[2/10] Environment validation (preflight)..."
echo ----------------------------------------
if /i "%SKIP_CODEGEN%"=="1" (
  call :color_echo "%YELLOW%" "  Skipped (SKIP_CODEGEN=1)"
  set "SECTION2_STATUS=SKIPPED"
) else (
  if exist "scripts\validate_env.py" (
    call :color_echo "%BLUE%" "  Running: !PY! !PY_EXTRA! scripts\validate_env.py"
    call "%PY%" %PY_EXTRA% scripts\validate_env.py
    if errorlevel 1 (
      if /i "%ENV_VALIDATE_NO_FAIL%"=="1" (
        set /a WARNING_COUNT+=1
        set "SECTION2_STATUS=WARNING"
        call :color_echo "%YELLOW%" "  ! validate_env failed (ENV_VALIDATE_NO_FAIL=1)"
      ) else (
        set /a ERROR_COUNT+=1
        set "SECTION2_STATUS=FAILED"
        call :color_echo "%RED%" "  X validate_env failed — fix .env or use ENV_VALIDATE_NO_FAIL=1 / SKIP_CODEGEN=1"
        goto :summary
      )
    ) else (
      set "SECTION2_STATUS=PASSED"
      call :color_echo "%GREEN%" "  OK Environment validation passed"
    )
  ) else (
    set /a WARNING_COUNT+=1
    set "SECTION2_STATUS=WARNING"
    call :color_echo "%YELLOW%" "  ! scripts\validate_env.py not found"
  )
)
echo.

call :color_echo "%CYAN%" "[3/10] Type checking (mypy)..."
echo ----------------------------------------
if /i "%SKIP_MYPY%"=="1" (
  call :color_echo "%YELLOW%" "  Skipped (SKIP_MYPY=1)"
  set "SECTION3_STATUS=SKIPPED"
) else (
  call :color_echo "%YELLOW%" "  Running: !PY! !PY_EXTRA! -m mypy app/"
  call "%PY%" %PY_EXTRA% -m mypy app/
  if errorlevel 1 (
    if /i "%MYPY_STRICT%"=="1" (
      set /a ERROR_COUNT+=1
      set "SECTION3_STATUS=FAILED"
      call :color_echo "%RED%" "  X mypy failed (MYPY_STRICT=1)"
    ) else (
      set /a WARNING_COUNT+=1
      set "SECTION3_STATUS=WARNING"
      call :color_echo "%YELLOW%" "  ! mypy issues (warning only; set MYPY_STRICT=1 to fail)"
    )
  ) else (
    set "SECTION3_STATUS=PASSED"
    call :color_echo "%GREEN%" "  OK mypy passed"
  )
)
echo.

call :color_echo "%CYAN%" "[3b/10] Pyrefly (static analysis)..."
echo ----------------------------------------
if /i "%SKIP_PYREFLY%"=="1" (
  call :color_echo "%YELLOW%" "  Skipped (SKIP_PYREFLY=1)"
  set "SECTION_PYREFLY_STATUS=SKIPPED"
) else (
  call :color_echo "%BLUE%" "  Checking for pyrefly module..."
  call "%PY%" %PY_EXTRA% -c "import pyrefly" 2>nul
  if errorlevel 1 (
    set /a WARNING_COUNT+=1
    set "SECTION_PYREFLY_STATUS=WARNING"
    call :color_echo "%YELLOW%" "  ! pyrefly not installed — pip install pyrefly (or set SKIP_PYREFLY=1)"
  ) else (
    call :color_echo "%YELLOW%" "  Running: !PY! !PY_EXTRA! -m pyrefly check app/ --summarize-errors"
    call "%PY%" %PY_EXTRA% -m pyrefly check app/ --summarize-errors
    if errorlevel 1 (
      if /i "%PYREFLY_NO_FAIL%"=="1" (
        set /a WARNING_COUNT+=1
        set "SECTION_PYREFLY_STATUS=WARNING"
        call :color_echo "%YELLOW%" "  ! pyrefly reported issues (PYREFLY_NO_FAIL=1)"
      ) else (
        set /a ERROR_COUNT+=1
        set "SECTION_PYREFLY_STATUS=FAILED"
        call :color_echo "%RED%" "  X pyrefly check failed — fix errors or set PYREFLY_NO_FAIL=1 for warning-only"
      )
    ) else (
      set "SECTION_PYREFLY_STATUS=PASSED"
      call :color_echo "%GREEN%" "  OK pyrefly passed"
    )
  )
)
echo.

call :color_echo "%CYAN%" "[4/10] Formatting checks (black)..."
echo ----------------------------------------
if /i "%SKIP_FORMAT_CHECK%"=="1" (
  call :color_echo "%YELLOW%" "  Skipped (SKIP_FORMAT_CHECK=1)"
  set "SECTION4_STATUS=SKIPPED"
) else (
  call :color_echo "%YELLOW%" "  Running: !PY! !PY_EXTRA! -m black --check app scripts tests docs\tests"
  call "%PY%" %PY_EXTRA% -m black --check app scripts tests docs\tests
  if errorlevel 1 (
    set /a ERROR_COUNT+=1
    set "SECTION4_STATUS=FAILED"
    call :color_echo "%RED%" "  X black --check failed - run: black"
  ) else (
    set "SECTION4_STATUS=PASSED"
    call :color_echo "%GREEN%" "  OK black check passed"
  )
)
echo.

call :color_echo "%CYAN%" "[4b/10] Prettier (Markdown, JSON, YAML)..."
echo ----------------------------------------
if /i "%SKIP_PRETTIER%"=="1" (
  call :color_echo "%YELLOW%" "  Skipped (SKIP_PRETTIER=1)"
  set "SECTION4P_STATUS=SKIPPED"
) else (
  if not exist "package.json" (
    set /a WARNING_COUNT+=1
    set "SECTION4P_STATUS=WARNING"
    call :color_echo "%YELLOW%" "  ! package.json not found — set SKIP_PRETTIER=1 or add npm metadata"
  ) else (
    where npm >nul 2>&1
    if errorlevel 1 (
      set /a WARNING_COUNT+=1
      set "SECTION4P_STATUS=WARNING"
      call :color_echo "%YELLOW%" "  ! npm not on PATH — install Node.js or set SKIP_PRETTIER=1"
    ) else (
      call :color_echo "%BLUE%" "  Running: npm ci (or npm install) then npm run format:check"
      if exist "package-lock.json" (
        call npm ci
      ) else (
        call npm install
      )
      if errorlevel 1 (
        set /a WARNING_COUNT+=1
        set "SECTION4P_STATUS=WARNING"
        call :color_echo "%YELLOW%" "  ! npm install failed"
      ) else (
        call npm run format:check
        if errorlevel 1 (
          set /a WARNING_COUNT+=1
          set "SECTION4P_STATUS=WARNING"
          call :color_echo "%YELLOW%" "  ! format:check failed — run: npm run format"
        ) else (
          set "SECTION4P_STATUS=PASSED"
          call :color_echo "%GREEN%" "  OK Prettier check passed"
        )
      )
    )
  )
)
echo.

call :color_echo "%CYAN%" "[5/10] Linting (ruff)..."
echo ----------------------------------------
if /i "%SKIP_LINT%"=="1" (
  call :color_echo "%YELLOW%" "  Skipped (SKIP_LINT=1)"
  set "SECTION5_STATUS=SKIPPED"
) else (
  call :color_echo "%YELLOW%" "  Running: !PY! !PY_EXTRA! -m ruff check"
  call "%PY%" %PY_EXTRA% -m ruff check
  if errorlevel 1 (
    set /a ERROR_COUNT+=1
    set "SECTION5_STATUS=FAILED"
    call :color_echo "%RED%" "  X ruff check failed"
  ) else (
    set "SECTION5_STATUS=PASSED"
    call :color_echo "%GREEN%" "  OK ruff passed"
  )
)
echo.

call :color_echo "%CYAN%" "[6/10] Running tests (pytest)..."
echo ----------------------------------------
if /i "%SKIP_TESTS%"=="1" (
  call :color_echo "%YELLOW%" "  Skipped (SKIP_TESTS=1)"
  set "SECTION6_STATUS=SKIPPED"
) else (
  set "PREV_ENV=%ENVIRONMENT%"
  set ENVIRONMENT=test
  call :color_echo "%BLUE%" "  ENVIRONMENT=test"
  call :color_echo "%YELLOW%" "  Running: !PY! !PY_EXTRA! -m pytest tests/"
  call "%PY%" %PY_EXTRA% -m pytest tests/
  if errorlevel 1 (
    set /a ERROR_COUNT+=1
    set "SECTION6_STATUS=FAILED"
    call :color_echo "%RED%" "  X Tests failed"
  ) else (
    set "SECTION6_STATUS=PASSED"
    call :color_echo "%GREEN%" "  OK Tests passed"
  )
  if defined PREV_ENV (set "ENVIRONMENT=%PREV_ENV%") else (set "ENVIRONMENT=")
)
echo.

if /i "%RUN_TEST_COVERAGE%"=="1" (
  if /i "%SKIP_TESTS%"=="1" (
    call :color_echo "%YELLOW%" "[6b] Coverage skipped (SKIP_TESTS=1)"
  ) else (
    call :color_echo "%CYAN%" "[6b] Pytest coverage (RUN_TEST_COVERAGE=1)..."
    echo ----------------------------------------
    set ENVIRONMENT=test
    call :color_echo "%YELLOW%" "  Running: pytest tests/ --cov=app --cov-report=term-missing"
    call "%PY%" %PY_EXTRA% -m pytest tests/ --cov=app --cov-report=term-missing
    if errorlevel 1 (
      set /a WARNING_COUNT+=1
      set "SECTION6_COVERAGE_STATUS=WARNING"
      call :color_echo "%YELLOW%" "  Warning: coverage run failed"
    ) else (
      set "SECTION6_COVERAGE_STATUS=PASSED"
      call :color_echo "%GREEN%" "  OK Coverage run completed"
    )
    if defined PREV_ENV (set "ENVIRONMENT=%PREV_ENV%") else (set "ENVIRONMENT=")
  )
  echo.
) else (
  call :color_echo "%BLUE%" "[6b] Coverage skipped (set RUN_TEST_COVERAGE=1 for pytest --cov=app)"
  echo.
)

if /i "%SKIP_BEST_PRACTICES%"=="1" (
  call :color_echo "%YELLOW%" "[7/10] Best practices skipped (SKIP_BEST_PRACTICES=1)"
  set "SECTION7_STATUS=SKIPPED"
  echo.
) else (
  call :color_echo "%CYAN%" "[7/10] API best-practices checklist..."
  echo ----------------------------------------
  call :color_echo "%BLUE%" "  Output: reports\check_report_bat.json"
  if exist "scripts\check_best_practices.py" (
    set "BP_FMT=both"
    if /i "!BEST_PRACTICES_FORMAT!"=="text" set "BP_FMT=text"
    if /i "!BEST_PRACTICES_FORMAT!"=="json" set "BP_FMT=json"
    if /i "!BEST_PRACTICES_FORMAT!"=="both" set "BP_FMT=both"
    if /i "%BEST_PRACTICES_NO_FAIL%"=="1" (
      if not "!BEST_PRACTICES_THRESHOLD!"=="" (
        call "%PY%" %PY_EXTRA% scripts\check_best_practices.py --output reports\check_report_bat.json --format !BP_FMT! --threshold !BEST_PRACTICES_THRESHOLD! --no-fail
      ) else (
        call "%PY%" %PY_EXTRA% scripts\check_best_practices.py --output reports\check_report_bat.json --format !BP_FMT! --no-fail
      )
      set "SECTION7_STATUS=PASSED"
      call :color_echo "%GREEN%" "  OK Best-practices report written (--no-fail)"
    ) else (
      if not "!BEST_PRACTICES_THRESHOLD!"=="" (
        call "%PY%" %PY_EXTRA% scripts\check_best_practices.py --output reports\check_report_bat.json --format !BP_FMT! --threshold !BEST_PRACTICES_THRESHOLD!
      ) else (
        call "%PY%" %PY_EXTRA% scripts\check_best_practices.py --output reports\check_report_bat.json --format !BP_FMT!
      )
      if errorlevel 1 (
        set /a ERROR_COUNT+=1
        set "SECTION7_STATUS=FAILED"
        call :color_echo "%RED%" "  X Best-practices check failed"
      ) else (
        set "SECTION7_STATUS=PASSED"
        call :color_echo "%GREEN%" "  OK Best-practices check passed"
      )
    )
  ) else (
    set /a WARNING_COUNT+=1
    set "SECTION7_STATUS=WARNING"
    call :color_echo "%YELLOW%" "  ! scripts\check_best_practices.py not found"
  )
  echo.
)

if /i "%SKIP_FINAL_FORMAT%"=="1" (
  call :color_echo "%YELLOW%" "[8/10] Final format skipped (SKIP_FINAL_FORMAT=1)"
  set "SECTION8_STATUS=SKIPPED"
  echo.
) else (
  call :color_echo "%CYAN%" "[8/10] Final format (black)..."
  echo ----------------------------------------
  call :color_echo "%YELLOW%" "  Running: !PY! !PY_EXTRA! -m black app scripts tests docs\tests"
  call "%PY%" %PY_EXTRA% -m black app scripts tests docs\tests
  if errorlevel 1 (
    set /a WARNING_COUNT+=1
    set "SECTION8_STATUS=WARNING"
    call :color_echo "%YELLOW%" "  ! black apply had issues"
  ) else (
    set "SECTION8_STATUS=PASSED"
    call :color_echo "%GREEN%" "  OK black formatting applied"
    if /i "!SECTION4_STATUS!"=="FAILED" (
      set "SECTION4_STATUS=FIXED"
      set /a ERROR_COUNT-=1
    )
  )
  echo.
)

call :color_echo "%CYAN%" "[9/10] Install / import integrity..."
echo ----------------------------------------
if /i "%SKIP_BUILD%"=="1" (
  call :color_echo "%YELLOW%" "  Skipped (SKIP_BUILD=1)"
  set "SECTION9_STATUS=SKIPPED"
) else (
  set "DO_PIP_CHECK=1"
  if /i "%SKIP_PIP_CHECK%"=="1" set "DO_PIP_CHECK=0"
  if /i "%FORCE_PIP_CHECK%"=="1" set "DO_PIP_CHECK=1"
  if "!DO_PIP_CHECK!"=="1" (
    "%PY%" %PY_EXTRA% -c "import sys; raise SystemExit(0 if (sys.platform=='win32' and sys.version_info>=(3,13)) else 1)" 2>nul
    if not errorlevel 1 (
      if /i not "%FORCE_PIP_CHECK%"=="1" (
        set "DO_PIP_CHECK=0"
        call :color_echo "%BLUE%" "  Skipping pip check (Windows Python 3.13+; set FORCE_PIP_CHECK=1 to run)"
      )
    )
  )
  if "!DO_PIP_CHECK!"=="1" (
    call :color_echo "%YELLOW%" "  Running: !PY! !PY_EXTRA! -m pip check"
    call "%PY%" %PY_EXTRA% -m pip check
    if errorlevel 1 (
      set /a WARNING_COUNT+=1
      set "SECTION9_STATUS=WARNING"
      call :color_echo "%YELLOW%" "  ! pip check reported conflicts"
    ) else (
      call :color_echo "%GREEN%" "  OK pip check"
    )
  ) else (
    if /i "%SKIP_PIP_CHECK%"=="1" (
      call :color_echo "%BLUE%" "  pip check skipped (SKIP_PIP_CHECK=1)"
    )
  )
  call :color_echo "%BLUE%" "  Import smoke: from app.main import app"
  call "%PY%" %PY_EXTRA% -c "from app.main import app"
  if errorlevel 1 (
    set /a ERROR_COUNT+=1
    set "SECTION9_STATUS=FAILED"
    call :color_echo "%RED%" "  X Failed to import app.main"
  ) else (
    if not "!SECTION9_STATUS!"=="WARNING" set "SECTION9_STATUS=PASSED"
    call :color_echo "%GREEN%" "  OK app.main import succeeded"
  )
)
echo.

:summary
echo.
call :color_echo "%CYAN%" "========================================"
call :color_echo "%CYAN%" "  SUMMARY"
call :color_echo "%CYAN%" "========================================"
echo.
call :color_echo "%BLUE%" "Section Status:"
echo   [0] Source inventory:              !SECTION0_STATUS!
echo   [0b] Docker hint:                   !SECTION0B_STATUS!
echo   [1] Pip dependencies:              !SECTION1_STATUS!
echo   [2] Environment validate:          !SECTION2_STATUS!
echo   [3] mypy:                          !SECTION3_STATUS!
echo   [3b] pyrefly:                      !SECTION_PYREFLY_STATUS!
echo   [4] black --check:                 !SECTION4_STATUS!
echo   [4b] Prettier:                     !SECTION4P_STATUS!
echo   [5] ruff check:                    !SECTION5_STATUS!
echo   [6] pytest:                        !SECTION6_STATUS!
echo   [6b] pytest coverage:              !SECTION6_COVERAGE_STATUS!
echo   [7] Best practices:               !SECTION7_STATUS!
echo   [8] black (apply):                 !SECTION8_STATUS!
echo   [9] pip check + import app:        !SECTION9_STATUS!
echo.

if %ERROR_COUNT% EQU 0 (
    call :color_echo "%GREEN%" "  OK All blocking checks passed!"
    if %WARNING_COUNT% GTR 0 call :color_echo "%YELLOW%" "  Found %WARNING_COUNT% warning(s)"
    echo.
    if /i "%SKIP_DEV_SERVER%"=="1" goto :after_prompt
    if /i "%NO_PROMPT%"=="1" goto :after_prompt
    if defined CI goto :after_prompt
    if defined GITHUB_ACTIONS goto :after_prompt
    call :color_echo "%CYAN%" "  Start API server? (Y/N)"
    choice /C YN /N /M ""
    if errorlevel 2 goto :after_prompt
    if errorlevel 1 goto :dev_server
    goto :after_prompt
) else (
    call :color_echo "%RED%" "  X Found %ERROR_COUNT% error(s)"
    if %WARNING_COUNT% GTR 0 call :color_echo "%YELLOW%" "  Found %WARNING_COUNT% warning(s)"
    echo.
    call :color_echo "%YELLOW%" "  Please fix the errors before proceeding."
)
goto :after_prompt

:dev_server
echo.
call :color_echo "%CYAN%" "[10/10] Starting uvicorn (reload)..."
call :color_echo "%BLUE%" "  !PY! !PY_EXTRA! -m uvicorn app.main:app --reload"
call :color_echo "%BLUE%" "  Press Ctrl+C to stop"
echo.
call "%PY%" %PY_EXTRA% -m uvicorn app.main:app --reload

:after_prompt
echo.
call :color_echo "%CYAN%" "========================================"
call :color_echo "%CYAN%" "  CHECK COMPLETE"
call :color_echo "%CYAN%" "========================================"
echo.
if %ERROR_COUNT% GTR 0 (exit /b 1) else (exit /b 0)
