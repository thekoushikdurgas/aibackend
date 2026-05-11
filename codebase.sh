#!/usr/bin/env bash
# DURGASAI BACKEND (FASTAPI) — codebase state check (Linux/macOS).
# Run from ai.backend: ./codebase.sh
#
# Same steps as codebase.bat:
#   0 Source inventory
#   1 pip install (requirements.txt + requirements-dev.txt)
#   2 Environment validation (scripts/validate_env.py if present)
#   3 mypy
#   4 black --check
#   4b Prettier (npm run format:check / npx)
#   5 ruff check
#   6 pytest
#   6b coverage if RUN_TEST_COVERAGE=1
#   7 scripts/check_best_practices.py (if present)
#   8 black app/ scripts/ tests/
#   9 pip check + import smoke
#
# Optional environment variables (same semantics as codebase.bat):
# SKIP_CSS_INVENTORY=1, SKIP_PIP_INSTALL=1, SKIP_CODEGEN=1, ENV_VALIDATE_NO_FAIL=1,
# SKIP_MYPY=1, MYPY_STRICT=1, SKIP_FORMAT_CHECK=1, SKIP_LINT=1, SKIP_TESTS=1,
# RUN_TEST_COVERAGE=1, SKIP_BEST_PRACTICES=1, BEST_PRACTICES_NO_FAIL=1,
# BEST_PRACTICES_THRESHOLD=N, BEST_PRACTICES_FORMAT=text|json|both,
# SKIP_FINAL_FORMAT=1, SKIP_BUILD=1, SKIP_PIP_CHECK=1, SKIP_PRETTIER=1,
# SKIP_DEV_SERVER=1, NO_PROMPT=1 — skip interactive uvicorn prompt / server start

set +e

RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
CYAN='\033[96m'
NC='\033[0m'

color_echo() {
  local c="$1"
  shift
  printf '%b%s%b\n' "$c" "$*" "$NC"
}

API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ERROR_COUNT=0
WARNING_COUNT=0
SECTION6_COVERAGE_STATUS="SKIPPED"

echo ""
color_echo "$CYAN" "========================================"
color_echo "$CYAN" "  DURGASAI BACKEND (FASTAPI) STATE CHECK"
color_echo "$CYAN" "========================================"
echo ""

if [[ ! -f "${API_DIR}/app/main.py" ]]; then
  color_echo "$RED" "ERROR: app/main.py not found under: ${API_DIR}"
  exit 1
fi

cd "$API_DIR" || exit 1
color_echo "$BLUE" "Current directory: $(pwd)"

PY=""
PY_EXTRA=()
if [[ -x "${API_DIR}/venv/bin/python" ]]; then
  PY="${API_DIR}/venv/bin/python"
  if "${PY}" -c "import sys" 2>/dev/null; then
    color_echo "$BLUE" "Using venv Python: ${PY}"
  else
    color_echo "$YELLOW" "venv/bin/python failed import check. Recreate: python3 -m venv venv"
    PY=""
  fi
fi
if [[ -z "$PY" ]]; then
  if command -v python3 &>/dev/null && python3 -c "import sys" 2>/dev/null; then
    PY="$(command -v python3)"
    color_echo "$BLUE" "Using python3 from PATH: ${PY}"
  elif command -v python &>/dev/null && python -c "import sys" 2>/dev/null; then
    PY="$(command -v python)"
    color_echo "$BLUE" "Using python from PATH: ${PY}"
  else
    color_echo "$YELLOW" "No working Python; install Python 3.10+ or fix venv"
    PY="python3"
  fi
fi
echo ""

SECTION0_STATUS="SKIPPED"
SECTION1_STATUS="SKIPPED"
SECTION2_STATUS="SKIPPED"
SECTION3_STATUS="SKIPPED"
SECTION4_STATUS="SKIPPED"
SECTION5_STATUS="SKIPPED"
SECTION6_STATUS="SKIPPED"
SECTION7_STATUS="SKIPPED"
SECTION8_STATUS="SKIPPED"
SECTION9_STATUS="SKIPPED"
SECTION4P_STATUS="SKIPPED"

