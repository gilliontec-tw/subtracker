import pytest
from api.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def authed_client(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    return client
