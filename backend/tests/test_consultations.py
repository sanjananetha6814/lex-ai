def test_create_consultation_success(client):
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

    response = client.post("/api/consultations", json=payload)
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

    # Verify retrieval by ID
    get_resp = client.get(f"/api/consultations/{consultation_id}")
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