if [[ "${SKIP_CSS_INVENTORY:-}" == "1" ]]; then
  color_echo "$YELLOW" "[0] Source inventory skipped (SKIP_CSS_INVENTORY=1)"
  SECTION0_STATUS="SKIPPED"
  echo ""
else
  color_echo "$CYAN" "[0] Python source inventory (app / scripts / tests)..."
  echo "----------------------------------------"
  mkdir -p reports
  color_echo "$BLUE" "  Output: reports/api-source-inventory.txt"
  {
    echo "DURGASAI BACKEND - Python modules under app/, scripts/, tests/"
    echo "Generated: $(date)"
    echo ""
    echo "=== app ==="
    find app -name '*.py' 2>/dev/null | sort || true
    echo ""
    echo "=== scripts ==="
    find scripts -name '*.py' 2>/dev/null | sort || true
    echo ""
    echo "=== tests ==="
    find tests -name '*.py' 2>/dev/null | sort || true
  } > "reports/api-source-inventory.txt" 2>&1
  color_echo "$GREEN" "  OK Inventory written"
  SECTION0_STATUS="PASSED"
  echo ""
fi

color_echo "$CYAN" "[0b] Self-hosted Supabase (optional)"
echo "----------------------------------------"
color_echo "$BLUE" "  For Docker: copy .env.example to .env and set POSTGRES_PASSWORD / secrets"
color_echo "$BLUE" "  Start stack: docker compose --env-file .env -f compose.yaml up -d"
color_echo "$BLUE" "  See docker/README.md for ports 8080 (Kong) and 3001 (Studio)."
echo ""

color_echo "$CYAN" "[1/10] Dependencies (pip)..."
echo "----------------------------------------"
if [[ "${SKIP_PIP_INSTALL:-}" == "1" ]]; then
  color_echo "$YELLOW" "  Skipped (SKIP_PIP_INSTALL=1)"
  SECTION1_STATUS="SKIPPED"
else
  color_echo "$YELLOW" "  Running: ${PY} -m pip install --upgrade pip"
  "${PY}" "${PY_EXTRA[@]}" -m pip install --upgrade pip
  if [[ $? -ne 0 ]]; then
    ((WARNING_COUNT++)) || true
    color_echo "$YELLOW" "  ! pip upgrade warning"
  fi
  color_echo "$YELLOW" "  Running: ${PY} -m pip install --no-warn-script-location -r requirements.txt -r requirements-dev.txt"
  "${PY}" "${PY_EXTRA[@]}" -m pip install --no-warn-script-location -r requirements.txt -r requirements-dev.txt
  if [[ $? -ne 0 ]]; then
    ((ERROR_COUNT++)) || true
    SECTION1_STATUS="FAILED"
    color_echo "$RED" "  X pip install failed"
  else
    SECTION1_STATUS="PASSED"
    color_echo "$GREEN" "  OK Dependencies installed"
  fi
fi
echo ""

if [[ "$SECTION1_STATUS" == "FAILED" ]]; then
  goto_summary=true
else
  goto_summary=false
fi

