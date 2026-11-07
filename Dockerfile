# =========================================================================
# LexAI Production Backend Dockerfile
# =========================================================================
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (build-essential and libpq for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python production dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend application source and database migration configurations
COPY backend /app

# Ensure uploads directory exists
RUN mkdir -p /app/uploads

# Expose API port
EXPOSE 8000

# Container healthcheck using native python request to avoid extra dependencies
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# Environment variable for trusted reverse proxy subnets (Nginx ingress)
ENV FORWARDED_ALLOW_IPS="127.0.0.1,172.16.0.0/12,10.0.0.0/8"

# Launch with multi-worker Uvicorn configuration for production throughput behind reverse proxies
# Restrict forwarded-header trust strictly to trusted proxy IP ranges
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips=\"${FORWARDED_ALLOW_IPS:-127.0.0.1,172.16.0.0/12,10.0.0.0/8}\""]

