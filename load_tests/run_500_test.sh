#!/usr/bin/env bash
set -e

WORKERS="${UVICORN_WORKERS:-4}"
mkdir -p results

echo "================================================================="
echo "  LEXAI 500-USER SCALABILITY EXPERIMENT"
echo "  Configuration: ${WORKERS} Uvicorn Workers + SQLite (WAL Mode)"
echo "================================================================="

# Clean any existing listeners on port 8000
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start backend server in background with multi-worker configuration
PYTHONPATH=backend ./venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers "${WORKERS}" > results/500_users_server.log 2>&1 &
SERVER_PID=$!

# Ensure cleanup of backend and all child worker processes on script completion or interrupt
trap "pkill -P $SERVER_PID 2>/dev/null || true; kill -9 $SERVER_PID 2>/dev/null || true" EXIT INT TERM

# Wait for health check
echo "Waiting for LexAI backend to become ready..."
READY=0
for i in $(seq 1 30); do
  RES=$(curl -s http://127.0.0.1:8000/health || true)
  if echo "$RES" | grep -q '"status":"healthy"'; then
    echo "Healthcheck response: $RES"
    READY=1
    break
  fi
  sleep 0.5
done

if [ $READY -ne 1 ]; then
  echo "ERROR: Backend failed to start within timeout. Server log:"
  cat results/500_users_server.log
  exit 1
fi

# Pre-flight assertions
DB_STATUS=$(echo "$RES" | python3 -c 'import sys, json; data=json.load(sys.stdin); print(data.get("database"))')
DB_ENGINE=$(echo "$RES" | python3 -c 'import sys, json; data=json.load(sys.stdin); print(data.get("database_engine"))')
WORKER_COUNT=$(grep -c "Started server process" results/500_users_server.log || true)

echo "-----------------------------------------------------------------"
echo "  PRE-FLIGHT VALIDATION:"
echo "    Database Status       : ${DB_STATUS}"
echo "    Database Engine       : ${DB_ENGINE}"
echo "    Active Worker Processes: ${WORKER_COUNT} (Expected: ${WORKERS})"
echo "-----------------------------------------------------------------"

if [ "$DB_STATUS" != "connected" ] || [ "$DB_ENGINE" != "sqlite" ] || [ "$WORKER_COUNT" -ne "$WORKERS" ]; then
  echo "ERROR: Pre-flight check failed! Aborting load test."
  exit 1
fi

echo "Starting 500-user uninterrupted Locust run for 3 minutes..."
./venv/bin/locust \
  -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 500 \
  --spawn-rate 50 \
  --run-time 3m \
  --csv=results/500_users_4w_wal \
  --html=results/500_users_4w_wal.html

echo "================================================================="
echo "  500-user load test run complete!"
echo "================================================================="

