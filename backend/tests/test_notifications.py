def get_auth_token(client, email, password):
    login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]

def test_get_notifications_unauthenticated(client):
    response = client.get("/api/notifications")
    assert response.status_code == 401

def test_get_notifications_authenticated(client):
    token = get_auth_token(client, "alex.morgan@workspace.lexai", "DemoUserPass123!")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "unread_count" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1

def test_mark_notification_read(client):
    token = get_auth_token(client, "alex.morgan@workspace.lexai", "DemoUserPass123!")
    headers = {"Authorization": f"Bearer {token}"}

    # Get list
    resp = client.get("/api/notifications", headers=headers)
    items = resp.json()["items"]
    assert len(items) > 0
    target = items[0]
    target_id = target["id"]

    # Mark as read
    patch_resp = client.patch(f"/api/notifications/{target_id}/read", headers=headers)
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["id"] == target_id
    assert updated["is_read"] is True

def test_mark_all_notifications_read(client):
    token = get_auth_token(client, "ananya.rao@lexai.directory", "LawyerPass123!")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/notifications/mark-all-read", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    # Verify unread count is now 0
    get_resp = client.get("/api/notifications", headers=headers)
    assert get_resp.json()["unread_count"] == 0

def test_notification_cross_user_forbidden(client):
    user_token = get_auth_token(client, "alex.morgan@workspace.lexai", "DemoUserPass123!")
    lawyer_token = get_auth_token(client, "ananya.rao@lexai.directory", "LawyerPass123!")

    # Get lawyer's notification ID
    lawyer_resp = client.get("/api/notifications", headers={"Authorization": f"Bearer {lawyer_token}"})
    lawyer_items = lawyer_resp.json()["items"]
    assert len(lawyer_items) > 0
    lawyer_notif_id = lawyer_items[0]["id"]

    # Client attempts to mark lawyer's notification as read
    patch_resp = client.patch(
        f"/api/notifications/{lawyer_notif_id}/read",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert patch_resp.status_code == 404
