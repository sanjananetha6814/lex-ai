# LexAI Production Deployment Guide

This document provides the definitive guide, architectural specification, and step-by-step operational checklist for deploying the LexAI legal knowledge and consultation platform to production.

---

## 1. Production Architecture Overview

The LexAI production architecture is engineered for high throughput, low latency, and defense-in-depth security supporting 1,000+ concurrent users with zero HTTP 500 errors and sub-100ms p95 response times.

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
         └──────────────────────┬───────────────────────┘
                                │ Internal Docker Network (lexai-net)
                                ▼
         ┌──────────────────────────────────────────────┐
         │        FastAPI API (4 Uvicorn Workers)       │
         │  - Port 8000 (Internal Only, Unexposed)      │
         │  - Restricted --forwarded-allow-ips          │
         │  - Distributed Redis-backed Rate Limiter     │
         │  - Short-lived Sessions for Auth             │
         │  - Timing-safe Argon2id Verification         │
         └──────────────┬────────────────┬──────────────┘
                        │                │
            SQL Queries │                │ Caching & Sync
            (Port 6432) │                │ (Port 6379)
                        ▼                ▼
         ┌──────────────────────┐ ┌──────────────────────┐
         │      PgBouncer       │ │    Redis Cluster     │
         │  - Transaction Mode  │ │  - Shared Cache      │
         │  - 1,000 Client Conn │ │  - Cross-worker Inval│
         │  - 75 Server Conn    │ │  - Distributed Limiter
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
1. **Zero Unintended Public Ports:** Only Nginx binds public host ports `80` and `443`. PostgreSQL (`5432`), PgBouncer (`6432`), Redis (`6379`), and Uvicorn (`8000`) are accessible strictly through the internal container network (`lexai-net`) or loopback (`127.0.0.1`).
2. **Restricted Forwarded-Header Trust:** Uvicorn strictly limits `--forwarded-allow-ips` to the reverse proxy subnet (`127.0.0.1,172.16.0.0/12,10.0.0.0/8`). Client-supplied spoofed headers are ignored.
3. **Defense-in-Depth Authentication Rate Limiting:**
   - **Ingress Layer (Nginx):** Drops abusive login bursts with `limit_req zone=auth_login_limit burst=3 nodelay; limit_req_status 429;`.
   - **Application Layer (FastAPI + Redis):** Synchronizes sliding-window rate limit counters across all four Uvicorn workers, returning HTTP 429 with standard JSON and `Retry-After: 60`.
   - **Zero User Enumeration:** Existent and non-existent accounts receive identical timing and identical 401/429 responses.
4. **Database Migration Isolation:** Alembic migrations connect directly to PostgreSQL on port 5432 (bypassing PgBouncer) during pre-deployment to prevent transaction-pooling DDL locking issues.

---

## 2. Secrets Management & Environment Configuration

### Generation Commands
Before starting the containers, generate cryptographically secure production secrets:

```bash
# 1. Generate 64-character hex JWT secret key (minimum 32 characters required)
openssl rand -hex 32

# 2. Generate strong random PostgreSQL password
openssl rand -base64 24
```

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
SECRET_KEY="<GENERATED_OPENSSL_SECRET_KEY>"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Network & Proxy Security
FORWARDED_ALLOW_IPS="127.0.0.1,172.16.0.0/12,10.0.0.0/8"
AUTH_RATE_LIMIT_LOGIN=10

# PostgreSQL Credentials
POSTGRES_DB=lexai
POSTGRES_USER=lexai_user
POSTGRES_PASSWORD="<GENERATED_POSTGRES_PASSWORD>"

# Database URLs
DATABASE_URL=postgresql+psycopg2://lexai_user:<GENERATED_POSTGRES_PASSWORD>@pgbouncer:6432/lexai
MIGRATION_DATABASE_URL=postgresql+psycopg2://lexai_user:<GENERATED_POSTGRES_PASSWORD>@db:5432/lexai

# Connection Pool Sizing
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# Distributed Redis Cache
REDIS_URL=redis://redis:6379/0

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

## 3. SSL / TLS Certificate Setup

### Staging / Local Validation (Self-Signed)
For pre-production testing:

```bash
chmod +x nginx/generate_ssl_certs.sh
./nginx/generate_ssl_certs.sh
```

### Production Validation (Let's Encrypt / Certbot)
On your cloud Linux host (Ubuntu/Debian):

```bash
# 1. Install certbot
sudo apt-get update && sudo apt-get install -y certbot

# 2. Obtain certificate via webroot (with Nginx running port 80)
sudo certbot certonly --webroot -w /var/www/certbot \
  -d api.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos --no-eff-email

# 3. Symlink certificates into nginx/ssl
ln -sf /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem nginx/ssl/lexai.crt
ln -sf /etc/letsencrypt/live/api.yourdomain.com/privkey.pem nginx/ssl/lexai.key
```

---

## 4. Step-by-Step Production Deployment Checklist

### Step 1: Pre-flight Verification
Run local regressions to verify code integrity before deployment:

```bash
# 1. Run all backend tests (must report 66/66 passed)
./venv/bin/pytest backend/tests -v

# 2. Run frontend typecheck, linter, and production build
cd frontend
npm run typecheck
npm run lint
npm run build
cd ..
```

### Step 2: Database Migration & Seeding
Execute database migrations directly against PostgreSQL port 5432:

```bash
# Apply pending schema migrations
docker compose run --rm api alembic upgrade head
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

All 5 services (`lexai-postgres`, `lexai-pgbouncer`, `lexai-redis`, `lexai-api`, `lexai-nginx`) must display status `healthy` or `Up`.

### Step 4: Health Check & Verification Smoke Tests
Execute the automated smoke verification:

```bash
# 1. Verify HTTP -> HTTPS 301 Redirection
curl -I http://localhost/health
# Expected: HTTP/1.1 301 Moved Permanently -> Location: https://localhost/health

# 2. Verify HTTPS Healthcheck Endpoint
curl -k https://localhost/health
# Expected: {"status":"healthy","database":"connected","database_engine":"postgresql","environment":"production","version":"1.0.0"}

# 3. Verify Rate Limiting on Login
for i in {1..12}; do
  curl -k -s -o /dev/null -w "Attempt $i: HTTP %{http_code}\n" \
    -X POST https://localhost/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"probe@example.com","password":"WrongPassword!"}'
done
# Expected: Attempts 1-5 (or burst) return 401; subsequent attempts return 429 Too Many Requests

# 4. Verify Full Real User Journeys
docker compose run --rm -e API_BASE_URL=http://api:8000 api \
  python /app/staging/verify_full_user_journeys.py
```

---

## 5. Operations & Monitoring

### Viewing Logs
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
Inspect cache hit/miss ratio and memory usage:

```bash
redis-cli -p 6379 info stats | grep -E "keyspace_hits|keyspace_misses"
redis-cli -p 6379 info memory | grep "used_memory_human"
```

---

## 6. Rollback Procedures

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
   docker compose exec redis redis-cli flushdb
   ```