if ! $goto_summary; then
  color_echo "$CYAN" "[2/10] Environment validation (preflight)..."
  echo "----------------------------------------"
  if [[ "${SKIP_CODEGEN:-}" == "1" ]]; then
    color_echo "$YELLOW" "  Skipped (SKIP_CODEGEN=1)"
    SECTION2_STATUS="SKIPPED"
  elif [[ -f scripts/validate_env.py ]]; then
    color_echo "$BLUE" "  Running: ${PY} scripts/validate_env.py"
    "${PY}" "${PY_EXTRA[@]}" scripts/validate_env.py
    rv=$?
    if [[ $rv -ne 0 ]]; then
      if [[ "${ENV_VALIDATE_NO_FAIL:-}" == "1" ]]; then
        ((WARNING_COUNT++)) || true
        SECTION2_STATUS="WARNING"
        color_echo "$YELLOW" "  ! validate_env reported issues (ENV_VALIDATE_NO_FAIL=1)"
      else
        ((WARNING_COUNT++)) || true
        SECTION2_STATUS="WARNING"
        color_echo "$YELLOW" "  ! validate_env failed - fix .env or set SKIP_CODEGEN=1 / ENV_VALIDATE_NO_FAIL=1"
      fi
    else
      SECTION2_STATUS="PASSED"
      color_echo "$GREEN" "  OK Environment validation passed"
    fi
  else
    ((WARNING_COUNT++)) || true
    SECTION2_STATUS="WARNING"
    color_echo "$YELLOW" "  ! scripts/validate_env.py not found"
  fi
  echo ""

  color_echo "$CYAN" "[3/10] Type checking (mypy)..."
  echo "----------------------------------------"
  if [[ "${SKIP_MYPY:-}" == "1" ]]; then
    color_echo "$YELLOW" "  Skipped (SKIP_MYPY=1)"
    SECTION3_STATUS="SKIPPED"
  else
    color_echo "$YELLOW" "  Running: ${PY} -m mypy app/"
    "${PY}" "${PY_EXTRA[@]}" -m mypy app/
    if [[ $? -ne 0 ]]; then
      if [[ "${MYPY_STRICT:-}" == "1" ]]; then
        ((ERROR_COUNT++)) || true
        SECTION3_STATUS="FAILED"
        color_echo "$RED" "  X mypy failed (MYPY_STRICT=1)"
      else
        ((WARNING_COUNT++)) || true
        SECTION3_STATUS="WARNING"
        color_echo "$YELLOW" "  ! mypy issues (warning only; set MYPY_STRICT=1 to fail)"
      fi
    else
      SECTION3_STATUS="PASSED"
      color_echo "$GREEN" "  OK mypy passed"
    fi
  fi
  echo ""

  color_echo "$CYAN" "[4/10] Formatting checks (black)..."
  echo "----------------------------------------"
  if [[ "${SKIP_FORMAT_CHECK:-}" == "1" ]]; then
    color_echo "$YELLOW" "  Skipped (SKIP_FORMAT_CHECK=1)"
    SECTION4_STATUS="SKIPPED"
  else
    color_echo "$YELLOW" "  Running: ${PY} -m black --check app/ scripts/ tests/"
    "${PY}" "${PY_EXTRA[@]}" -m black --check app/ scripts/ tests/
    if [[ $? -ne 0 ]]; then
      ((ERROR_COUNT++)) || true
      SECTION4_STATUS="FAILED"
      color_echo "$RED" "  X black --check failed - run: black app/ scripts/ tests/"
    else
      SECTION4_STATUS="PASSED"
      color_echo "$GREEN" "  OK black check passed"
    fi
  fi
  echo ""

  color_echo "$CYAN" "[4b/10] Prettier (Markdown, JSON, YAML, etc.)..."
  echo "----------------------------------------"
  if [[ "${SKIP_PRETTIER:-}" == "1" ]]; then
    color_echo "$YELLOW" "  Skipped (SKIP_PRETTIER=1)"
    SECTION4P_STATUS="SKIPPED"
  elif ! command -v npx &>/dev/null; then
    ((WARNING_COUNT++)) || true
    SECTION4P_STATUS="WARNING"
    color_echo "$YELLOW" "  ! npx not on PATH - install Node.js or set SKIP_PRETTIER=1"
  else
    color_echo "$BLUE" "  Complements black (Python); formats Markdown, JSON, YAML, etc."
    if [[ -f node_modules/prettier/package.json ]]; then
      color_echo "$YELLOW" "  Running: npm run format:check"
      npm run format:check
    else
      if [[ -f package.json ]]; then
        color_echo "$YELLOW" "  ! Run: npm install (pinned Prettier); using npx until then"
      fi
      color_echo "$YELLOW" "  Running: npx prettier --check ."
      npx prettier --check .
    fi
    pr=$?
    if [[ $pr -ne 0 ]]; then
      ((WARNING_COUNT++)) || true
      SECTION4P_STATUS="WARNING"
      if [[ -f node_modules/prettier/package.json ]]; then
        color_echo "$YELLOW" "  Prettier issues - running: npm run format"
        npm run format
      else
        color_echo "$YELLOW" "  Prettier issues - running: npx prettier --write ."
        npx prettier --write .
      fi
      if [[ $? -ne 0 ]]; then
        ((WARNING_COUNT++)) || true
        SECTION4P_STATUS="WARNING"
        color_echo "$YELLOW" "  ! Prettier write had issues"
      else
        if [[ -f node_modules/prettier/package.json ]]; then
          npm run format:check
        else
          npx prettier --check .
        fi
        if [[ $? -ne 0 ]]; then
          ((WARNING_COUNT++)) || true
          SECTION4P_STATUS="WARNING"
        else
          SECTION4P_STATUS="WARNING_FIXED"
          color_echo "$GREEN" "  OK Prettier formatted"
        fi
      fi
    else
      SECTION4P_STATUS="PASSED"
      color_echo "$GREEN" "  OK Prettier check passed"
    fi
  fi
  echo ""

  color_echo "$CYAN" "[5/10] Linting (ruff)..."
  echo "----------------------------------------"
  if [[ "${SKIP_LINT:-}" == "1" ]]; then
    color_echo "$YELLOW" "  Skipped (SKIP_LINT=1)"
    SECTION5_STATUS="SKIPPED"
  else
    color_echo "$YELLOW" "  Running: ${PY} -m ruff check app/ scripts/ tests/"
    "${PY}" "${PY_EXTRA[@]}" -m ruff check app/ scripts/ tests/
    if [[ $? -ne 0 ]]; then
      ((ERROR_COUNT++)) || true
      SECTION5_STATUS="FAILED"
      color_echo "$RED" "  X ruff check failed"
    else
      SECTION5_STATUS="PASSED"
      color_echo "$GREEN" "  OK ruff passed"
    fi
  fi
  echo ""

  color_echo "$CYAN" "[6/10] Running tests (pytest)..."
  echo "----------------------------------------"
  if [[ "${SKIP_TESTS:-}" == "1" ]]; then
    color_echo "$YELLOW" "  Skipped (SKIP_TESTS=1)"
    SECTION6_STATUS="SKIPPED"
  else
    PREV_ENV="${ENVIRONMENT-}"
    export ENVIRONMENT=test
    color_echo "$BLUE" "  ENVIRONMENT=test"
    color_echo "$YELLOW" "  Running: ${PY} -m pytest tests/ -q --tb=short"
    "${PY}" "${PY_EXTRA[@]}" -m pytest tests/ -q --tb=short
    pr=$?
    if [[ $PREV_ENV ]]; then
      export ENVIRONMENT="$PREV_ENV"
    else
      unset ENVIRONMENT
    fi
    if [[ $pr -ne 0 ]]; then
      ((ERROR_COUNT++)) || true
      SECTION6_STATUS="FAILED"
      color_echo "$RED" "  X Tests failed"
    else
      SECTION6_STATUS="PASSED"
      color_echo "$GREEN" "  OK Tests passed"
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
      color_echo "$YELLOW" "  Running: ${PY} -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing"
      "${PY}" "${PY_EXTRA[@]}" -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing
      if [[ $? -ne 0 ]]; then
        ((WARNING_COUNT++)) || true
        SECTION6_COVERAGE_STATUS="WARNING"
        color_echo "$YELLOW" "  Warning: coverage run failed or thresholds"
      else
        SECTION6_COVERAGE_STATUS="PASSED"
        color_echo "$GREEN" "  OK Coverage run completed"
      fi
      if [[ -n "${PREV_ENV:-}" ]]; then export ENVIRONMENT="$PREV_ENV"; else unset ENVIRONMENT; fi
    fi
    echo ""
  else
    color_echo "$BLUE" "[6b] Coverage skipped (set RUN_TEST_COVERAGE=1 for pytest --cov=app)"
    echo ""
  fi

  if [[ "${SKIP_BEST_PRACTICES:-}" == "1" ]]; then
    color_echo "$YELLOW" "[7/10] Best practices skipped (SKIP_BEST_PRACTICES=1)"
    SECTION7_STATUS="SKIPPED"
    echo ""
  else
    color_echo "$CYAN" "[7/10] API best-practices checklist..."
    echo "----------------------------------------"
    color_echo "$BLUE" "  scripts/check_best_practices.py - config .api-checker-config.json"
    color_echo "$BLUE" "  Output: reports/check_report.json"
    BP_FMT="${BEST_PRACTICES_FORMAT:-both}"
    [[ "$BP_FMT" != "text" && "$BP_FMT" != "json" && "$BP_FMT" != "both" ]] && BP_FMT="both"

    if [[ -f scripts/check_best_practices.py ]]; then
      BP_ARGS=(scripts/check_best_practices.py --output reports/check_report.json --format "$BP_FMT")
      if [[ -n "${BEST_PRACTICES_THRESHOLD:-}" ]]; then
        BP_ARGS+=(--threshold "$BEST_PRACTICES_THRESHOLD")
      fi
      if [[ "${BEST_PRACTICES_NO_FAIL:-}" == "1" ]]; then
        if [[ -n "${BEST_PRACTICES_THRESHOLD:-}" ]]; then
          color_echo "$YELLOW" "  Running: check_best_practices.py --no-fail --threshold …"
        else
          color_echo "$YELLOW" "  Running: check_best_practices.py --no-fail"
        fi
        BP_ARGS+=(--no-fail)
      else
        if [[ -n "${BEST_PRACTICES_THRESHOLD:-}" ]]; then
          color_echo "$YELLOW" "  Running: check_best_practices.py --threshold …"
        else
          color_echo "$YELLOW" "  Running: check_best_practices.py"
        fi
      fi
      "${PY}" "${PY_EXTRA[@]}" "${BP_ARGS[@]}"
      if [[ $? -ne 0 ]]; then
        ((ERROR_COUNT++)) || true
        SECTION7_STATUS="FAILED"
        color_echo "$RED" "  X Best-practices below threshold or script error"
      else
        SECTION7_STATUS="PASSED"
        color_echo "$GREEN" "  OK Best-practices check passed"
      fi
    else
      ((WARNING_COUNT++)) || true
      SECTION7_STATUS="WARNING"
      color_echo "$YELLOW" "  ! scripts/check_best_practices.py not found"
    fi
    echo ""
  fi

  if [[ "${SKIP_FINAL_FORMAT:-}" == "1" ]]; then
    color_echo "$YELLOW" "[8/10] Final format skipped (SKIP_FINAL_FORMAT=1)"
    SECTION8_STATUS="SKIPPED"
    echo ""
  else
    color_echo "$CYAN" "[8/10] Final format (black)..."
    echo "----------------------------------------"
    color_echo "$YELLOW" "  Running: ${PY} -m black app/ scripts/ tests/"
    "${PY}" "${PY_EXTRA[@]}" -m black app/ scripts/ tests/
    if [[ $? -ne 0 ]]; then
      ((WARNING_COUNT++)) || true
      SECTION8_STATUS="WARNING"
      color_echo "$YELLOW" "  ! black apply had issues"
    else
      SECTION8_STATUS="PASSED"
      color_echo "$GREEN" "  OK black formatting applied"
      if [[ "$SECTION4_STATUS" == "FAILED" ]]; then
        SECTION4_STATUS="FIXED"
        ((ERROR_COUNT--)) || true
      fi
    fi
    echo ""
  fi

  color_echo "$CYAN" "[9/10] Install / import integrity..."
  echo "----------------------------------------"
  if [[ "${SKIP_BUILD:-}" == "1" ]]; then
    color_echo "$YELLOW" "  Skipped (SKIP_BUILD=1)"
    SECTION9_STATUS="SKIPPED"
  else
    if [[ "${SKIP_PIP_CHECK:-}" == "1" ]]; then
      color_echo "$YELLOW" "  Skipped pip check (SKIP_PIP_CHECK=1)"
    else
      color_echo "$YELLOW" "  Running: ${PY} -m pip check"
      "${PY}" "${PY_EXTRA[@]}" -m pip check
      if [[ $? -ne 0 ]]; then
        ((WARNING_COUNT++)) || true
        SECTION9_STATUS="WARNING"
        color_echo "$YELLOW" "  ! pip check reported conflicts"
      else
        color_echo "$GREEN" "  OK pip check"
      fi
    fi
    color_echo "$BLUE" "  Import smoke: from app.main import app"
    "${PY}" "${PY_EXTRA[@]}" -c "from app.main import app"
    if [[ $? -ne 0 ]]; then
      ((ERROR_COUNT++)) || true
      SECTION9_STATUS="FAILED"
      color_echo "$RED" "  X Failed to import app.main (check .env / deps)"
    else
      if [[ "$SECTION9_STATUS" != "WARNING" ]]; then
        SECTION9_STATUS="PASSED"
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
echo "  [0] Source inventory:              ${SECTION0_STATUS}  (reports/api-source-inventory.txt)"
echo "  [1] Pip dependencies:              ${SECTION1_STATUS}"
echo "  [2] Environment validate:          ${SECTION2_STATUS}"
echo "  [3] mypy:                          ${SECTION3_STATUS}"
echo "  [4] black --check:                 ${SECTION4_STATUS}"
echo "  [4b] Prettier:                     ${SECTION4P_STATUS}"
echo "  [5] ruff check:                    ${SECTION5_STATUS}"
echo "  [6] pytest:                        ${SECTION6_STATUS}"
echo "  [6b] pytest coverage:              ${SECTION6_COVERAGE_STATUS}"
echo "  [7] Best practices (check_*.py):   ${SECTION7_STATUS}"
echo "  [8] black (apply):                 ${SECTION8_STATUS}"
echo "  [9] pip check + import app:        ${SECTION9_STATUS}"
echo ""

