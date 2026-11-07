import os
import re
import pytest
from app.config import Settings
from app.rate_limiter import RateLimiter

def test_production_secret_key_length_enforcement():
    """Verify that production fails when SECRET_KEY is shorter than 32 characters."""
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="short-secret-key-16",
        CORS_ORIGINS=["https://lex-ai-rust-five.vercel.app"]
    )
    with pytest.raises(RuntimeError, match="minimum 32 characters"):
        settings.validate_production_security()

def test_production_default_secret_key_rejection():
    """Verify that production fails when DEFAULT_INSECURE_SECRET is used."""
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="lexai-super-secret-jwt-key-2026-production-ready",
        CORS_ORIGINS=["https://lex-ai-rust-five.vercel.app"]
    )
    with pytest.raises(RuntimeError, match="must be configured with a strong, unique secret key"):
        settings.validate_production_security()

def test_production_valid_secret_key_passes():
    """Verify that a strong 32+ character secret key succeeds."""
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="c84d72e9a2f6b801a95e6f3b7d1e4c9a8f2b6e1d5a7c3e9b0d4f8a2c6e1d5a7b",
        CORS_ORIGINS=["https://lex-ai-rust-five.vercel.app"]
    )
    # Should not raise any exception
    settings.validate_production_security()

def test_production_cors_wildcard_rejection():
    """Verify that wildcard CORS is rejected in production mode."""
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="c84d72e9a2f6b801a95e6f3b7d1e4c9a8f2b6e1d5a7c3e9b0d4f8a2c6e1d5a7b",
        CORS_ORIGINS=["*"]
    )
    with pytest.raises(RuntimeError, match="Wildcard '\\*' in CORS_ORIGINS is prohibited"):
        settings.validate_production_security()

def test_forwarded_ip_extraction():
    """Verify rate limiter extracts the genuine client IP from proxy headers."""
    limiter = RateLimiter()

    class MockRequest:
        def __init__(self, headers, client_host="127.0.0.1"):
            self.headers = headers
            class Client:
                def __init__(self, host):
                    self.host = host
            self.client = Client(client_host)

    # 1. Multi-hop X-Forwarded-For: Client IP must be the first element
    req1 = MockRequest(headers={"X-Forwarded-For": "203.0.113.195, 172.18.0.4, 10.0.0.1"})
    assert limiter._get_client_ip(req1) == "203.0.113.195"

    # 2. X-Real-IP fallback
    req2 = MockRequest(headers={"X-Real-IP": "198.51.100.77"})
    assert limiter._get_client_ip(req2) == "198.51.100.77"

    # 3. Direct client connection without proxy headers
    req3 = MockRequest(headers={}, client_host="192.168.1.50")
    assert limiter._get_client_ip(req3) == "192.168.1.50"

def test_nginx_configuration_security_directives():
    """Verify Nginx reverse proxy configuration files enforce required security rules."""
    nginx_conf_path = "nginx/nginx.conf"
    lexai_conf_path = "nginx/conf.d/lexai.conf"

    assert os.path.exists(nginx_conf_path), "nginx.conf must exist"
    assert os.path.exists(lexai_conf_path), "lexai.conf must exist"

    with open(nginx_conf_path, "r") as f:
        nginx_conf = f.read()

    with open(lexai_conf_path, "r") as f:
        lexai_conf = f.read()

    # Rate limiting zone configuration
    assert "limit_req_zone $binary_remote_addr zone=auth_login_limit" in nginx_conf
    assert "rate=5r/m" in nginx_conf

    # Port 80 HTTP -> HTTPS redirection
    assert "listen 80" in lexai_conf
    assert "return 301 https://$host$request_uri;" in lexai_conf

    # Port 443 SSL termination
    assert "listen 443 ssl" in lexai_conf
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in lexai_conf
    assert "ssl_certificate /etc/nginx/ssl/lexai.crt;" in lexai_conf
    assert "ssl_certificate_key /etc/nginx/ssl/lexai.key;" in lexai_conf

    # Strict Security Headers
    assert "Strict-Transport-Security" in lexai_conf
    assert "X-Content-Type-Options" in lexai_conf
    assert "X-Frame-Options" in lexai_conf

    # Rate limiting on /api/auth/login
    assert "location /api/auth/login" in lexai_conf
    assert "limit_req zone=auth_login_limit" in lexai_conf
    assert "limit_req_status 429;" in lexai_conf

def test_docker_compose_port_isolation():
    """Verify that docker-compose.yml does not expose backend/database ports to 0.0.0.0."""
    with open("docker-compose.yml", "r") as f:
        lines = f.readlines()

    in_ports_section = False
    current_service = None

    for line in lines:
        stripped = line.strip()
        # Track service definitions
        if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
            current_service = stripped[:-1]

        if stripped == "ports:":
            in_ports_section = True
            continue

        if in_ports_section:
            if stripped.startswith("- "):
                port = stripped[2:].strip('"').strip("'")
                if current_service == "nginx":
                    assert port in ["80:80", "443:443"], f"Nginx should only expose standard HTTP/S: {port}"
                else:
                    assert port.startswith("127.0.0.1:"), (
                        f"Service '{current_service}' exposes unsafe port binding '{port}'. "
                        "Only 127.0.0.1 loopback or internal Docker network bindings are permitted."
                    )
            else:
                in_ports_section = False

def test_docker_compose_production_hardening():
    """Verify log rotation, certbot, and mandatory environment variables in compose."""
    with open("docker-compose.yml", "r") as f:
        compose_text = f.read()

    # Log rotation
    assert 'max-size: "50m"' in compose_text
    assert 'max-file: "5"' in compose_text

    # Certbot renewal companion
    assert "certbot-www:/var/www/certbot" in compose_text
    assert "container_name: lexai-certbot" in compose_text

    # No insecure fallback secrets
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?FATAL" in compose_text
    assert "SECRET_KEY: ${SECRET_KEY:?FATAL" in compose_text
    assert "REDIS_PASSWORD: ${REDIS_PASSWORD:?FATAL" in compose_text

def test_dockerfile_runs_as_non_root():
    """Verify Dockerfile creates and executes under an unprivileged user."""
    with open("Dockerfile", "r") as f:
        dockerfile_text = f.read()

    assert "useradd" in dockerfile_text
    assert "USER lexai" in dockerfile_text
