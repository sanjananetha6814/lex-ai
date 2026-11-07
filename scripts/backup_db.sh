#!/usr/bin/env bash
# =========================================================================
# LexAI Automated PostgreSQL Database Backup Script
# Performs a compressed custom-format dump with integrity validation & retention
# =========================================================================
set -euo pipefail

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-lexai}"
POSTGRES_USER="${POSTGRES_USER:-${USER:-lexai_user}}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Locate pg_dump and pg_restore
PG_DUMP_BIN="pg_dump"
PG_RESTORE_BIN="pg_restore"

if ! command -v "$PG_DUMP_BIN" &>/dev/null; then
    if [ -x "/Applications/Postgres.app/Contents/Versions/16/bin/pg_dump" ]; then
        PG_DUMP_BIN="/Applications/Postgres.app/Contents/Versions/16/bin/pg_dump"
        PG_RESTORE_BIN="/Applications/Postgres.app/Contents/Versions/16/bin/pg_restore"
    elif [ -x "/usr/lib/postgresql/16/bin/pg_dump" ]; then
        PG_DUMP_BIN="/usr/lib/postgresql/16/bin/pg_dump"
        PG_RESTORE_BIN="/usr/lib/postgresql/16/bin/pg_restore"
    else
        echo "ERROR: pg_dump utility not found in PATH." >&2
        exit 1
    fi
fi

mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
BACKUP_FILE="${BACKUP_DIR}/${POSTGRES_DB}_backup_${TIMESTAMP}.dump"
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"

echo "================================================================="
echo "  LEXAI POSTGRESQL BACKUP"
echo "  Database: ${POSTGRES_DB} on ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "  Output:   ${BACKUP_FILE}"
echo "================================================================="

# Execute pg_dump using custom format (-Fc) with built-in compression
echo "Dumping database schema and data..."
"$PG_DUMP_BIN" \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -Fc \
    -v \
    -d "$POSTGRES_DB" \
    -f "$BACKUP_FILE" > "$LOG_FILE" 2>&1

# Verify backup existence and non-zero size
if [[ ! -s "$BACKUP_FILE" ]]; then
    echo "ERROR: Backup file ${BACKUP_FILE} was not created or is empty!" >&2
    exit 1
fi

# Verify archive integrity via pg_restore table of contents listing
echo "Verifying backup archive integrity..."
if ! "$PG_RESTORE_BIN" --list "$BACKUP_FILE" >/dev/null 2>&1; then
    echo "ERROR: Backup verification failed! Archive is corrupted." >&2
    exit 1
fi

FILE_SIZE="$(du -h "$BACKUP_FILE" | cut -f1)"
echo "✓ Backup completed and verified successfully (${FILE_SIZE})"

# Prune old backups exceeding retention policy
echo "Pruning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "${POSTGRES_DB}_backup_*.dump" -type f -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "backup_*.log" -type f -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true

echo "Backup workflow finished cleanly."

