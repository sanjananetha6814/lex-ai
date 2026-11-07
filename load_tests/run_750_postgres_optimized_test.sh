#!/usr/bin/env bash
set -e

OUTPUT_DIR="results/750_users_4w_postgres_250conn_optimized"
mkdir -p "$OUTPUT_DIR"

SERVER_LOG="${OUTPUT_DIR}/server.log"
CONN_MONITOR_LOG="${OUTPUT_DIR}/conn_monitor.log"
SYS_MONITOR_LOG="${OUTPUT_DIR}/system_monitor.log"

echo "================================================================="
echo "  LEXAI 750-USER POSTGRESQL BENCHMARK (PHASE 3, STEP 6 - OPTIMIZED)"
echo "  Configuration: 4 Uvicorn Workers | PostgreSQL 16 (max_conn=250)"
echo "  DB Pool: pool_size=25, max_overflow=25"
echo "  Target: 750 users @ 50 users/sec spawn rate for 3 minutes"
echo "  Output Directory: ${OUTPUT_DIR}"
echo "================================================================="

# Load environment variables
if [ -f .env ]; then
  echo "Loading environment variables from .env..."
  set -a
  source .env
  set +a
fi

export DB_POOL_SIZE=25
export DB_MAX_OVERFLOW=25
export UVICORN_WORKERS=4

echo "Configuration:"
echo "  DATABASE_URL     : ${DATABASE_URL:0:35}..."
echo "  Uvicorn Workers  : ${UVICORN_WORKERS}"
echo "  DB Pool Size     : ${DB_POOL_SIZE}"
echo "  DB Max Overflow  : ${DB_MAX_OVERFLOW}"

if [ -z "$DATABASE_URL" ] || [[ "$DATABASE_URL" != postgresql* ]]; then
  echo "ERROR: DATABASE_URL must be a valid PostgreSQL connection string."
  exit 1
fi

PSQL_BIN="/Applications/Postgres.app/Contents/Versions/16/bin/psql"
if [ ! -x "$PSQL_BIN" ]; then
  PSQL_BIN="psql"
fi

# Step 1: Pre-flight PostgreSQL verification
echo "Checking PostgreSQL connection and max_connections..."
MAX_CONN=$($PSQL_BIN -h localhost -p 5432 -U machasanjana -d lexai -t -A -c "SHOW max_connections;")
echo "PostgreSQL reports max_connections = ${MAX_CONN}"
if [ "$MAX_CONN" -lt 250 ]; then
  echo "ERROR: max_connections is ${MAX_CONN}, expected at least 250."
  exit 1
fi

