#!/usr/bin/env bash
# DURGASAI BACKEND (FASTAPI) — codebase state check (Linux/macOS).
# Run from ai.backend: ./codebase.sh
#
# Mirrors contact360.io API codebase.bat / this repo codebase.bat, aligned with
# .github/workflows/api-ci.yml (ruff, black, mypy, Prettier, pytest).
#
# Steps:
#   0  Source inventory → reports/durgasai-source-inventory.txt
#   0b Docker Compose hints (optional)
#   1  pip install -r requirements.txt -r requirements-dev.txt
#   2  scripts/validate_env.py
#   3  mypy app/
#   4  black --check app/ scripts/ tests/
#   4b npm run format:check
#   5  ruff check app/ scripts/ tests/
#   6  pytest tests/
#   6b pytest --cov=app if RUN_TEST_COVERAGE=1
#   7  scripts/check_best_practices.py
#   8  black app/ scripts/ tests/
#   9  pip check + import app.main (pip check skipped on win32 Python 3.13+ unless FORCE_PIP_CHECK=1)
#
# Optional env (same semantics as codebase.bat):
#   SKIP_CSS_INVENTORY SKIP_DOCKER_HINT SKIP_PIP_INSTALL SKIP_CODEGEN ENV_VALIDATE_NO_FAIL
#   SKIP_MYPY MYPY_STRICT SKIP_FORMAT_CHECK SKIP_LINT SKIP_TESTS RUN_TEST_COVERAGE
#   SKIP_BEST_PRACTICES BEST_PRACTICES_NO_FAIL BEST_PRACTICES_THRESHOLD BEST_PRACTICES_FORMAT
#   SKIP_FINAL_FORMAT SKIP_BUILD SKIP_PIP_CHECK FORCE_PIP_CHECK SKIP_PRETTIER
#   SKIP_DEV_SERVER NO_PROMPT  (also non-interactive if CI or GITHUB_ACTIONS is set)
#   SKIP_PIP_INSTALL=1  (CI can skip slow reinstall)

set +e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

ERROR_COUNT=0
WARNING_COUNT=0
SECTION6_COVERAGE_STATUS=SKIPPED

RED=$'\033[91m'
GREEN=$'\033[92m'
YELLOW=$'\033[93m'
BLUE=$'\033[94m'
CYAN=$'\033[96m'
NC=$'\033[0m'

color_echo() {
  local c="$1"
  shift
  printf '%b%s%b\n' "$c" "$*" "$NC"
}

PY=(python3)
if [[ -x "$ROOT/venv/bin/python" ]]; then
  PY=("$ROOT/venv/bin/python")
elif command -v python3 >/dev/null 2>&1; then
  PY=(python3)
elif command -v python >/dev/null 2>&1; then
  PY=(python)
else
  color_echo "$RED" "ERROR: no python3/python on PATH"
  exit 1
fi

section_done() {
  local status="$1"
  shift
  if [[ "$status" == PASSED ]]; then
    color_echo "$GREEN" "  OK $*"
  elif [[ "$status" == SKIPPED ]]; then
    color_echo "$YELLOW" "  Skipped $*"
  elif [[ "$status" == WARNING ]]; then
    color_echo "$YELLOW" "  ! $*"
  else
    color_echo "$RED" "  X $*"
  fi
}

echo ""
color_echo "$CYAN" "========================================"
color_echo "$CYAN" "  DURGASAI BACKEND (FASTAPI) STATE CHECK"
color_echo "$CYAN" "========================================"
echo ""

if [[ ! -f app/main.py ]]; then
  color_echo "$RED" "ERROR: app/main.py not found under $ROOT"
  exit 1
fi

color_echo "$BLUE" "Current directory: $ROOT"
color_echo "$BLUE" "Using Python: ${PY[*]}"
echo ""

SECTION0_STATUS=SKIPPED
SECTION0B_STATUS=SKIPPED
SECTION1_STATUS=SKIPPED
SECTION2_STATUS=SKIPPED
SECTION3_STATUS=SKIPPED
SECTION4_STATUS=SKIPPED
SECTION4P_STATUS=SKIPPED
SECTION5_STATUS=SKIPPED
SECTION6_STATUS=SKIPPED
SECTION7_STATUS=SKIPPED
SECTION8_STATUS=SKIPPED
SECTION9_STATUS=SKIPPED

