def test_create_consultation_success(client):
    # Register/authenticate Priya Sharma
    reg_res = client.post("/api/auth/register", json={
        "email": "priya.sharma@example.com",
        "password": "Password123!",
        "full_name": "Priya Sharma",
        "city": "Bengaluru"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get an existing lawyer ID
    lawyers = client.get("/api/lawyers").json()
    lawyer_id = lawyers[0]["id"]

    payload = {
        "lawyer_id": lawyer_id,
        "client_name": "Priya Sharma",
        "client_email": "priya.sharma@example.com",
        "client_phone": "+91 98765 11111",
        "client_language": "English",
        "format": "video",
        "scheduled_date": "2026-11-05",
        "scheduled_slot": "10:00 AM",
        "issue_description": "Need legal review of tenancy agreement and dispute resolution options.",
        "is_urgent": True
    }

    response = client.post("/api/consultations", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "reference_no" in data
    assert data["reference_no"].startswith("LEX-")
    assert data["client_name"] == "Priya Sharma"
    assert data["format"] == "video"
    assert data["is_urgent"] is True
    assert data["status"] == "PENDING"
    assert data["lawyer_name"] is not None

    consultation_id = data["id"]

    # Verify retrieval by ID with authenticated client headers
    get_resp = client.get(f"/api/consultations/{consultation_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["reference_no"] == data["reference_no"]

def test_create_consultation_invalid_lawyer(client):
    payload = {
        "lawyer_id": 99999,
        "client_name": "Ghost Client",
        "client_email": "ghost@example.com",
        "client_phone": "+91 99999 00000",
        "client_language": "English",
        "format": "phone",
        "scheduled_date": "2026-11-05",
        "scheduled_slot": "11:30 AM",
        "issue_description": "Looking for advice on a general corporate query."
    }
    response = client.post("/api/consultations", json=payload)
    assert response.status_code == 404
    assert "does not exist" in response.json()["message"]

def test_create_consultation_validation_error(client):
    # Missing required issue_description
    payload = {
        "lawyer_id": 1,
        "client_name": "A",  # too short (<2 chars)
        "client_email": "not-an-email",
        "client_phone": "123",
        "scheduled_date": "2026-11-05",
        "scheduled_slot": "10:00 AM",
        "issue_description": ""
    }
    response = client.post("/api/consultations", json=payload)
    assert response.status_code == 422
    assert response.json()["error"] is True

def test_get_consultations_list(client):
    response = client.get("/api/consultations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_consultation_status_success(client):
    # 1. Create a consultation with client
    reg_res = client.post("/api/auth/register", json={
        "email": "test.client@example.com",
        "password": "Password123!",
        "full_name": "Test Client",
        "city": "Bengaluru"
    })
    client_token = reg_res.json()["access_token"]
    client_headers = {"Authorization": f"Bearer {client_token}"}

    lawyers = client.get("/api/lawyers").json()
    lawyer_id = lawyers[0]["id"]
    payload = {
        "lawyer_id": lawyer_id,
        "client_name": "Test Client",
        "client_email": "test.client@example.com",
        "client_phone": "+91 98765 22222",
        "scheduled_date": "2026-11-10",
        "scheduled_slot": "02:00 PM",
        "issue_description": "Initial dispute consultation.",
    }
    create_res = client.post("/api/consultations", json=payload, headers=client_headers)
    assert create_res.status_code == 201
    c_id = create_res.json()["id"]

    # Authenticate as assigned advocate (Adv. Ananya Rao)
    lawyer_login = client.post("/api/auth/login", json={
        "email": "ananya.rao@lexai.directory",
        "password": "LawyerPass123!"
    })
    lawyer_token = lawyer_login.json()["access_token"]
    lawyer_headers = {"Authorization": f"Bearer {lawyer_token}"}

    # 2. Update status to CONFIRMED
    patch_res = client.patch(f"/api/consultations/{c_id}/status", json={"status": "CONFIRMED"}, headers=lawyer_headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "CONFIRMED"

    # 3. Update status to COMPLETED
    patch_res2 = client.patch(f"/api/consultations/{c_id}/status", json={"status": "COMPLETED"}, headers=lawyer_headers)
    assert patch_res2.status_code == 200
    assert patch_res2.json()["status"] == "COMPLETED"

def test_update_consultation_status_not_found(client):
    lawyer_login = client.post("/api/auth/login", json={
        "email": "ananya.rao@lexai.directory",
        "password": "LawyerPass123!"
    })
    lawyer_token = lawyer_login.json()["access_token"]
    lawyer_headers = {"Authorization": f"Bearer {lawyer_token}"}

    patch_res = client.patch("/api/consultations/99999/status", json={"status": "CANCELLED"}, headers=lawyer_headers)
    assert patch_res.status_code == 404

