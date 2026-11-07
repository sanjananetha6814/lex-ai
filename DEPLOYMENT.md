# LexAI Production Deployment Guide

This document provides the definitive guide, architectural specification, operational runbooks, and step-by-step checklist for deploying the LexAI legal knowledge and consultation platform to production.

---

## 1. Production Architecture Overview

The LexAI production architecture is engineered for high throughput, sub-100ms response times, and defense-in-depth security supporting 1,000+ concurrent users with zero HTTP 500 errors.

```
                    Internet (HTTPS / Port 443)
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │         Nginx Edge Reverse Proxy             │
         │  - SSL Termination (TLS 1.2 / TLS 1.3)       │
         │  - HTTP -> HTTPS 301 Permanent Redirection   │
         │  - Auth Rate Limiting (limit_req: 5 req/min) │
         │  - Strict Headers (HSTS, CSP, Sniff, Frame)  │
         │  - ACME Webroot Mount (/var/www/certbot)     │
         └──────────────────────┬───────────────────────┘
                                │ Internal Docker Network (lexai-net)
                                ▼
         ┌──────────────────────────────────────────────┐
         │        FastAPI API (4 Uvicorn Workers)       │
         │  - Non-Root Execution (User: lexai UID 1001) │
         │  - Port 8000 (Internal Only, Loopback Bind)  │
         │  - Restricted --forwarded-allow-ips          │
         │  - Distributed Redis-backed Rate Limiter     │
         │  - Short-lived Sessions for Auth             │
         │  - Timing-safe Argon2id Verification         │
         └──────────────┬────────────────┬──────────────┘
                        │                │
            SQL Queries │                │ Caching & Sync
            (Port 6432) │                │ (Port 6379, Authenticated)
                        ▼                ▼
         ┌──────────────────────┐ ┌──────────────────────┐
         │      PgBouncer       │ │    Redis Cluster     │
         │  - Transaction Mode  │ │  - Password Protected│
         │  - 1,000 Client Conn │ │  - Shared Cache & LRU│
         │  - 75 Server Conn    │ │  - Distributed Limits│
         └──────────┬───────────┘ └──────────────────────┘
                    │ Direct Server Conn
                    ▼
         ┌──────────────────────┐
         │    PostgreSQL 16     │
         │  - Port 5432 Internal│
         │  - 250 Max Conns     │
         │  - Persistent Volume │
         └──────────────────────┘
```

### Security Guardrails
1. **Zero Unintended Public Ports:** Only Nginx binds public host ports `80` and `443`. PostgreSQL (`5432`), PgBouncer (`6432`), Redis (`6379`), and Uvicorn (`8000`) are accessible strictly through the internal container network (`lexai-net`) or local loopback (`127.0.0.1`).
2. **Restricted Forwarded-Header Trust:** Uvicorn strictly limits `--forwarded-allow-ips` to the reverse proxy subnet (`127.0.0.1,172.16.0.0/12,10.0.0.0/8`). Client-supplied spoofed headers are ignored.
3. **Non-Root Execution:** The FastAPI container runs under unprivileged user `lexai` (UID 1001, GID 1001) to mitigate container escape risks.
4. **Defense-in-Depth Authentication Rate Limiting:**
   - **Ingress Layer (Nginx):** Drops abusive login bursts with `limit_req zone=auth_login_limit burst=3 nodelay; limit_req_status 429;`.
   - **Application Layer (FastAPI + Redis):** Synchronizes sliding-window rate limit counters across all four Uvicorn workers, returning HTTP 429 with standard JSON and `Retry-After: 60`.
   - **Zero User Enumeration:** Existent and non-existent accounts receive identical timing and identical 401/429 responses.
5. **Database Migration Isolation:** Alembic migrations connect directly to PostgreSQL on port 5432 (bypassing PgBouncer) during pre-deployment to prevent transaction-pooling DDL locking issues.

---

## 2. Secrets Management & Environment Configuration

### Generation Commands
Before starting the containers, generate cryptographically secure production secrets:

```bash
# 1. Generate 64-character hex JWT secret key (minimum 32 characters required)
openssl rand -hex 32

# 2. Generate hexadecimal password for PostgreSQL (avoids URL-encoding errors)
openssl rand -hex 24

# 3. Generate hexadecimal password for Redis
openssl rand -hex 24
```

> [!IMPORTANT]
> **URL-Encoding Database Passwords:** Always use hexadecimal format (`openssl rand -hex 24`) for passwords. Characters such as `@`, `:`, `/`, or `?` will break standard connection string parsing in `DATABASE_URL=postgresql://user:pass@host/db`. If special characters are present, they must be URL-encoded using `urllib.parse.quote_plus()`.