if [[ "${SKIP_CSS_INVENTORY:-}" == "1" ]]; then
  color_echo "$YELLOW" "[0] Source inventory skipped (SKIP_CSS_INVENTORY=1)"
else
  color_echo "$CYAN" "[0] Python source inventory (app / scripts / tests)..."
  echo "----------------------------------------"
  mkdir -p reports
  color_echo "$BLUE" "  Output: reports/durgasai-source-inventory.txt"
  {
    echo "DURGASAI BACKEND - Python modules"
    echo "Generated: $(date -Iseconds 2>/dev/null || date)"
    echo ""
    echo "=== app ==="
    find app -name '*.py' -type f 2>/dev/null | sort
    echo ""
    echo "=== scripts ==="
    find scripts -name '*.py' -type f 2>/dev/null | sort
    echo ""
    echo "=== tests ==="
    find tests -name '*.py' -type f 2>/dev/null | sort
  } >reports/durgasai-source-inventory.txt 2>&1
  SECTION0_STATUS=PASSED
  section_done PASSED "Inventory written"
  echo ""
fi

if [[ "${SKIP_DOCKER_HINT:-}" == "1" ]]; then
  SECTION0B_STATUS=SKIPPED
else
  color_echo "$CYAN" "[0b] Docker Compose (optional)"
  echo "----------------------------------------"
  color_echo "$BLUE" "  Copy .env.example to .env; set POSTGRES_PASSWORD, JWT_SECRET_KEY, API_KEY."
  color_echo "$BLUE" "  Start: docker compose --env-file .env -f compose.yaml up -d --build"
  color_echo "$BLUE" "  See docker/README.md and scripts/docker-up.sh"
  SECTION0B_STATUS=DONE
  echo ""
fi

color_echo "$CYAN" "[1/10] Dependencies (pip)..."
echo "----------------------------------------"
if [[ "${SKIP_PIP_INSTALL:-}" == "1" ]]; then
  SECTION1_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_PIP_INSTALL=1)"
else
  color_echo "$YELLOW" "  Running: ${PY[*]} -m pip install --upgrade pip"
  "${PY[@]}" -m pip install --upgrade pip
  if [[ $? -ne 0 ]]; then
    ((WARNING_COUNT++)) || true
    color_echo "$YELLOW" "  ! pip upgrade warning"
  fi
  color_echo "$YELLOW" "  Running: pip install -r requirements.txt -r requirements-dev.txt"
  "${PY[@]}" -m pip install --no-warn-script-location -r requirements.txt -r requirements-dev.txt
  if [[ $? -ne 0 ]]; then
    ((ERROR_COUNT++)) || true
    SECTION1_STATUS=FAILED
    section_done FAILED "pip install failed"
    echo ""
    goto_summary=1
  else
    SECTION1_STATUS=PASSED
    section_done PASSED "Dependencies installed"
  fi
fi
echo ""

if [[ "${goto_summary:-}" == "1" ]]; then
  :
else

color_echo "$CYAN" "[2/10] Environment validation (preflight)..."
echo "----------------------------------------"
if [[ "${SKIP_CODEGEN:-}" == "1" ]]; then
  SECTION2_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_CODEGEN=1)"
elif [[ -f scripts/validate_env.py ]]; then
  color_echo "$BLUE" "  Running: scripts/validate_env.py"
  "${PY[@]}" scripts/validate_env.py
  rc=$?
  if [[ $rc -ne 0 ]]; then
    if [[ "${ENV_VALIDATE_NO_FAIL:-}" == "1" ]]; then
      ((WARNING_COUNT++)) || true
      SECTION2_STATUS=WARNING
      color_echo "$YELLOW" "  ! validate_env failed (ENV_VALIDATE_NO_FAIL=1)"
    else
      ((ERROR_COUNT++)) || true
      SECTION2_STATUS=FAILED
      color_echo "$RED" "  X validate_env failed"
      goto_summary=1
    fi
  else
    SECTION2_STATUS=PASSED
    section_done PASSED "Environment validation passed"
  fi
else
  ((WARNING_COUNT++)) || true
  SECTION2_STATUS=WARNING
  color_echo "$YELLOW" "  ! scripts/validate_env.py not found"
fi
echo ""
fi

if [[ "${goto_summary:-}" == "1" ]]; then
  :
else

