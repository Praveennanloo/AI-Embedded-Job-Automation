#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"

PASS=0
FAIL=0

a_ok() { PASS=$((PASS+1)); printf '[PASS] %s\n' "$1"; }
a_fail() { FAIL=$((FAIL+1)); printf '[FAIL] %s\n' "$1"; }

printf '%s\n' '============================================================'
printf '%s\n' 'AI EMBEDDED JOB AUTOMATION - PROJECT DOCTOR'
printf '%s\n' '============================================================'

if python -m compileall -q . -x '(^|/)(\.venv|venv|env|\.git|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache)(/|$)' 2>/dev/null; then
  a_ok 'Python compilation'
else
  a_fail 'Python compilation'
fi

if python - <<'PY'
import app
from ai_engine.job_filter import JobFilter
from search_engine.search_manager import SearchManager
from database_engine.database import Database
print('imports-ok')
PY
then
  a_ok 'Core imports'
else
  a_fail 'Core imports'
fi

if pytest -q; then
  a_ok 'Test suite'
else
  a_fail 'Test suite'
fi

# Start a local API instance with background scheduling disabled so doctor mode
# never launches a provider search cycle merely to test API health.
PORT=8765
LOG=/tmp/ai_embedded_job_doctor_$$.log
PID=''
cleanup() {
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
  rm -f "$LOG"
}
trap cleanup EXIT

SCHEDULER_ENABLED=false python -m uvicorn app:app --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
PID=$!

ready=0
for _ in $(seq 1 60); do
  if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/" >/tmp/ai_embedded_job_root_$$.json 2>/dev/null; then
    ready=1
    break
  fi
  sleep 0.5
done

if [[ "$ready" == "1" ]]; then
  a_ok 'FastAPI startup and root endpoint'
else
  a_fail 'FastAPI startup and root endpoint'
  tail -50 "$LOG" || true
fi
rm -f /tmp/ai_embedded_job_root_$$.json

if python - <<'PY'
from ai_engine.job_filter import JobFilter
f = JobFilter()
assert 'intern' not in f._find_keyword_hits('international software company', f.ENTRY_LEVEL_KEYWORDS)
assert 'arm' not in f._find_keyword_hits('harmonic analysis', f.PRIMARY_EMBEDDED_KEYWORDS)
assert 'intern' in f._find_keyword_hits('intern software engineer', f.ENTRY_LEVEL_KEYWORDS)
assert 'arm' in f._find_keyword_hits('ARM Linux engineer', f.PRIMARY_EMBEDDED_KEYWORDS)
PY
then
  a_ok 'Keyword regression checks'
else
  a_fail 'Keyword regression checks'
fi

printf '%s\n' '------------------------------------------------------------'
printf 'TOTAL PASS: %s\n' "$PASS"
printf 'TOTAL FAIL: %s\n' "$FAIL"
printf '%s\n' '------------------------------------------------------------'

if [[ "$FAIL" == "0" ]]; then
  printf '%s\n' 'PROJECT DOCTOR RESULT: PASS'
  exit 0
else
  printf '%s\n' 'PROJECT DOCTOR RESULT: FAIL'
  exit 1
fi
