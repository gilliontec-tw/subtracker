import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── helpers ──────────────────────────────────────────────────────────────────


def _create_payload(**overrides):
    base = {
        "service_name": "IntegrationTestSVC",
        "expiry_date": "2027-12-31",
        "login_account": "test@corp.com",
        "notification_emails": ["admin@corp.com"],
        "notification_days": 14,
    }
    base.update(overrides)
    return base


def _csrf(client):
    return client.cookies.get("csrf_token", "")


# ── auth-gating ───────────────────────────────────────────────────────────────


async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/subscriptions")
    assert r.status_code == 401


async def test_get_without_auth_returns_401(client):
    r = await client.get("/api/v1/subscriptions/1")
    assert r.status_code == 401


async def test_create_without_auth_returns_401(client):
    r = await client.post("/api/v1/subscriptions", json=_create_payload())
    assert r.status_code == 401


# ── full CRUD flow ────────────────────────────────────────────────────────────


async def test_full_crud_flow(authed_client):
    csrf = _csrf(authed_client)

    # CREATE
    r = await authed_client.post(
        "/api/v1/subscriptions",
        json=_create_payload(),
        headers={"x-csrf-token": csrf},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["success"] is True
    sub_id = body["data"]["id"]
    assert body["data"]["service_name"] == "IntegrationTestSVC"
    assert body["data"]["currency"] == "TWD"

    # GET
    r = await authed_client.get(f"/api/v1/subscriptions/{sub_id}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == sub_id

    # UPDATE
    r = await authed_client.put(
        f"/api/v1/subscriptions/{sub_id}",
        json={"service_name": "UpdatedSVC", "notes": "updated"},
        headers={"x-csrf-token": csrf},
    )
    assert r.status_code == 200
    updated = r.json()["data"]
    assert updated["service_name"] == "UpdatedSVC"
    assert updated["notes"] == "updated"
    assert updated["login_account"] == "test@corp.com"  # unchanged

    # DELETE
    r = await authed_client.delete(
        f"/api/v1/subscriptions/{sub_id}",
        headers={"x-csrf-token": csrf},
    )
    assert r.status_code == 200

    # GET after DELETE → 404
    r = await authed_client.get(f"/api/v1/subscriptions/{sub_id}")
    assert r.status_code == 404


# ── list endpoint ─────────────────────────────────────────────────────────────


async def test_list_returns_pagination_meta(authed_client):
    r = await authed_client.get("/api/v1/subscriptions?limit=10&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "total" in body["meta"]
    assert body["meta"]["limit"] == 10
    assert body["meta"]["offset"] == 0


async def test_cancelled_subscription_hidden_by_default(authed_client):
    csrf = _csrf(authed_client)

    # Create a cancelled subscription
    r = await authed_client.post(
        "/api/v1/subscriptions",
        json=_create_payload(service_name="CancelledSVC", status="cancelled"),
        headers={"x-csrf-token": csrf},
    )
    assert r.status_code == 201
    cancelled_id = r.json()["data"]["id"]

    try:
        # List without show_cancelled — should not appear
        r = await authed_client.get("/api/v1/subscriptions?show_cancelled=false")
        ids = [s["id"] for s in r.json()["data"]]
        assert cancelled_id not in ids

        # List with show_cancelled=true — should appear
        r = await authed_client.get("/api/v1/subscriptions?show_cancelled=true")
        ids = [s["id"] for s in r.json()["data"]]
        assert cancelled_id in ids
    finally:
        # Cleanup
        await authed_client.delete(
            f"/api/v1/subscriptions/{cancelled_id}",
            headers={"x-csrf-token": csrf},
        )


# ── exchange_rate ─────────────────────────────────────────────────────────────


async def test_create_with_exchange_rate(authed_client):
    csrf = _csrf(authed_client)

    r = await authed_client.post(
        "/api/v1/subscriptions",
        json=_create_payload(
            service_name="AWSTest",
            currency="USD",
            cost="99.00",
            exchange_rate="31.500000",
        ),
        headers={"x-csrf-token": csrf},
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    sub_id = data["id"]
    assert data["currency"] == "USD"
    assert float(data["exchange_rate"]) == pytest.approx(31.5, rel=1e-4)

    # Cleanup
    await authed_client.delete(
        f"/api/v1/subscriptions/{sub_id}",
        headers={"x-csrf-token": csrf},
    )