color_echo "$CYAN" "[3/10] Type checking (mypy)..."
echo "----------------------------------------"
if [[ "${SKIP_MYPY:-}" == "1" ]]; then
  SECTION3_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_MYPY=1)"
else
  "${PY[@]}" -m mypy app/
  rc=$?
  if [[ $rc -ne 0 ]]; then
    if [[ "${MYPY_STRICT:-}" == "1" ]]; then
      ((ERROR_COUNT++)) || true
      SECTION3_STATUS=FAILED
      color_echo "$RED" "  X mypy failed (MYPY_STRICT=1)"
    else
      ((WARNING_COUNT++)) || true
      SECTION3_STATUS=WARNING
      color_echo "$YELLOW" "  ! mypy issues (warning only)"
    fi
  else
    SECTION3_STATUS=PASSED
    section_done PASSED "mypy passed"
  fi
fi
echo ""

color_echo "$CYAN" "[4/10] Formatting checks (black)..."
echo "----------------------------------------"
if [[ "${SKIP_FORMAT_CHECK:-}" == "1" ]]; then
  SECTION4_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_FORMAT_CHECK=1)"
else
  "${PY[@]}" -m black --check app/ scripts/ tests/
  if [[ $? -ne 0 ]]; then
    ((ERROR_COUNT++)) || true
    SECTION4_STATUS=FAILED
    color_echo "$RED" "  X black --check failed"
  else
    SECTION4_STATUS=PASSED
    section_done PASSED "black check passed"
  fi
fi
echo ""

color_echo "$CYAN" "[4b/10] Prettier (npm run format:check)..."
echo "----------------------------------------"
if [[ "${SKIP_PRETTIER:-}" == "1" ]]; then
  SECTION4P_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_PRETTIER=1)"
elif [[ ! -f package.json ]]; then
  ((WARNING_COUNT++)) || true
  SECTION4P_STATUS=WARNING
  color_echo "$YELLOW" "  ! package.json not found"
elif ! command -v npm >/dev/null 2>&1; then
  ((WARNING_COUNT++)) || true
  SECTION4P_STATUS=WARNING
  color_echo "$YELLOW" "  ! npm not on PATH"
else
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
  if [[ $? -ne 0 ]]; then
    ((WARNING_COUNT++)) || true
    SECTION4P_STATUS=WARNING
    color_echo "$YELLOW" "  ! npm install failed"
  else
    npm run format:check
    if [[ $? -ne 0 ]]; then
      ((WARNING_COUNT++)) || true
      SECTION4P_STATUS=WARNING
      color_echo "$YELLOW" "  ! format:check failed — run: npm run format"
    else
      SECTION4P_STATUS=PASSED
      section_done PASSED "Prettier check passed"
    fi
  fi
fi
echo ""

color_echo "$CYAN" "[5/10] Linting (ruff)..."
echo "----------------------------------------"
if [[ "${SKIP_LINT:-}" == "1" ]]; then
  SECTION5_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_LINT=1)"
else
  "${PY[@]}" -m ruff check app/ scripts/ tests/
  if [[ $? -ne 0 ]]; then
    ((ERROR_COUNT++)) || true
    SECTION5_STATUS=FAILED
    color_echo "$RED" "  X ruff failed"
  else
    SECTION5_STATUS=PASSED
    section_done PASSED "ruff passed"
  fi
fi
echo ""

color_echo "$CYAN" "[6/10] Running tests (pytest)..."
echo "----------------------------------------"
if [[ "${SKIP_TESTS:-}" == "1" ]]; then
  SECTION6_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_TESTS=1)"
else
  PREV_ENV="${ENVIRONMENT-}"
  export ENVIRONMENT=test
  color_echo "$BLUE" "  ENVIRONMENT=test"
  "${PY[@]}" -m pytest tests/
  rc=$?
  if [[ -n "${PREV_ENV}" ]]; then
    export ENVIRONMENT="$PREV_ENV"
  else
    unset ENVIRONMENT
  fi
  if [[ $rc -ne 0 ]]; then
    ((ERROR_COUNT++)) || true
    SECTION6_STATUS=FAILED
    color_echo "$RED" "  X Tests failed"
  else
    SECTION6_STATUS=PASSED
    section_done PASSED "Tests passed"
  fi
fi
echo ""

