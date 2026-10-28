# tests/test_health.py

def test_openapi_documentation_is_available(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    data = response.json()
    assert "paths" in data
    assert "info" in data