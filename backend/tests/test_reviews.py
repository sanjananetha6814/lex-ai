import pytest

def test_review_completed_consultation_flow(client):
    # 1. Register a client
    user_payload = {
        "email": "reviewer.client@test.lexai",
        "password": "Password123!",
        "full_name": "Reviewer Client",
        "city": "Bengaluru",
        "role": "USER"
    }
    reg_res = client.post("/api/auth/register", json=user_payload)
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get lawyer
    lawyers_res = client.get("/api/lawyers")
    assert lawyers_res.status_code == 200
    lawyer_id = lawyers_res.json()[0]["id"]

    # 3. Book consultation
    booking_payload = {
        "lawyer_id": lawyer_id,
        "client_name": "Reviewer Client",
        "client_email": "reviewer.client@test.lexai",
        "client_phone": "+91 9988776655",
        "client_language": "English",
        "format": "video",
        "scheduled_date": "2026-11-15",
        "scheduled_slot": "11:30 AM",
        "issue_description": "Reviewing tenancy clause regarding repairs and maintenance.",
        "is_urgent": False
    }
    book_res = client.post("/api/consultations", json=booking_payload, headers=headers)
    assert book_res.status_code == 201
    consultation_id = book_res.json()["id"]

    # 4. Attempt to review while PENDING -> should fail with 400
    early_review_res = client.post(
        f"/api/consultations/{consultation_id}/review",
        json={"rating": 5, "comment": "Great lawyer"},
        headers=headers
    )
    assert early_review_res.status_code == 400

    # 5. Mark consultation as COMPLETED by authorized advocate
    lawyer_login = client.post("/api/auth/login", json={
        "email": "ananya.rao@lexai.directory",
        "password": "LawyerPass123!"
    })
    lawyer_token = lawyer_login.json()["access_token"]
    lawyer_headers = {"Authorization": f"Bearer {lawyer_token}"}

    update_res = client.patch(
        f"/api/consultations/{consultation_id}/status",
        json={"status": "COMPLETED"},
        headers=lawyer_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "COMPLETED"

    # 6. Submit review on COMPLETED consultation
    review_res = client.post(
        f"/api/consultations/{consultation_id}/review",
        json={
            "rating": 5,
            "comment": "Exceptional legal advice! Clarified the tenancy terms thoroughly."
        },
        headers=headers
    )
    assert review_res.status_code == 201
    rev_data = review_res.json()
    assert rev_data["rating"] == 5
    assert rev_data["lawyer_id"] == lawyer_id
    assert rev_data["consultation_id"] == consultation_id
    assert rev_data["client_name"] == "Reviewer Client"

    # 7. Duplicate review -> should fail with 400
    dup_res = client.post(
        f"/api/consultations/{consultation_id}/review",
        json={"rating": 4, "comment": "Another review"},
        headers=headers
    )
    assert dup_res.status_code == 400

    # 8. Check that consultation response now reflects is_reviewed == True
    consult_check = client.get(f"/api/consultations/{consultation_id}", headers=headers)
    assert consult_check.status_code == 200
    assert consult_check.json()["is_reviewed"] is True
    assert consult_check.json()["user_review"] is not None
    assert consult_check.json()["user_review"]["rating"] == 5

    # 9. Check that lawyer detail includes the new review
    lawyer_check = client.get(f"/api/lawyers/{lawyer_id}")
    assert lawyer_check.status_code == 200
    reviews = lawyer_check.json().get("reviews", [])
    assert any(r["comment"] == "Exceptional legal advice! Clarified the tenancy terms thoroughly." for r in reviews)
