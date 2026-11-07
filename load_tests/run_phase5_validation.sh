#!/usr/bin/env bash
set -e

# ==============================================================================
# Phase 5: Production-Grade Database Connection Architecture Validation
# 750-User & 1,000-User Benchmarks with Read Caching & Auth Session Optimization
# ==============================================================================

WORKERS=${1:-4}
POOL_SIZE=${2:-25}
MAX_OVERFLOW=${3:-25}

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
echo "  LEXAI PHASE 5 BENCHMARK VALIDATION"
echo "  Workers: ${WORKERS} | Pool: ${POOL_SIZE} | Overflow: ${MAX_OVERFLOW}"
echo "  Caching: In-Memory TTL (60s) Active"
echo "  PostgreSQL 16: max_connections = 250"
echo "================================================================="

run_benchmark() {
  local USERS=$1
  local SPAWN_RATE=$2
  local DURATION=$3
  local OUT_DIR=$4

  echo ""
  echo "================================================================="
  echo "  STARTING BENCHMARK: ${USERS} Users @ ${SPAWN_RATE}/s for ${DURATION}"
  echo "  Target Output: ${OUT_DIR}"
  echo "================================================================="

  mkdir -p "$OUT_DIR"
  local SERVER_LOG="${OUT_DIR}/server.log"
  local CONN_LOG="${OUT_DIR}/conn_monitor.log"
  local SYS_LOG="${OUT_DIR}/system_monitor.log"

  # Clean port 8000
  lsof -ti :8000 | xargs kill -9 2>/dev/null || true
  sleep 2

  # Start Uvicorn
  > "$SERVER_LOG"
  DATABASE_URL="$DATABASE_URL" \
  DB_POOL_SIZE="$POOL_SIZE" \
  DB_MAX_OVERFLOW="$MAX_OVERFLOW" \
  PYTHONPATH=backend \
  ./venv/bin/uvicorn app.main:app \
    --app-dir backend \
    --host 127.0.0.1 \
    --port 8000 \
    --workers "${WORKERS}" > "$SERVER_LOG" 2>&1 &
  local SERVER_PID=$!

  # Wait for health
  local READY=0
  for attempt in $(seq 1 30); do
    RES=$(curl -s http://127.0.0.1:8000/health || true)
    if echo "$RES" | grep -q '"status":"healthy"'; then
      READY=1
      break
    fi
    sleep 0.5
  done

  if [ $READY -ne 1 ]; then
    echo "ERROR: Backend failed to start."
    cat "$SERVER_LOG"
    kill -9 $SERVER_PID 2>/dev/null || true
    exit 1
  fi

  echo "Backend is healthy on 127.0.0.1:8000 with ${WORKERS} workers."

  # Start monitors
  > "$CONN_LOG"
  (
    while true; do
      DATE=$(date +"%T")
      STATS=$($PSQL_BIN -h localhost -p 5432 -U machasanjana -d lexai -t -A -F"|" -c \
        "SELECT count(*) as total, count(*) filter (where state = 'active') as active, count(*) filter (where state = 'idle') as idle, count(*) filter (where wait_event_type is not null) as waiting FROM pg_stat_activity WHERE datname = 'lexai';" 2>/dev/null || true)
      TOTAL=$(echo "$STATS" | cut -d'|' -f1)
      ACTIVE=$(echo "$STATS" | cut -d'|' -f2)
      IDLE=$(echo "$STATS" | cut -d'|' -f3)
      WAITING=$(echo "$STATS" | cut -d'|' -f4)
      echo "[$DATE] Total: ${TOTAL} | Active: ${ACTIVE} | Idle: ${IDLE} | Waiting: ${WAITING}" >> "$CONN_LOG"
      if [ -n "$TOTAL" ] && [ "$TOTAL" -ge 242 ] 2>/dev/null; then
        echo "[$DATE] CRITICAL ALERT: Database connection count reached ${TOTAL} (Limit: 250)!" >> "$CONN_LOG"
      fi
      sleep 1
    done
  ) &
  local MON_PID=$!

  > "$SYS_LOG"
  (
    while true; do
      DATE=$(date +"%T")
      SYS_INFO=$(ps -A -o %cpu,%mem,comm | grep -E "uvicorn|postgres|python" | awk '{cpu+=$1; mem+=$2} END {printf "Proc CPU: %.1f%% | Proc Mem: %.1f%%", cpu, mem}')
      VM_STAT=$(vm_stat | grep "Pages free:" | awk '{print $3}' | tr -d '.')
      echo "[$DATE] $SYS_INFO | Free pages: $VM_STAT" >> "$SYS_LOG"
      sleep 2
    done
  ) &
  local SYS_PID=$!

  # Run Locust
  echo "Launching Locust: ${USERS} users @ ${SPAWN_RATE}/s for ${DURATION}..."
  ./venv/bin/locust \
    -f load_tests/locustfile.py \
    --host http://127.0.0.1:8000 \
    --headless \
    --users "${USERS}" \
    --spawn-rate "${SPAWN_RATE}" \
    --run-time "${DURATION}" \
    --csv="${OUT_DIR}/stats" \
    --html="${OUT_DIR}/report.html" > "${OUT_DIR}/locust.log" 2>&1 || true

  # Stop monitors and server
  kill -9 $MON_PID $SYS_PID 2>/dev/null || true
  pkill -P $SERVER_PID 2>/dev/null || true
  kill -9 $SERVER_PID 2>/dev/null || true
  lsof -ti :8000 | xargs kill -9 2>/dev/null || true

  FINAL_CONNS=$($PSQL_BIN -h localhost -p 5432 -U machasanjana -d lexai -t -A -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'lexai';")
  echo "Post-test connections on 'lexai': ${FINAL_CONNS}"
  echo "Benchmark ${USERS} users completed. Results in ${OUT_DIR}"
  sleep 3
}

# Execute 750 users (3 minutes)
run_benchmark 750 50 3m "results/750_users_phase5_cached"

# Execute 1,000 users (40s ramp + 3m sustained = 220s)
run_benchmark 1000 25 220s "results/1000_users_phase5_cached"

echo "================================================================="
echo "  All Phase 5 Validation Benchmarks Complete!"
echo "================================================================="