if [[ "$ERROR_COUNT" -eq 0 ]]; then
  color_echo "$GREEN" "  OK All blocking checks passed!"
  if [[ "$WARNING_COUNT" -gt 0 ]]; then
    color_echo "$YELLOW" "  Found ${WARNING_COUNT} warning(s)"
  fi
  echo ""
  if [[ "${SKIP_DEV_SERVER:-}" != "1" && "${NO_PROMPT:-}" != "1" ]]; then
    color_echo "$CYAN" "  Start API server? [y/N]"
    read -r _yn
    case "${_yn:-}" in
      y|Y|yes|YES)
        echo ""
        color_echo "$CYAN" "[10/10] Starting uvicorn (reload)..."
        color_echo "$BLUE" "  ${PY} -m uvicorn app.main:app --reload"
        color_echo "$BLUE" "  Press Ctrl+C to stop"
        echo ""
        "${PY}" "${PY_EXTRA[@]}" -m uvicorn app.main:app --reload
        ;;
      *)
        ;;
    esac
  fi
else
  color_echo "$RED" "  X Found ${ERROR_COUNT} error(s)"
  if [[ "$WARNING_COUNT" -gt 0 ]]; then
    color_echo "$YELLOW" "  Found ${WARNING_COUNT} warning(s)"
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