### Environment Configuration (.env)
Create the production `.env` file from the provided template:

```bash
cp .env.production.example .env
chmod 600 .env
```

Ensure the following variables are configured in `.env`:

```ini
ENVIRONMENT=production
PROJECT_NAME="LexAI Production API"
VERSION="1.0.0"

# Cryptographic Keys (Must be >= 32 characters)
SECRET_KEY="<GENERATED_OPENSSL_HEX_32_SECRET>"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Initial Production Administrator
INITIAL_ADMIN_EMAIL="admin@lexai.internal"
INITIAL_ADMIN_PASSWORD="<GENERATED_ADMIN_PASSWORD_OR_LEAVE_BLANK_TO_AUTOGENERATE>"
INITIAL_ADMIN_NAME="LexAI Chief Administrator"

# Network & Proxy Security
FORWARDED_ALLOW_IPS="127.0.0.1,172.16.0.0/12,10.0.0.0/8"
AUTH_RATE_LIMIT_LOGIN=10

# PostgreSQL Credentials
POSTGRES_DB=lexai
POSTGRES_USER=lexai_user
POSTGRES_PASSWORD="<GENERATED_HEX_POSTGRES_PASSWORD>"

# Database URLs
DATABASE_URL=postgresql+psycopg2://lexai_user:<GENERATED_HEX_POSTGRES_PASSWORD>@pgbouncer:6432/lexai
MIGRATION_DATABASE_URL=postgresql+psycopg2://lexai_user:<GENERATED_HEX_POSTGRES_PASSWORD>@db:5432/lexai

# Connection Pool Sizing
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# Distributed Redis Cache (Password Protected)
REDIS_PASSWORD="<GENERATED_HEX_REDIS_PASSWORD>"
REDIS_URL=redis://:<GENERATED_HEX_REDIS_PASSWORD>@redis:6379/0

# Strict CORS Whitelist (JSON array, wildcards strictly prohibited)
CORS_ORIGINS='["https://lex-ai-rust-five.vercel.app"]'

# OpenAI API Configuration
OPENAI_API_KEY="sk-proj-<YOUR_PRODUCTION_OPENAI_KEY>"
OPENAI_MODEL="gpt-4o-mini"
OPENAI_EMBEDDING_MODEL="text-embedding-3-small"

# Storage
UPLOAD_DIR="/app/uploads"
MAX_UPLOAD_SIZE=20971520
```

---

## 3. SSL / TLS Certificate Setup & Renewal

### Staging / Local Validation (Self-Signed)
For pre-production testing:

```bash
chmod +x nginx/generate_ssl_certs.sh
./nginx/generate_ssl_certs.sh
```

### Production Validation (Let's Encrypt / Certbot)
On your cloud Linux host (Ubuntu/Debian):

```bash
# 1. Install certbot on the host
sudo apt-get update && sudo apt-get install -y certbot

# 2. Start Nginx container to serve port 80 ACME challenge
docker compose up -d nginx

# 3. Obtain certificate via webroot (mounted into /var/www/certbot)
sudo certbot certonly --webroot -w /var/www/certbot \
  -d api.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos --no-eff-email

# 4. Copy certificates into nginx/ssl (Avoid broken host symlinks inside Docker)
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem nginx/ssl/lexai.crt
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem nginx/ssl/lexai.key
sudo chmod 644 nginx/ssl/lexai.crt
sudo chmod 600 nginx/ssl/lexai.key

# 5. Reload Nginx
docker compose exec nginx nginx -s reload
```

### Automated Renewal
The stack includes a companion `lexai-certbot` container that attempts automated renewal every 12 hours. Alternatively, configure a host cron job:

```bash
# Add to host crontab (crontab -e):
0 2 * * * /opt/lexai/scripts/renew_ssl.sh >> /var/log/lexai_ssl_renewal.log 2>&1
```

---

## 4. Step-by-Step Production Deployment Checklist

### Step 1: Pre-flight Verification
Run local regressions to verify code integrity before deployment:

```bash
# 1. Run all backend tests (must report all passed)
./venv/bin/pytest backend/tests -v

# 2. Run frontend typecheck, linter, and production build
cd frontend
npm run typecheck
npm run lint
npm run build
cd ..
```

### Step 2: Database Migration & Production Initialization
Apply pending schema migrations and initialize admin/advocate baseline data:

```bash
# 1. Apply schema migrations (direct to PostgreSQL port 5432)
docker compose run --rm api alembic upgrade head

# 2. Seed production admin user and baseline verified lawyers
docker compose run --rm api python -m scripts.seed_production
```

### Step 3: Launch Production Infrastructure
Launch all services in detached mode:

```bash
# Build and start services
docker compose up -d --build
```

Verify service statuses:

```bash
docker compose ps
```

All services (`lexai-postgres`, `lexai-pgbouncer`, `lexai-redis`, `lexai-api`, `lexai-nginx`, `lexai-certbot`) must display status `healthy` or `Up`.

### Step 4: Health Check & Verification Smoke Tests
Execute the automated smoke verification:

```bash
# 1. Verify HTTP -> HTTPS 301 Redirection
curl -I http://localhost/health
# Expected: HTTP/1.1 301 Moved Permanently -> Location: https://localhost/health

# 2. Verify HTTPS Healthcheck Endpoint
curl -k https://localhost/health
# Expected: {"status":"healthy","database":"connected","database_engine":"postgresql","cache":"redis_connected","environment":"production","version":"1.0.0"}

# 3. Verify Operational Metrics Endpoint
curl -k https://localhost/metrics

# 4. Verify Rate Limiting on Login
for i in {1..12}; do
  curl -k -s -o /dev/null -w "Attempt $i: HTTP %{http_code}\n" \
    -X POST https://localhost/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"probe@example.com","password":"WrongPassword!"}'
done
# Expected: Attempts 1-5 return 401; subsequent attempts return 429 Too Many Requests

# 5. Verify Full Real User Journeys
docker compose run --rm -e API_BASE_URL=http://api:8000 api \
  python /app/staging/verify_full_user_journeys.py
```

---

## 5. Backup, Restore, and Disaster Recovery

### Automated Database Backup
Run the backup script (compressed custom-format dump with integrity verification and 30-day retention):

```bash
# Manual backup execution
./scripts/backup_db.sh

# Recommended host cron job for daily automated backup (crontab -e):
0 3 * * * /opt/lexai/scripts/backup_db.sh >> /var/log/lexai_backup.log 2>&1
```

### Database Restoration Runbook
To restore the database from a verified dump file:

```bash
# Syntax: ./scripts/restore_db.sh <path_to_backup.dump> [target_database]
./scripts/restore_db.sh ./backups/lexai_backup_20261107_124854.dump
```

The script will:
1. Verify archive integrity before touching the database.
2. Drop and recreate schema objects cleanly (`--clean --if-exists`).
3. Restore tables, sequences, indexes, and constraints.
4. Execute sanity checks and report row counts.

### Document Storage Backup
User uploaded documents in `/app/uploads` are stored in Docker volume `uploadsdata`. To create an off-site archive:

```bash
docker run --rm -v uploadsdata:/data -v $(pwd)/backups:/backup alpine \
  tar -czf /backup/uploads_backup_$(date +"%Y%m%d").tar.gz -C /data .
```

---

## 6. Operations & Monitoring

### Viewing Logs
All containers are configured with Docker log rotation (`max-size: 50m`, `max-file: 5`):

```bash
# View aggregated live logs
docker compose logs -f

# View Nginx access & error logs
docker compose logs -f nginx

# View API application & worker logs
docker compose logs -f api
```

### PgBouncer Pool Telemetry
Inspect active pools and connection counts:

```bash
psql -h 127.0.0.1 -p 6432 -U lexai_user -d pgbouncer -c "SHOW POOLS;"
psql -h 127.0.0.1 -p 6432 -U lexai_user -d pgbouncer -c "SHOW CLIENTS;"
psql -h 127.0.0.1 -p 6432 -U lexai_user -d pgbouncer -c "SHOW SERVERS;"
```

### Redis Cache Telemetry
Inspect authenticated cache stats:

```bash
redis-cli -a "$REDIS_PASSWORD" info stats | grep -E "keyspace_hits|keyspace_misses"
redis-cli -a "$REDIS_PASSWORD" info memory | grep "used_memory_human"
```

---

## 7. Rollback Procedures

If an unexpected regression occurs in production:

1. **Service Rollback:**
   ```bash
   git checkout <PREVIOUS_STABLE_COMMIT_OR_TAG>
   docker compose up -d --build
   ```
2. **Database Schema Rollback:**
   ```bash
   docker compose run --rm api alembic downgrade -1
   ```
3. **Cache Purge:**
   ```bash
   docker compose exec redis redis-cli -a "$REDIS_PASSWORD" flushdb
   ```
