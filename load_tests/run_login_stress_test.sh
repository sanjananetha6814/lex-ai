#!/usr/bin/env bash
set -e

OUTPUT_DIR="results/targeted_login_stress"
mkdir -p "$OUTPUT_DIR"

SERVER_LOG="${OUTPUT_DIR}/server.log"
CONN_MONITOR_LOG="${OUTPUT_DIR}/conn_monitor.log"
SYS_MONITOR_LOG="${OUTPUT_DIR}/system_monitor.log"

echo "================================================================="
echo "  LEXAI TARGETED LOGIN STRESS TEST (PHASE 3, STEP 5)"
echo "  Configuration: 4 Uvicorn Workers | PostgreSQL 16 (max_conn=250)"
echo "  DB Pool: pool_size=25, max_overflow=25"
echo "  Target: 300 Concurrent Login Users @ 50 users/sec for 45 seconds"
echo "  Output Directory: ${OUTPUT_DIR}"
echo "================================================================="

# Load environment variables
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export DB_POOL_SIZE=25
export DB_MAX_OVERFLOW=25
export UVICORN_WORKERS=4

PSQL_BIN="/Applications/Postgres.app/Contents/Versions/16/bin/psql"
if [ ! -x "$PSQL_BIN" ]; then
  PSQL_BIN="psql"
fi

# Clean port 8000
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start backend server
echo "Starting LexAI backend with 4 workers..."
> "$SERVER_LOG"
DATABASE_URL="$DATABASE_URL" \
DB_POOL_SIZE="$DB_POOL_SIZE" \
DB_MAX_OVERFLOW="$DB_MAX_OVERFLOW" \
PYTHONPATH=backend \
./venv/bin/uvicorn app.main:app \
  --app-dir backend \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 4 > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

trap "echo 'Cleaning up...'; kill -9 \$MON_PID \$SYS_PID 2>/dev/null || true; pkill -P \$SERVER_PID 2>/dev/null || true; kill -9 \$SERVER_PID 2>/dev/null || true" EXIT INT TERM

# Wait for /health
READY=0
for i in $(seq 1 30); do
  RES=$(curl -s http://127.0.0.1:8000/health || true)
  if echo "$RES" | grep -q '"status":"healthy"'; then
    READY=1
    break
  fi
  sleep 0.5
done

if [ $READY -ne 1 ]; then
  echo "ERROR: Backend failed to start. Logs:"
  cat "$SERVER_LOG"
  exit 1
fi

echo "Backend ready. Starting connection and system telemetry..."
> "$CONN_MONITOR_LOG"
(
  while true; do
    DATE=$(date +"%T")
    STATS=$($PSQL_BIN -h localhost -p 5432 -U machasanjana -d lexai -t -A -F"|" -c \
      "SELECT count(*) as total, count(*) filter (where state = 'active') as active, count(*) filter (where state = 'idle') as idle FROM pg_stat_activity WHERE datname = 'lexai';" 2>/dev/null || true)
    echo "[$DATE] DB -> $STATS" >> "$CONN_MONITOR_LOG"
    sleep 1
  done
) &
MON_PID=$!

> "$SYS_MONITOR_LOG"
(
  while true; do
    DATE=$(date +"%T")
    SYS_INFO=$(ps -A -o %cpu,%mem,comm | grep -E "uvicorn|postgres|python" | awk '{cpu+=$1; mem+=$2} END {printf "CPU: %.1f%% | Mem: %.1f%%", cpu, mem}')
    echo "[$DATE] $SYS_INFO" >> "$SYS_MONITOR_LOG"
    sleep 2
  done
) &
SYS_PID=$!

echo "Launching Locust login stress: 300 users @ 50/sec for 45s..."
./venv/bin/locust \
  -f load_tests/locustfile_login_stress.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 300 \
  --spawn-rate 50 \
  --run-time 45s \
  --csv="${OUTPUT_DIR}/stats" \
  --html="${OUTPUT_DIR}/report.html" || true

kill -9 $MON_PID $SYS_PID 2>/dev/null || true

echo "Checking for QueuePool timeouts or 500 errors in server log..."
grep -E "500 Internal Server Error|QueuePool|TimeoutError" "$SERVER_LOG" || echo "No 500 errors or QueuePool timeouts detected!"

echo "Targeted Login Stress Test Complete!"

