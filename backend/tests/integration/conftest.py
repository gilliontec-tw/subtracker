import httpx
import pytest
from api.main import app


@pytest.fixture(scope="module")
async def client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://testserver",
    ) as c:
        yield c


@pytest.fixture(scope="module")
async def authed_client(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    return client