if [[ "${RUN_TEST_COVERAGE:-}" == "1" ]]; then
  if [[ "${SKIP_TESTS:-}" == "1" ]]; then
    color_echo "$YELLOW" "[6b] Coverage skipped (SKIP_TESTS=1)"
  else
    color_echo "$CYAN" "[6b] Pytest coverage (RUN_TEST_COVERAGE=1)..."
    echo "----------------------------------------"
    export ENVIRONMENT=test
    "${PY[@]}" -m pytest tests/ --cov=app --cov-report=term-missing
    if [[ $? -ne 0 ]]; then
      ((WARNING_COUNT++)) || true
      SECTION6_COVERAGE_STATUS=WARNING
      color_echo "$YELLOW" "  Warning: coverage run failed"
    else
      SECTION6_COVERAGE_STATUS=PASSED
      section_done PASSED "Coverage run completed"
    fi
    if [[ -n "${PREV_ENV:-}" ]]; then
      export ENVIRONMENT="$PREV_ENV"
    else
      unset ENVIRONMENT
    fi
  fi
  echo ""
else
  color_echo "$BLUE" "[6b] Coverage skipped (set RUN_TEST_COVERAGE=1 for pytest --cov=app)"
  echo ""
fi

color_echo "$CYAN" "[7/10] API best-practices checklist..."
echo "----------------------------------------"
if [[ "${SKIP_BEST_PRACTICES:-}" == "1" ]]; then
  SECTION7_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_BEST_PRACTICES=1)"
elif [[ -f scripts/check_best_practices.py ]]; then
  BP_FMT="${BEST_PRACTICES_FORMAT:-both}"
  [[ "$BP_FMT" != "text" && "$BP_FMT" != "json" && "$BP_FMT" != "both" ]] && BP_FMT=both
  BP_ARGS=(scripts/check_best_practices.py --output reports/check_report_bat.json --format "$BP_FMT")
  if [[ -n "${BEST_PRACTICES_THRESHOLD:-}" ]]; then
    BP_ARGS+=(--threshold "$BEST_PRACTICES_THRESHOLD")
  fi
  if [[ "${BEST_PRACTICES_NO_FAIL:-}" == "1" ]]; then
    BP_ARGS+=(--no-fail)
    "${PY[@]}" "${BP_ARGS[@]}"
    SECTION7_STATUS=PASSED
    section_done PASSED "Best-practices report written (--no-fail)"
  else
    "${PY[@]}" "${BP_ARGS[@]}"
    if [[ $? -ne 0 ]]; then
      ((ERROR_COUNT++)) || true
      SECTION7_STATUS=FAILED
      color_echo "$RED" "  X Best-practices check failed"
    else
      SECTION7_STATUS=PASSED
      section_done PASSED "Best-practices check passed"
    fi
  fi
else
  ((WARNING_COUNT++)) || true
  SECTION7_STATUS=WARNING
  color_echo "$YELLOW" "  ! scripts/check_best_practices.py not found"
fi
echo ""

color_echo "$CYAN" "[8/10] Final format (black)..."
echo "----------------------------------------"
if [[ "${SKIP_FINAL_FORMAT:-}" == "1" ]]; then
  SECTION8_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_FINAL_FORMAT=1)"
else
  "${PY[@]}" -m black app/ scripts/ tests/
  if [[ $? -ne 0 ]]; then
    ((WARNING_COUNT++)) || true
    SECTION8_STATUS=WARNING
    color_echo "$YELLOW" "  ! black apply had issues"
  else
    SECTION8_STATUS=PASSED
    section_done PASSED "black formatting applied"
    if [[ "$SECTION4_STATUS" == "FAILED" ]]; then
      SECTION4_STATUS=FIXED
      ((ERROR_COUNT--)) || true
    fi
  fi
fi
echo ""

color_echo "$CYAN" "[9/10] Install / import integrity..."
echo "----------------------------------------"
if [[ "${SKIP_BUILD:-}" == "1" ]]; then
  SECTION9_STATUS=SKIPPED
  section_done SKIPPED "(SKIP_BUILD=1)"
