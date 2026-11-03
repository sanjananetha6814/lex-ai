import pytest
from app.config import Settings
from app.models.consultation import ConsultationStatus

def _get_err_msg(response) -> str:
    data = response.json()
    return (data.get("message") or data.get("detail") or "").lower()

def test_admin_privilege_escalation_forbidden(client):
    """CRITICAL FIX 1: Verify public registration cannot escalate to ADMIN."""
    payload = {
        "email": "rogue.admin@example.com",
        "password": "Password123!",
        "full_name": "Rogue Admin",
        "role": "ADMIN"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 403
    assert "administrative privileges" in _get_err_msg(response)

def test_lawyer_self_registration_assigned_user_role(client):
    """CRITICAL FIX 1 (cont.): Verify public registration requesting LAWYER role is assigned USER role."""
    payload = {
        "email": "applicant.lawyer@example.com",
        "password": "Password123!",
        "full_name": "Adv. Applicant",
        "role": "LAWYER"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "USER"

def test_consultations_data_leak_prevented_anonymous(client):
    """CRITICAL FIX 2: Verify anonymous requests to /api/consultations do not leak records."""
    # List should return empty array
    list_res = client.get("/api/consultations")
    assert list_res.status_code == 200
    assert list_res.json() == []

    # Direct ID access should be blocked with 401
    get_res = client.get("/api/consultations/1")
    assert get_res.status_code == 401

def test_consultations_cross_user_idor_forbidden(client):
    """CRITICAL FIX 2 (cont.): Verify User A cannot access User B's consultation."""
    # Register Client A
    reg_a = client.post("/api/auth/register", json={
        "email": "client.alpha.sec@example.com",
        "password": "Password123!",
        "full_name": "Client Alpha"
    })
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Client B
    reg_b = client.post("/api/auth/register", json={
        "email": "client.beta.sec@example.com",
        "password": "Password123!",
        "full_name": "Client Beta"
    })
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Client A books consultation
    lawyer_id = client.get("/api/lawyers").json()[0]["id"]
    book_res = client.post("/api/consultations", json={
        "lawyer_id": lawyer_id,
        "client_name": "Client Alpha",
        "client_email": "client.alpha.sec@example.com",
        "client_phone": "+91 99999 11111",
        "scheduled_date": "2026-11-20",
        "scheduled_slot": "10:00 AM",
        "issue_description": "Alpha Private Consultation."
    }, headers=headers_a)
    assert book_res.status_code == 201
    c_id = book_res.json()["id"]

    # Client B attempts to view Client A's consultation
    b_view_res = client.get(f"/api/consultations/{c_id}", headers=headers_b)
    assert b_view_res.status_code == 403
    assert "permission" in _get_err_msg(b_view_res)

def test_consultation_status_manipulation_forbidden(client):
    """CRITICAL FIX 3: Verify client cannot mark consultation CONFIRMED or COMPLETED."""
    reg = client.post("/api/auth/register", json={
        "email": "client.status.test@example.com",
        "password": "Password123!",
        "full_name": "Status Tester"
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    lawyer_id = client.get("/api/lawyers").json()[0]["id"]
    book_res = client.post("/api/consultations", json={
        "lawyer_id": lawyer_id,
        "client_name": "Status Tester",
        "client_email": "client.status.test@example.com",
        "client_phone": "+91 99999 22222",
        "scheduled_date": "2026-11-20",
        "scheduled_slot": "11:00 AM",
        "issue_description": "Testing status manipulation."
    }, headers=headers)
    c_id = book_res.json()["id"]

    # Anonymous patch is blocked (401)
    anon_patch = client.patch(f"/api/consultations/{c_id}/status", json={"status": "CONFIRMED"})
    assert anon_patch.status_code == 401

    # Client attempts to confirm own consultation -> blocked (403)
    client_confirm = client.patch(f"/api/consultations/{c_id}/status", json={"status": "CONFIRMED"}, headers=headers)
    assert client_confirm.status_code == 403

    # Client can cancel own consultation -> allowed (200)
    client_cancel = client.patch(f"/api/consultations/{c_id}/status", json={"status": "CANCELLED"}, headers=headers)
    assert client_cancel.status_code == 200
    assert client_cancel.json()["status"] == "CANCELLED"

def test_production_fails_on_default_jwt_secret():
    """CRITICAL FIX 4: Verify production fails startup when default secret or wildcard is present."""
    # Default secret in production must raise RuntimeError
    insecure_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="lexai-super-secret-jwt-key-2026-production-ready",
        CORS_ORIGINS=["https://lexai.com"]
    )
    with pytest.raises(RuntimeError) as exc_info:
        insecure_settings.validate_production_security()
    assert "In production mode, SECRET_KEY must be configured" in str(exc_info.value)

    # Valid secret in production passes
    secure_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 32,
        CORS_ORIGINS=["https://lexai.com"]
    )
    secure_settings.validate_production_security()  # Should not raise

def test_review_spoofing_prevented(client):
    """HIGH FIX 5: Verify reviews require authentication, completed consultation, and matching ownership."""
    # 1. Anonymous review blocked
    anon_res = client.post("/api/lawyers/1/reviews", json={"rating": 5, "comment": "Fake review"})
    assert anon_res.status_code == 401

    # Register user
    reg = client.post("/api/auth/register", json={
        "email": "reviewer.sec@example.com",
        "password": "Password123!",
        "full_name": "Reviewer Sec"
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # 2. Missing consultation_id blocked
    no_consult_res = client.post("/api/lawyers/1/reviews", json={"rating": 5, "comment": "No consultation review"}, headers=headers)
    assert no_consult_res.status_code == 400

    # 3. Non-completed consultation blocked
    book_res = client.post("/api/consultations", json={
        "lawyer_id": 1,
        "client_name": "Reviewer Sec",
        "client_email": "reviewer.sec@example.com",
        "client_phone": "+91 99999 33333",
        "scheduled_date": "2026-11-20",
        "scheduled_slot": "02:00 PM",
        "issue_description": "Testing premature review."
    }, headers=headers)
    c_id = book_res.json()["id"]

    premature_res = client.post("/api/lawyers/1/reviews", json={
        "consultation_id": c_id,
        "rating": 5,
        "comment": "Premature review"
    }, headers=headers)
    assert premature_res.status_code == 400
    assert "completed" in _get_err_msg(premature_res)

def test_cors_origins_has_no_wildcard():
    """HIGH FIX 6: Verify CORS_ORIGINS does not contain wildcard '*'."""
    from app.config import settings
    assert "*" not in settings.CORS_ORIGINS

def test_chat_ownership_and_demo_isolation(client):
    """HIGH FIX 7: Verify conversation ownership check and demo isolation in /api/chat."""
    # Register User A and create conversation
    reg_a = client.post("/api/auth/register", json={
        "email": "chat.user.a@example.com",
        "password": "Password123!",
        "full_name": "Chat User A"
    })
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    conv_res = client.post("/api/conversations", json={"title": "User A Private Chat"}, headers=headers_a)
    conv_id = conv_res.json()["id"]

    # Register User B
    reg_b = client.post("/api/auth/register", json={
        "email": "chat.user.b@example.com",
        "password": "Password123!",
        "full_name": "Chat User B"
    })
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # User B attempts to append message to User A's conversation
    idor_res = client.post("/api/chat", json={
        "message": "Injected malicious message",
        "conversation_id": conv_id
    }, headers=headers_b)
    assert idor_res.status_code == 403
    assert "permission" in _get_err_msg(idor_res)

    # Anonymous user calling /api/chat with conversation_id is blocked with 401
    anon_idor = client.post("/api/chat", json={
        "message": "Anonymous injection",
        "conversation_id": conv_id
    })
    assert anon_idor.status_code == 401

    # Anonymous user calling /api/chat without conversation_id works, but returns conversation_id = None
    anon_chat = client.post("/api/chat", json={"message": "What is Section 106 of Transfer of Property Act?"})
    assert anon_chat.status_code == 200
    assert anon_chat.json()["conversation_id"] is None
