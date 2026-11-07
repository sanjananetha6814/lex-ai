#!/usr/bin/env bash
set -e

mkdir -p results

echo "================================================================="
echo "  LEXAI 500-USER POSTGRESQL SCALABILITY EXPERIMENT"
echo "  Configuration: 4 Uvicorn Workers + PostgreSQL"
echo "================================================================="

# Load from .env or backend/.env if present and DATABASE_URL is not already set in environment
if [ -z "$DATABASE_URL" ] && [ -f .env ]; then
  echo "Loading environment variables from .env..."
  set -a
  source .env
  set +a
fi
if [ -z "$DATABASE_URL" ] && [ -f backend/.env ]; then
  echo "Loading environment variables from backend/.env..."
  set -a
  source backend/.env
  set +a
fi

# Strict validation: DATABASE_URL must be provided and must target PostgreSQL
if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set."
  echo "A live PostgreSQL connection string is required to run this benchmark."
  echo "Example:"
  echo "  export DATABASE_URL=\"postgresql+psycopg2://user:pass@host:5432/lexai?sslmode=require\""
  exit 1
fi

if [[ "$DATABASE_URL" != postgresql* ]]; then
  echo "ERROR: DATABASE_URL is not a PostgreSQL URL (found: ${DATABASE_URL:0:15}...)"
  echo "Silent SQLite fallback is strictly prohibited."
  exit 1
fi

echo "Verifying PostgreSQL direct connectivity and schema migrations..."
./venv/bin/python -c "
import os, sys
from sqlalchemy import create_engine, text

db_url = os.environ['DATABASE_URL']
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

try:
    engine = create_engine(db_url, connect_args={'connect_timeout': 10})
    with engine.connect() as conn:
        res = conn.execute(text('SELECT current_database(), version();')).fetchone()
        print(f'Connected successfully to PostgreSQL database: {res[0]}')
        print(f'PostgreSQL Version: {res[1][:60]}...')
        
        # Check active connections
        conn_count = conn.execute(text('SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();')).scalar()
        print(f'Initial active PostgreSQL connections: {conn_count}')
except Exception as e:
    print(f'ERROR connecting to PostgreSQL: {e}', file=sys.stderr)
    sys.exit(1)
"

# Results prefix and log paths
RESULT_PREFIX="${RESULT_PREFIX:-results/500_users_4w_postgres_250conn}"
SERVER_LOG="${RESULT_PREFIX}_server.log"
CONN_MONITOR_LOG="${RESULT_PREFIX}_conn_monitor.log"
echo "Targeting output prefix: ${RESULT_PREFIX}"

# Clean any existing listeners on port 8000
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start backend server in background with 4 Uvicorn workers
WORKERS="${UVICORN_WORKERS:-4}"
echo "Starting LexAI backend with ${WORKERS} Uvicorn workers connected to PostgreSQL..."
DATABASE_URL="$DATABASE_URL" PYTHONPATH=backend ./venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers "${WORKERS}" > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

# Ensure cleanup of backend and all child worker processes on script completion or interrupt
trap "kill -9 \$MONITOR_PID 2>/dev/null || true; pkill -P \$SERVER_PID 2>/dev/null || true; kill -9 \$SERVER_PID 2>/dev/null || true" EXIT INT TERM

# Wait for health check
echo "Waiting for LexAI backend /health endpoint..."
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
  echo "ERROR: Backend failed to start within timeout. Server log:"
  cat "$SERVER_LOG"
  exit 1
fi

# Pre-flight assertions
DB_STATUS=$(echo "$RES" | python3 -c 'import sys, json; data=json.load(sys.stdin); print(data.get("database"))')
DB_ENGINE=$(echo "$RES" | python3 -c 'import sys, json; data=json.load(sys.stdin); print(data.get("database_engine"))')
WORKER_COUNT=$(grep -c "Started server process" "$SERVER_LOG" || true)

echo "-----------------------------------------------------------------"
echo "  PRE-FLIGHT VALIDATION:"
echo "    Healthcheck Response   : ${RES}"
echo "    Database Status        : ${DB_STATUS}"
echo "    Database Engine        : ${DB_ENGINE} (MUST be postgresql)"
echo "    Active Worker Processes: ${WORKER_COUNT} (Expected: ${WORKERS})"
echo "-----------------------------------------------------------------"

if [ "$DB_STATUS" != "connected" ]; then
  echo "ERROR: Database status is not 'connected'. Aborting."
  exit 1
fi

if [ "$DB_ENGINE" != "postgresql" ]; then
  echo "ERROR: Database engine is '${DB_ENGINE}', expected 'postgresql'. SQLite fallback blocked. Aborting."
  exit 1
fi

if [ "$WORKER_COUNT" -ne "$WORKERS" ]; then
  echo "ERROR: Expected ${WORKERS} worker processes, found ${WORKER_COUNT}. Aborting."
  exit 1
fi

# Step 6: Short preflight Locust test
echo "Running short preflight Locust verification (5 users for 10s)..."
./venv/bin/locust \
  -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 5 \
  --spawn-rate 5 \
  --run-time 10s \
  --csv=results/preflight_postgres \
  --html=results/preflight_postgres.html

# Step 7: Confirm backend health before launching full benchmark
POST_PREFLIGHT_HEALTH=$(curl -s http://127.0.0.1:8000/health || true)
if ! echo "$POST_PREFLIGHT_HEALTH" | grep -q '"status":"healthy"'; then
  echo "ERROR: Backend became unhealthy after preflight check! Response: $POST_PREFLIGHT_HEALTH"
  exit 1
fi
echo "Backend confirmed healthy after preflight check: $POST_PREFLIGHT_HEALTH"

# Start background PostgreSQL connection monitor
echo "Starting PostgreSQL connection telemetry monitor..."
> "$CONN_MONITOR_LOG"
(
  while true; do
    DATE=$(date +"%T")
    CONN_STATS=$(./venv/bin/python -c "
import os
from sqlalchemy import create_engine, text
try:
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as conn:
        res = conn.execute(text(\"SELECT count(*) total, count(*) filter (where state = 'active') active, count(*) filter (where state = 'idle') idle FROM pg_stat_activity WHERE datname = 'lexai';\")).fetchone()
        print(f'Total: {res[0]} | Active: {res[1]} | Idle: {res[2]}')
except Exception as e:
    print(f'Error: {e}')
" 2>/dev/null || true)
    echo "[$DATE] DB Connections -> $CONN_STATS" >> "$CONN_MONITOR_LOG"
    sleep 3
  done
) &
MONITOR_PID=$!

echo "Starting 500-user uninterrupted Locust run for 3 minutes against PostgreSQL..."
./venv/bin/locust \
  -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 500 \
  --spawn-rate 50 \
  --run-time 3m \
  --csv="${RESULT_PREFIX}" \
  --html="${RESULT_PREFIX}.html"

kill -9 $MONITOR_PID 2>/dev/null || true

echo "Checking final PostgreSQL connection count..."
./venv/bin/python -c "
import os
from sqlalchemy import create_engine, text
db_url = os.environ['DATABASE_URL']
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        count = conn.execute(text('SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();')).scalar()
        print(f'Post-test active PostgreSQL connections: {count}')
except Exception as e:
    print(f'Could not query connection count: {e}')
"

echo "================================================================="
echo "  PostgreSQL 500-user load test run complete!"
echo "================================================================="

