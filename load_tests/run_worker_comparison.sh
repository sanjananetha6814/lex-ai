#!/usr/bin/env bash
set -e

# ==============================================================================
# LexAI Worker Configuration Benchmarking (Stage 3)
# Evaluates 4, 6, and 8 Uvicorn Workers under identical load (500 users, 60s)
# ==============================================================================

WORKERS_LIST=(4 6 8)
POOL_SIZES=(25 20 15)
MAX_OVERFLOWS=(25 15 15)

PSQL_BIN="/Applications/Postgres.app/Contents/Versions/16/bin/psql"
if [ ! -x "$PSQL_BIN" ]; then
  PSQL_BIN="psql"
fi

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "================================================================="
echo "  LEXAI WORKER BENCHMARK COMPARISON (4 vs 6 vs 8 Workers)"
echo "  PostgreSQL 16 (max_connections = 250)"
echo "  Workload: 500 concurrent users @ 50 users/sec for 60 seconds"
echo "================================================================="

for i in "${!WORKERS_LIST[@]}"; do
  WORKERS="${WORKERS_LIST[$i]}"
  POOL_SZ="${POOL_SIZES[$i]}"
  MAX_OVF="${MAX_OVERFLOWS[$i]}"
  OUT_DIR="results/worker_bench_${WORKERS}w"
  mkdir -p "$OUT_DIR"

  SERVER_LOG="${OUT_DIR}/server.log"
  CONN_LOG="${OUT_DIR}/conn_monitor.log"
  SYS_LOG="${OUT_DIR}/system_monitor.log"

  echo ""
  echo ">>> Testing ${WORKERS} Workers (pool_size=${POOL_SZ}, max_overflow=${MAX_OVF}, budget=${WORKERS}*$(($POOL_SZ + $MAX_OVF))=$(($WORKERS * ($POOL_SZ + $MAX_OVF)))) <<<"

  # Clean port 8000
  lsof -ti :8000 | xargs kill -9 2>/dev/null || true
  sleep 2

  # Start Uvicorn
  > "$SERVER_LOG"
  DATABASE_URL="$DATABASE_URL" \
  DB_POOL_SIZE="$POOL_SZ" \
  DB_MAX_OVERFLOW="$MAX_OVF" \
  PYTHONPATH=backend \
  ./venv/bin/uvicorn app.main:app \
    --app-dir backend \
    --host 127.0.0.1 \
    --port 8000 \
    --workers "${WORKERS}" > "$SERVER_LOG" 2>&1 &
  SERVER_PID=$!

  # Wait for health
  READY=0
  for attempt in $(seq 1 30); do
    RES=$(curl -s http://127.0.0.1:8000/health || true)
    if echo "$RES" | grep -q '"status":"healthy"'; then
      READY=1
      break
    fi
    sleep 0.5
  done

  if [ $READY -ne 1 ]; then
    echo "ERROR: Backend failed to start with ${WORKERS} workers."
    cat "$SERVER_LOG"
    kill -9 $SERVER_PID 2>/dev/null || true
    exit 1
  fi

  echo "Backend is healthy on 127.0.0.1:8000 with ${WORKERS} workers."

  # Start background monitors
  > "$CONN_LOG"
  (
    while true; do
      DATE=$(date +"%T")
      STATS=$($PSQL_BIN -h localhost -p 5432 -U machasanjana -d lexai -t -A -F"|" -c \
        "SELECT count(*) as total, count(*) filter (where state = 'active') as active, count(*) filter (where state = 'idle') as idle FROM pg_stat_activity WHERE datname = 'lexai';" 2>/dev/null || true)
      TOTAL=$(echo "$STATS" | cut -d'|' -f1)
      ACTIVE=$(echo "$STATS" | cut -d'|' -f2)
      IDLE=$(echo "$STATS" | cut -d'|' -f3)
      echo "[$DATE] Total: ${TOTAL} | Active: ${ACTIVE} | Idle: ${IDLE}" >> "$CONN_LOG"
      sleep 1
    done
  ) &
  MON_PID=$!

  > "$SYS_LOG"
  (
    while true; do
      DATE=$(date +"%T")
      SYS_INFO=$(ps -A -o %cpu,%mem,comm | grep -E "uvicorn|postgres|python" | awk '{cpu+=$1; mem+=$2} END {printf "Proc CPU: %.1f%% | Proc Mem: %.1f%%", cpu, mem}')
      echo "[$DATE] $SYS_INFO" >> "$SYS_LOG"
      sleep 2
    done
  ) &
  SYS_PID=$!

  # Run Locust
  echo "Running 500-user load test for 60s..."
  ./venv/bin/locust \
    -f load_tests/locustfile.py \
    --host http://127.0.0.1:8000 \
    --headless \
    --users 500 \
    --spawn-rate 50 \
    --run-time 60s \
    --csv="${OUT_DIR}/stats" \
    --html="${OUT_DIR}/report.html" > "${OUT_DIR}/locust.log" 2>&1 || true

  # Stop monitors and server
  kill -9 $MON_PID $SYS_PID 2>/dev/null || true
  pkill -P $SERVER_PID 2>/dev/null || true
  kill -9 $SERVER_PID 2>/dev/null || true
  lsof -ti :8000 | xargs kill -9 2>/dev/null || true

  echo "Finished testing ${WORKERS} workers."
  sleep 3
done

echo ""
echo "================================================================="
echo "  All Worker Benchmarks Complete! Analyzing Results..."
echo "================================================================="

