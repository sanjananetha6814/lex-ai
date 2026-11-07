from app.models.user import User, UserRole
from app.auth import get_password_hash

def test_register_user_success(client):
    payload = {
        "email": "test.lawyer@example.com",
        "password": "SecurePassword123!",
        "full_name": "Adv. Test Lawyer",
        "role": "LAWYER",
        "phone_number": "+91 99999 88888",
        "city": "Chennai",
        "preferred_language": "English"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test.lawyer@example.com"
    # Security requirement: public registration strictly assigns USER role
    assert data["user"]["role"] == "USER"
    assert data["user"]["profile"]["full_name"] == "Adv. Test Lawyer"

def test_register_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
        "full_name": "User One",
        "role": "USER"
    }
    # First registration
    resp1 = client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 201

    # Second registration with same email
    resp2 = client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["message"]

def test_login_success(client):
    # Register user
    client.post("/api/auth/register", json={
        "email": "login.test@example.com",
        "password": "LoginSecret123!",
        "full_name": "Login Tester",
        "role": "USER"
    })

    # Login
    response = client.post("/api/auth/login", json={
        "email": "login.test@example.com",
        "password": "LoginSecret123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login.test@example.com"

def test_login_invalid_password(client):
    response = client.post("/api/auth/login", json={
        "email": "admin@lexai.internal",
        "password": "WrongPassword999"
    })
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["message"]

def test_get_me_authenticated(client):
    # Login as seeded demo user
    login_resp = client.post("/api/auth/login", json={
        "email": "alex.morgan@workspace.lexai",
        "password": "DemoUserPass123!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Call /api/auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["email"] == "alex.morgan@workspace.lexai"
    assert user_data["profile"]["full_name"] == "Alex Morgan"

def test_get_me_unauthenticated(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_login_unknown_user_rejected_without_enumeration(client):
    response = client.post("/api/auth/login", json={
        "email": "ghost.nonexistent@lexai.internal",
        "password": "SomeRandomPassword123!"
    })
    assert response.status_code == 401
    assert "Incorrect email or password" in response.text
    assert response.headers.get("www-authenticate") == "Bearer"

def test_login_disabled_user_rejected(client, db):
    # Create deactivated user
    disabled_email = "deactivated.tester@example.com"
    existing = db.query(User).filter(User.email == disabled_email).first()
    if not existing:
        disabled_user = User(
            email=disabled_email,
            password_hash=get_password_hash("DeactivatedPass123!"),
            role=UserRole.USER,
            is_active=False
        )
        db.add(disabled_user)
        db.commit()

    # Wrong password should still return 401 (preventing status discovery)
    resp_bad_pwd = client.post("/api/auth/login", json={
        "email": disabled_email,
        "password": "WrongPassword!"
    })
    assert resp_bad_pwd.status_code == 401
    assert "Incorrect email or password" in resp_bad_pwd.text

    # Correct password on disabled account must return 403 Forbidden
    resp_correct_pwd = client.post("/api/auth/login", json={
        "email": disabled_email,
        "password": "DeactivatedPass123!"
    })
    assert resp_correct_pwd.status_code == 403
    assert "deactivated" in resp_correct_pwd.text.lower()

def test_login_session_released_before_password_verification(client, monkeypatch):
    """
    Verify that the database session is closed and returned to the pool
    strictly BEFORE CPU-intensive Argon2 password verification is executed.
    """
    from app.routers import auth as auth_router_mod
    original_verify = auth_router_mod.verify_password
    call_events = []

    # Intercept session close and verify_password to trace exact sequence
    from sqlalchemy.orm import Session
    original_close = Session.close

    def instrumented_close(self):
        call_events.append("db_session_closed")
        return original_close(self)

    def instrumented_verify(plain_pwd, hashed_pwd):
        call_events.append("argon2_verify_executed")
        return original_verify(plain_pwd, hashed_pwd)

    monkeypatch.setattr(Session, "close", instrumented_close)
    monkeypatch.setattr(auth_router_mod, "verify_password", instrumented_verify)

    response = client.post("/api/auth/login", json={
        "email": "alex.morgan@workspace.lexai",
        "password": "DemoUserPass123!"
    })
    assert response.status_code == 200

    # Ensure db_session_closed happened BEFORE argon2_verify_executed
    assert "db_session_closed" in call_events
    assert "argon2_verify_executed" in call_events
    first_close_idx = call_events.index("db_session_closed")
    verify_idx = call_events.index("argon2_verify_executed")
    assert first_close_idx < verify_idx, (
        f"Database session was closed at index {first_close_idx}, but password verification "
        f"ran at index {verify_idx}. The DB session must be released BEFORE verification."
    )

def test_login_failed_verification_does_not_leak_connections(client, monkeypatch):
    """
    Ensure repeated failed logins (bad password, unknown email, disabled user)
    cleanly close database sessions and do not leak connections.
    """
    monkeypatch.setenv("DISABLE_RATE_LIMITER", "true")
    for _ in range(10):
        res1 = client.post("/api/auth/login", json={
            "email": "unknown.probe@example.com",
            "password": "probe-password"
        })
        assert res1.status_code == 401

        res2 = client.post("/api/auth/login", json={
            "email": "alex.morgan@workspace.lexai",
            "password": "wrong-password"
        })
        assert res2.status_code == 401

    # Verify a valid login immediately succeeds thereafter
    valid_res = client.post("/api/auth/login", json={
        "email": "alex.morgan@workspace.lexai",
        "password": "DemoUserPass123!"
    })
    assert valid_res.status_code == 200
    assert "access_token" in valid_res.json()
