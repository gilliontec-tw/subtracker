import os

import httpx
import pytest
from api.main import app
from infrastructure.auth.password import hash_password
from infrastructure.database.models import Base, UserModel
from infrastructure.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _derive_test_url() -> str:
    base = os.environ["DATABASE_URL"]
    # postgresql+asyncpg://user:pass@host/dbname -> .../dbname_test
    # Requires: CREATE DATABASE subtrack_test; (run once in PostgreSQL)
    idx = base.rfind("/")
    rest = base[idx + 1 :]
    if "?" in rest:
        db_name, params = rest.split("?", 1)
        return base[: idx + 1] + db_name + "_test?" + params
    return base[: idx + 1] + rest + "_test"


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", _derive_test_url())

_engine = create_async_engine(TEST_DATABASE_URL, pool_size=5)
_Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    async with _Session() as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
async def _setup_test_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as session:
        session.add(
            UserModel(
                email="admin@test.com",
                display_name="Test Admin",
                password_hash=hash_password("testpass123"),
                role="admin",
                can_create=True,
                can_update=True,
                can_delete=True,
            )
        )
        await session.commit()
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


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
