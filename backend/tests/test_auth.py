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
    assert data["user"]["role"] == "LAWYER"
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
