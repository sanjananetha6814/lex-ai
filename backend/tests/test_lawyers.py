def test_get_lawyers_list(client):
    response = client.get("/api/lawyers")
    assert response.status_code == 200
    lawyers = response.json()
    assert len(lawyers) >= 5
    # Check structure
    lawyer = lawyers[0]
    assert "name" in lawyer
    assert "city" in lawyer
    assert "profile" in lawyer
    assert lawyer["profile"]["specialty"] is not None
    assert lawyer["profile"]["rating"] > 4.0

def test_search_lawyers(client):
    response = client.get("/api/lawyers?search=Property")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert any("Property" in l["profile"]["specialty"] for l in results)

def test_filter_lawyers_by_city(client):
    response = client.get("/api/lawyers?city=Mumbai")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert all(l["city"] == "Mumbai" for l in results)

def test_get_lawyer_by_id_success(client):
    # Fetch first lawyer from list
    list_resp = client.get("/api/lawyers")
    lawyer_id = list_resp.json()[0]["id"]

    response = client.get(f"/api/lawyers/{lawyer_id}")
    assert response.status_code == 200
    lawyer = response.json()
    assert lawyer["id"] == lawyer_id
    assert lawyer["profile"]["experience_years"] is not None
    assert len(lawyer["profile"]["practice_areas"]) > 0
    assert len(lawyer["profile"]["qualifications"]) > 0
    assert len(lawyer["profile"]["slots"]) > 0

def test_get_lawyer_by_id_not_found(client):
    response = client.get("/api/lawyers/999999")
    assert response.status_code == 404
    assert "not found" in response.json()["message"].lower()
