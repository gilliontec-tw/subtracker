import httpx
import pytest
from api.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="module")
async def client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://testserver",
    ) as c:
        yield c


async def test_me_without_auth_returns_401(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["success"] is False


async def test_login_with_wrong_password_returns_401(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "wrong"},
    )
    assert r.status_code == 401


async def test_login_with_nonexistent_email_returns_401(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "noexist@test.com", "password": "any"},
    )
    assert r.status_code == 401


async def test_full_login_me_logout_flow(client):
    # Login
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["email"] == "admin@test.com"
    assert body["data"]["role"] == "admin"
    assert "access_token" in r.cookies
    assert "csrf_token" in r.cookies

    # /me with valid session
    csrf = r.cookies["csrf_token"]
    r2 = await client.get("/api/v1/auth/me")
    assert r2.status_code == 200
    assert r2.json()["data"]["email"] == "admin@test.com"

    # Logout
    r3 = await client.post(
        "/api/v1/auth/logout",
        headers={"x-csrf-token": csrf},
    )
    assert r3.status_code == 200

    # /me after logout should fail
    r4 = await client.get("/api/v1/auth/me")
    assert r4.status_code == 401
