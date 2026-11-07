#!/usr/bin/env bash
# =========================================================================
# LexAI Automated SSL Renewal & Nginx Reload Helper
# Executes certbot renewal against the shared ACME webroot and reloads Nginx
# =========================================================================
set -euo pipefail

WEBROOT_DIR="${WEBROOT_DIR:-/var/www/certbot}"

echo "================================================================="
echo "  LEXAI SSL CERTIFICATE RENEWAL TRIGGER"
echo "  Webroot: ${WEBROOT_DIR}"
echo "================================================================="

if command -v certbot &>/dev/null; then
    echo "Running host Certbot renewal..."
    certbot renew --webroot -w "$WEBROOT_DIR" --quiet
elif command -v docker &>/dev/null && docker compose ps lexai-certbot &>/dev/null; then
    echo "Triggering renewal inside lexai-certbot container..."
    docker compose run --rm certbot renew --webroot -w /var/www/certbot --quiet
else
    echo "NOTICE: Certbot command not detected in current shell."
    echo "In production, install Certbot or rely on the lexai-certbot companion container."
    exit 0
fi

# Reload Nginx configuration if container is active
if command -v docker &>/dev/null && docker compose ps lexai-nginx | grep -q "Up"; then
    echo "Reloading Nginx to apply renewed certificates..."
    docker compose exec nginx nginx -s reload
    echo "✓ Nginx reloaded successfully."
fi

echo "SSL renewal workflow completed."