INITIAL_CONNS=$($PSQL_BIN -h localhost -p 5432 -U machasanjana -d lexai -t -A -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'lexai';")
echo "Initial connections on 'lexai': ${INITIAL_CONNS}"

# Step 2: Clean port 8000
echo "Ensuring port 8000 is clean..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
sleep 1

# Step 3: Start backend server
echo "Starting LexAI backend with ${UVICORN_WORKERS} workers..."
> "$SERVER_LOG"
DATABASE_URL="$DATABASE_URL" \
DB_POOL_SIZE="$DB_POOL_SIZE" \
DB_MAX_OVERFLOW="$DB_MAX_OVERFLOW" \
PYTHONPATH=backend \
./venv/bin/uvicorn app.main:app \
  --app-dir backend \
  --host 127.0.0.1 \
  --port 8000 \
  --workers "${UVICORN_WORKERS}" > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

trap "echo 'Shutting down processes...'; kill -9 \$MON_PID \$SYS_PID 2>/dev/null || true; pkill -P \$SERVER_PID 2>/dev/null || true; kill -9 \$SERVER_PID 2>/dev/null || true" EXIT INT TERM

# Step 4: Health check
echo "Waiting for /health endpoint..."
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

DB_ENGINE=$(echo "$RES" | ./venv/bin/python -c 'import sys, json; data=json.load(sys.stdin); print(data.get("database_engine"))')
DB_STATUS=$(echo "$RES" | ./venv/bin/python -c 'import sys, json; data=json.load(sys.stdin); print(data.get("database"))')
WORKER_COUNT=$(grep -c "Started server process" "$SERVER_LOG" || true)

echo "-----------------------------------------------------------------"
echo "  PRE-FLIGHT VALIDATION:"
echo "    Healthcheck Response   : ${RES}"
echo "    Database Status        : ${DB_STATUS}"
echo "    Database Engine        : ${DB_ENGINE}"
echo "    Active Worker Processes: ${WORKER_COUNT} (Expected: ${UVICORN_WORKERS})"
echo "-----------------------------------------------------------------"

if [ "$DB_STATUS" != "connected" ] || [ "$DB_ENGINE" != "postgresql" ]; then
  echo "ERROR: Invalid database state. Aborting."
  exit 1
fi

# Step 5: Start background monitors
echo "Starting PostgreSQL connection telemetry monitor..."
> "$CONN_MONITOR_LOG"
(
  while true; do
    DATE=$(date +"%T")
    STATS=$($PSQL_BIN -h localhost -p 5432 -U machasanjana -d lexai -t -A -F"|" -c \
      "SELECT count(*) as total, count(*) filter (where state = 'active') as active, count(*) filter (where state = 'idle') as idle, count(*) filter (where wait_event_type is not null) as waiting FROM pg_stat_activity WHERE datname = 'lexai';" 2>/dev/null || true)
    
    TOTAL=$(echo "$STATS" | cut -d'|' -f1)
    ACTIVE=$(echo "$STATS" | cut -d'|' -f2)
    IDLE=$(echo "$STATS" | cut -d'|' -f3)
    WAITING=$(echo "$STATS" | cut -d'|' -f4)
    
    echo "[$DATE] Total: ${TOTAL} | Active: ${ACTIVE} | Idle: ${IDLE} | Waiting: ${WAITING}" >> "$CONN_MONITOR_LOG"
    
    if [ -n "$TOTAL" ] && [ "$TOTAL" -ge 242 ] 2>/dev/null; then
      echo "[$DATE] CRITICAL ALERT: Database connection count reached ${TOTAL} (Limit: 250)!" >> "$CONN_MONITOR_LOG"
    fi
    sleep 2
  done
) &
MON_PID=$!

echo "Starting system resource monitor..."
> "$SYS_MONITOR_LOG"
(
  while true; do
    DATE=$(date +"%T")
    SYS_INFO=$(ps -A -o %cpu,%mem,comm | grep -E "uvicorn|postgres|python" | awk '{cpu+=$1; mem+=$2} END {printf "Proc CPU: %.1f%% | Proc Mem: %.1f%%", cpu, mem}')
    VM_STAT=$(vm_stat | grep "Pages free:" | awk '{print $3}' | tr -d '.')
    echo "[$DATE] $SYS_INFO | Free pages: $VM_STAT" >> "$SYS_MONITOR_LOG"
    sleep 3
  done
) &
SYS_PID=$!

# Step 6: Launch Locust 750-user load test
echo "================================================================="
echo "  Launching Locust: 750 users @ 50 users/sec for 3 minutes..."
echo "================================================================="
./venv/bin/locust \
  -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 750 \
  --spawn-rate 50 \
  --run-time 3m \
  --csv="${OUTPUT_DIR}/stats" \
  --html="${OUTPUT_DIR}/report.html" || true

# Stop monitors
kill -9 $MON_PID $SYS_PID 2>/dev/null || true

echo "Checking final PostgreSQL connection count..."
FINAL_CONNS=$($PSQL_BIN -h localhost -p 5432 -U machasanjana -d lexai -t -A -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'lexai';")
echo "Post-test connections on 'lexai': ${FINAL_CONNS}"

echo "================================================================="
echo "  Optimized 750-User PostgreSQL Benchmark Complete!"
echo "================================================================="

