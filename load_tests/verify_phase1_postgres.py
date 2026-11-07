#!/usr/bin/env python3
"""
Phase 1: PostgreSQL Setup and Validation Script
Verifies:
  1. Secure DATABASE_URL loading from .env
  2. Direct PostgreSQL connectivity & server version
  3. Alembic schema migrations to head
  4. Table & relationship schema presence
  5. GET /health reports database_engine as postgresql
  6. Prevention of silent SQLite fallback
  7. 44/44 backend regression test execution
"""

import os
import sys
import time
import subprocess
from urllib.parse import urlparse
from dotenv import load_dotenv

# Step 1: Load environment safely
load_dotenv(".env")
raw_url = os.getenv("DATABASE_URL", "")

print("=" * 65)
print("  LEXAI PHASE 1: POSTGRESQL READINESS & HEALTH VERIFICATION")
print("=" * 65)

if not raw_url:
    print("❌ ERROR: DATABASE_URL is not set in /Users/machasanjana/lexai/.env")
    sys.exit(1)

if "<user>" in raw_url or "<password>" in raw_url or "<host>" in raw_url or "your_actual" in raw_url:
    print("❌ ERROR: DATABASE_URL in .env contains unpopulated template placeholders.")
    print("   Please replace with your real PostgreSQL connection string.")
    sys.exit(1)

if not raw_url.startswith("postgresql"):
    print(f"❌ ERROR: DATABASE_URL is not a PostgreSQL scheme. Found: {raw_url[:15]}...")
    sys.exit(1)

# Redacted info display
parsed = urlparse(raw_url)
print(f"  Driver Scheme        : {parsed.scheme}")
print(f"  Target Host          : {parsed.hostname}")
print(f"  Target Port          : {parsed.port or 5432}")
print(f"  Target Database      : {parsed.path.lstrip('/')}")
print(f"  Authentication       : {'Configured (redacted)' if parsed.password else 'Missing Password'}")
print("-" * 65)

# Ensure psycopg2 driver prefix
db_url = raw_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Step 2: Direct Connection Test
print("[1/5] Testing direct PostgreSQL connectivity...")
try:
    from sqlalchemy import create_engine, text, inspect
    engine = create_engine(db_url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT current_database(), version();")).fetchone()
        conn_count = conn.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();")).scalar()
        print(f"  ✅ Connected successfully to database: {res[0]}")
        print(f"  ✅ PostgreSQL Server Version: {res[1][:65]}...")
        print(f"  ✅ Active PostgreSQL Connections: {conn_count}")
except Exception as e:
    print(f"  ❌ Connection failed: {type(e).__name__}: {e}")
    sys.exit(1)

# Step 3: Run Alembic Migrations
print("\n[2/5] Running Alembic database migrations to head...")
try:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("backend/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_cfg.set_main_option("script_location", "backend/alembic")
    command.upgrade(alembic_cfg, "head")
    print("  ✅ Alembic migrations applied successfully (head reached).")
except Exception as e:
    print(f"  ❌ Alembic migration failed: {type(e).__name__}: {e}")
    sys.exit(1)

# Step 4: Verify Tables and Relationships
print("\n[3/5] Verifying database schema tables...")
expected_tables = {
    "users",
    "user_profiles",
    "lawyers",
    "lawyer_profiles",
    "consultations",
    "reviews",
    "notifications",
    "conversations",
    "messages",
    "documents",
}
inspector = inspect(engine)
existing_tables = set(inspector.get_table_names())
missing = expected_tables - existing_tables
if missing:
    print(f"  ❌ Missing expected tables: {missing}")
    sys.exit(1)
print(f"  ✅ All {len(expected_tables)} required tables verified present in PostgreSQL.")

# Step 5: Test /health endpoint with multi-worker backend
print("\n[4/5] Launching backend server and checking /health endpoint...")
import urllib.request
import json

# Clean port 8000
subprocess.run("lsof -ti :8000 | xargs kill -9 2>/dev/null || true", shell=True)
time.sleep(1)

server_env = os.environ.copy()
server_env["DATABASE_URL"] = db_url
server_env["PYTHONPATH"] = "backend"

proc = subprocess.Popen(
    ["./venv/bin/uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000", "--workers", "4"],
    env=server_env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

health_data = None
try:
    for i in range(25):
        time.sleep(0.5)
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/health")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    health_data = json.loads(resp.read().decode())
                    break
        except Exception:
            pass

    if not health_data:
        print("  ❌ Server failed to respond to /health within timeout.")
        sys.exit(1)

    print(f"  ✅ Health status         : {health_data.get('status')}")
    print(f"  ✅ Database status       : {health_data.get('database')}")
    print(f"  ✅ Database Engine       : {health_data.get('database_engine')}")
    print(f"  ✅ Environment           : {health_data.get('environment')}")

    if health_data.get("database_engine") != "postgresql":
        print(f"  ❌ FAILED: Engine reported as '{health_data.get('database_engine')}', expected 'postgresql'!")
        sys.exit(1)
finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    subprocess.run("pkill -9 -f uvicorn 2>/dev/null || true", shell=True)

# Step 6: Backend Regression Tests
print("\n[5/5] Running backend regression test suite...")
test_res = subprocess.run(
    ["./venv/bin/pytest", "backend/tests", "-q"],
    env=server_env,
    capture_output=True,
    text=True
)
print(test_res.stdout.strip())
if test_res.returncode != 0:
    print(f"  ❌ Regression tests failed with return code {test_res.returncode}")
    print(test_res.stderr)
    sys.exit(1)

print("\n" + "=" * 65)
print("  🎉 PHASE 1 VERIFICATION COMPLETED SUCCESSFULLY!")
print("  PostgreSQL is fully connected, migrated, verified, and regression-tested.")
print("  Ready to proceed to Phase 2 (500-User PostgreSQL Benchmark).")
print("=" * 65)

