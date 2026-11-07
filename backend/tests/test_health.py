def test_health_check_endpoint(client):
    """Verify /health returns 200 with status=healthy, database=connected, cache, and database_engine."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "cache" in data
    assert "database_engine" in data
    assert data["database_engine"] in ["sqlite", "postgresql"]
    assert "environment" in data
    assert "version" in data

def test_metrics_endpoint(client):
    """Verify /metrics returns runtime and resource configuration parameters."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert "database_engine" in data
    assert "pool_size" in data
    assert "cache_backend" in data

def test_root_endpoint(client):
    """Verify / root documentation and online status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "documentation" in data

