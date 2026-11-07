#!/usr/bin/env bash
# =========================================================================
# LexAI Self-Signed SSL Certificate Generator (for Local/Staging Validation)
# In production, replace with certificates issued by Let's Encrypt / Certbot
# or an enterprise Certificate Authority (CA).
# =========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${SCRIPT_DIR}/ssl"

mkdir -p "${SSL_DIR}"

if [[ -f "${SSL_DIR}/lexai.key" && -f "${SSL_DIR}/lexai.crt" ]]; then
    echo "SSL certificate and key already exist in ${SSL_DIR}"
    exit 0
fi

echo "Generating 2048-bit RSA self-signed SSL certificate for LexAI..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${SSL_DIR}/lexai.key" \
    -out "${SSL_DIR}/lexai.crt" \
    -subj "/CN=localhost/O=LexAI/C=US"

chmod 600 "${SSL_DIR}/lexai.key"
chmod 644 "${SSL_DIR}/lexai.crt"

echo "SSL certificates generated successfully:"
echo "  Key:  ${SSL_DIR}/lexai.key"
echo "  Cert: ${SSL_DIR}/lexai.crt"

