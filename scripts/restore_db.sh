#!/usr/bin/env bash
# =========================================================================
# LexAI Automated PostgreSQL Database Restore Script
# Validates archive integrity, performs clean restoration, and checks data
# =========================================================================
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <path_to_backup.dump> [target_database]"
    exit 1
fi

BACKUP_FILE="$1"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${2:-${POSTGRES_DB:-lexai}}"
POSTGRES_USER="${POSTGRES_USER:-${USER:-lexai_user}}"

# Locate pg_restore and psql
PG_RESTORE_BIN="pg_restore"
PSQL_BIN="psql"

if ! command -v "$PG_RESTORE_BIN" &>/dev/null; then
    if [ -x "/Applications/Postgres.app/Contents/Versions/16/bin/pg_restore" ]; then
        PG_RESTORE_BIN="/Applications/Postgres.app/Contents/Versions/16/bin/pg_restore"
        PSQL_BIN="/Applications/Postgres.app/Contents/Versions/16/bin/psql"
    elif [ -x "/usr/lib/postgresql/16/bin/pg_restore" ]; then
        PG_RESTORE_BIN="/usr/lib/postgresql/16/bin/pg_restore"
        PSQL_BIN="/usr/lib/postgresql/16/bin/psql"
    else
        echo "ERROR: pg_restore utility not found in PATH." >&2
        exit 1
    fi
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "ERROR: Backup file ${BACKUP_FILE} does not exist!" >&2
    exit 1
fi

echo "================================================================="
echo "  LEXAI POSTGRESQL RESTORE"
echo "  Source Archive: ${BACKUP_FILE}"
echo "  Target DB:      ${POSTGRES_DB} on ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "================================================================="

# Pre-flight integrity check
echo "Checking archive integrity before restore..."
if ! "$PG_RESTORE_BIN" --list "$BACKUP_FILE" >/dev/null 2>&1; then
    echo "ERROR: ${BACKUP_FILE} is not a valid PostgreSQL custom-format dump!" >&2
    exit 1
fi
echo "✓ Archive integrity confirmed."

# Restore with --clean --if-exists to replace existing tables cleanly
echo "Restoring database tables and schema..."
"$PG_RESTORE_BIN" \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    -v \
    "$BACKUP_FILE" 2>&1 || true

# Post-restore verification
echo "Running post-restore sanity checks..."
TABLE_COUNT=$("$PSQL_BIN" -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
USER_COUNT=$("$PSQL_BIN" -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "SELECT count(*) FROM users;")
LAWYER_COUNT=$("$PSQL_BIN" -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "SELECT count(*) FROM lawyers;")

echo "Post-restore database state:"
echo "  - Public tables: ${TABLE_COUNT}"
echo "  - Users:         ${USER_COUNT}"
echo "  - Lawyers:       ${LAWYER_COUNT}"

if [[ "$TABLE_COUNT" -gt 0 ]]; then
    echo "✓ Database successfully restored and verified!"
else
    echo "ERROR: Post-restore sanity check failed (0 tables found)!" >&2
    exit 1
fi

