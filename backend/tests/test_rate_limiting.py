import pytest
from app.rate_limiter import auth_rate_limiter

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure a clean rate-limiting state before and after each test."""
    auth_rate_limiter.reset()
    yield
    auth_rate_limiter.reset()

def test_login_rate_limiting_enforced(client):
    """
    Verify that excessive login attempts from the same IP are rate-limited
    with HTTP 429 Too Many Requests.
    """
    limit = auth_rate_limiter.default_limit
    # Send requests up to limit
    for i in range(limit):
        resp = client.post("/api/auth/login", json={
            "email": f"attacker_{i}@example.com",
            "password": "WrongPassword123!"
        }, headers={"X-Forwarded-For": "198.51.100.10"})
        # Prior to hitting the limit, invalid credentials return 401
        assert resp.status_code == 401, f"Attempt {i+1} should be 401"

    # Next attempt must be blocked with HTTP 429
    blocked_resp = client.post("/api/auth/login", json={
        "email": "attacker_overflow@example.com",
        "password": "WrongPassword123!"
    }, headers={"X-Forwarded-For": "198.51.100.10"})
    
    assert blocked_resp.status_code == 429
    data = blocked_resp.json()
    assert data["error"] is True
    assert "Too many login attempts" in data["message"]
    assert "Retry-After" in blocked_resp.headers

def test_rate_limiting_does_not_leak_account_existence(client):
    """
    Verify that rate limiting behaves identically for both registered
    and non-existent accounts, preventing user enumeration.
    """
    # Register an actual user first
    client.post("/api/auth/register", json={
        "email": "realuser@example.com",
        "password": "ValidPassword123!",
        "full_name": "Real User",
        "role": "USER"
    })

    ip = "203.0.113.42"
    # Exhaust the rate limit using non-existent email
    for _ in range(10):
        client.post("/api/auth/login", json={
            "email": "ghost@example.com",
            "password": "WrongPassword123!"
        }, headers={"X-Forwarded-For": ip})

    # Now attempt with the real registered account from the same IP
    resp_real = client.post("/api/auth/login", json={
        "email": "realuser@example.com",
        "password": "ValidPassword123!"
    }, headers={"X-Forwarded-For": ip})

    # It must return 429 without verifying password or revealing the user exists
    assert resp_real.status_code == 429
    assert "Too many login attempts" in resp_real.json()["message"]

def test_rate_limiting_isolated_by_client_ip(client):
    """
    Verify that rate limiting for one IP does not impact legitimate
    traffic originating from a different client IP.
    """
    bad_ip = "192.0.2.1"
    good_ip = "192.0.2.2"

    # Exhaust rate limit for bad_ip
    for _ in range(10):
        client.post("/api/auth/login", json={
            "email": "user@example.com",
            "password": "WrongPassword!"
        }, headers={"X-Forwarded-For": bad_ip})

    bad_resp = client.post("/api/auth/login", json={
        "email": "user@example.com",
        "password": "WrongPassword!"
    }, headers={"X-Forwarded-For": bad_ip})
    assert bad_resp.status_code == 429

    # Legitimate user from good_ip should still be allowed through
    good_resp = client.post("/api/auth/login", json={
        "email": "alex.morgan@workspace.lexai",
        "password": "DemoUserPass123!"
    }, headers={"X-Forwarded-For": good_ip})
    assert good_resp.status_code == 200