else
  DO_PIP_CHECK=1
  [[ "${SKIP_PIP_CHECK:-}" == "1" ]] && DO_PIP_CHECK=0
  [[ "${FORCE_PIP_CHECK:-}" == "1" ]] && DO_PIP_CHECK=1
  if [[ "$DO_PIP_CHECK" == "1" ]]; then
    if "${PY[@]}" -c "import sys; raise SystemExit(0 if (sys.platform=='win32' and sys.version_info>=(3,13)) else 1)" 2>/dev/null; then
      if [[ "${FORCE_PIP_CHECK:-}" != "1" ]]; then
        DO_PIP_CHECK=0
        color_echo "$BLUE" "  Skipping pip check (Windows Python 3.13+; set FORCE_PIP_CHECK=1 to run)"
      fi
    fi
  fi
  if [[ "$DO_PIP_CHECK" == "1" ]]; then
    "${PY[@]}" -m pip check
    if [[ $? -ne 0 ]]; then
      ((WARNING_COUNT++)) || true
      SECTION9_STATUS=WARNING
      color_echo "$YELLOW" "  ! pip check reported conflicts"
    else
      color_echo "$GREEN" "  OK pip check"
    fi
  elif [[ "${SKIP_PIP_CHECK:-}" == "1" ]]; then
    color_echo "$BLUE" "  pip check skipped (SKIP_PIP_CHECK=1)"
  fi
  color_echo "$BLUE" "  Import smoke: from app.main import app"
  "${PY[@]}" -c "from app.main import app"
  if [[ $? -ne 0 ]]; then
    ((ERROR_COUNT++)) || true
    SECTION9_STATUS=FAILED
    color_echo "$RED" "  X Failed to import app.main"
  else
    if [[ "$SECTION9_STATUS" != "WARNING" ]]; then
      SECTION9_STATUS=PASSED
    fi
    color_echo "$GREEN" "  OK app.main import succeeded"
  fi
fi
echo ""

fi

echo ""
color_echo "$CYAN" "========================================"
color_echo "$CYAN" "  SUMMARY"
color_echo "$CYAN" "========================================"
echo ""
color_echo "$BLUE" "Section Status:"
echo "  [0] Source inventory:       $SECTION0_STATUS"
echo "  [0b] Docker hint:           $SECTION0B_STATUS"
echo "  [1] Pip dependencies:      $SECTION1_STATUS"
echo "  [2] Environment validate:  $SECTION2_STATUS"
echo "  [3] mypy:                   $SECTION3_STATUS"
echo "  [4] black --check:          $SECTION4_STATUS"
echo "  [4b] Prettier:              $SECTION4P_STATUS"
echo "  [5] ruff:                   $SECTION5_STATUS"
echo "  [6] pytest:                 $SECTION6_STATUS"
echo "  [6b] pytest coverage:       $SECTION6_COVERAGE_STATUS"
echo "  [7] Best practices:        $SECTION7_STATUS"
echo "  [8] black (apply):          $SECTION8_STATUS"
echo "  [9] pip check + import:     $SECTION9_STATUS"
echo ""

if [[ "$ERROR_COUNT" -eq 0 ]]; then
  color_echo "$GREEN" "  OK All blocking checks passed!"
  if [[ "$WARNING_COUNT" -gt 0 ]]; then
    color_echo "$YELLOW" "  Found $WARNING_COUNT warning(s)"
  fi
  echo ""
  if [[ "${SKIP_DEV_SERVER:-}" == "1" || "${NO_PROMPT:-}" == "1" || -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" ]]; then
    :
  else
    color_echo "$CYAN" "  Start API server? [y/N]"
    read -r -n 1 ans
    echo ""
    if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
      color_echo "$CYAN" "[10/10] Starting uvicorn (reload)..."
      color_echo "$BLUE" "  ${PY[*]} -m uvicorn app.main:app --reload"
      color_echo "$BLUE" "  Press Ctrl+C to stop"
      echo ""
      exec "${PY[@]}" -m uvicorn app.main:app --reload
    fi
  fi
else
  color_echo "$RED" "  X Found $ERROR_COUNT error(s)"
  if [[ "$WARNING_COUNT" -gt 0 ]]; then
    color_echo "$YELLOW" "  Found $WARNING_COUNT warning(s)"
  fi
  echo ""
  color_echo "$YELLOW" "  Please fix the errors before proceeding."
fi

echo ""
color_echo "$CYAN" "========================================"
color_echo "$CYAN" "  CHECK COMPLETE"
color_echo "$CYAN" "========================================"
echo ""

if [[ "$ERROR_COUNT" -gt 0 ]]; then
  exit 1
fi
exit 0
