import time
import pytest
from app.cache import (
    cache_manager,
    get_lawyer_list_cache_key,
    get_lawyer_detail_cache_key,
    invalidate_lawyer_caches
)

@pytest.fixture(autouse=True)
def clean_cache():
    cache_manager.clear()
    yield
    cache_manager.clear()

def test_lawyer_list_cache_hit_and_miss(client):
    # First request: Cache Miss -> Fetches from DB and stores in cache
    res1 = client.get("/api/lawyers?city=Hyderabad")
    assert res1.status_code == 200
    data1 = res1.json()

    key = get_lawyer_list_cache_key(city="Hyderabad", skip=0, limit=50)
    cached = cache_manager.get(key)
    assert cached is not None
    assert len(cached) == len(data1)

    # Second request: Cache Hit
    res2 = client.get("/api/lawyers?city=Hyderabad")
    assert res2.status_code == 200
    assert res2.json() == data1

def test_lawyer_list_cache_key_differentiation(client):
    # Different query parameters must produce distinct cache entries
    res_hyd = client.get("/api/lawyers?city=Hyderabad")
    res_blr = client.get("/api/lawyers?city=Bengaluru")

    assert res_hyd.status_code == 200
    assert res_blr.status_code == 200

    key_hyd = get_lawyer_list_cache_key(city="Hyderabad", skip=0, limit=50)
    key_blr = get_lawyer_list_cache_key(city="Bengaluru", skip=0, limit=50)

    assert key_hyd != key_blr
    assert cache_manager.get(key_hyd) is not None
    assert cache_manager.get(key_blr) is not None

def test_lawyer_detail_cache_hit_and_invalidation(client):
    # Fetch lawyer detail
    res1 = client.get("/api/lawyers/1")
    assert res1.status_code == 200
    key = get_lawyer_detail_cache_key(1)
    assert cache_manager.get(key) is not None

    # Invalidate cache for lawyer 1
    invalidate_lawyer_caches(1)
    assert cache_manager.get(key) is None

def test_cache_ttl_expiration():
    test_key = "test:ttl:key"
    cache_manager.set(test_key, {"status": "ok"}, ttl=1)
    assert cache_manager.get(test_key) == {"status": "ok"}

    time.sleep(1.1)
    # After TTL, cache must return None
    assert cache_manager.get(test_key) is None

def test_authenticated_me_never_cached(client):
    # Login User A
    login_a = client.post("/api/auth/login", json={
        "email": "alex.morgan@workspace.lexai",
        "password": "DemoUserPass123!"
    })
    token_a = login_a.json()["access_token"]

    # Register & Login User B
    client.post("/api/auth/register", json={
        "email": "user.b@example.com",
        "password": "Password123!",
        "full_name": "User B",
        "role": "USER"
    })
    login_b = client.post("/api/auth/login", json={
        "email": "user.b@example.com",
        "password": "Password123!"
    })
    token_b = login_b.json()["access_token"]

    # Fetch /api/auth/me for User A
    res_a = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["email"] == "alex.morgan@workspace.lexai"

    # Fetch /api/auth/me for User B - must never receive User A's data
    res_b = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["email"] == "user.b@example.com"

