# Plan 1: Backend Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete backend infrastructure layer: domain entities, PostgreSQL models, Alembic migrations, Redis client, JWT auth, CSRF middleware, and the four auth API endpoints (`/login`, `/logout`, `/refresh`, `/me`).

**Architecture:** Clean architecture — domain entities and exceptions live in `src/domain/`, infrastructure concerns (DB models, session, Redis, password hashing, JWT) in `src/infrastructure/`, HTTP concerns (schemas, routers, middleware, exception handlers, dependencies) in `src/api/`. Each layer depends only on the layer below it; nothing in `domain/` imports from `infrastructure/` or `api/`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async + asyncpg, Alembic, Redis (redis-py async), bcrypt, PyJWT, Pydantic v2, slowapi

---

## File Map

**Create:**
```
backend/
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
└── src/
    ├── api/
    │   ├── dependencies.py
    │   ├── exception_handlers.py
    │   ├── middleware/
    │   │   └── csrf.py
    │   └── v1/
    │       ├── routers/
    │       │   └── auth.py
    │       └── schemas/
    │           └── auth.py
    ├── domain/
    │   ├── entities/
    │   │   └── user.py
    │   ├── exceptions.py
    │   └── repositories/
    │       └── user_repository.py
    └── infrastructure/
        ├── auth/
        │   ├── jwt_service.py
        │   └── password.py
        ├── cache/
        │   └── redis_client.py
        └── database/
            ├── models.py
            ├── session.py
            └── repositories/
                └── user_repository.py
tests/
├── unit/
│   ├── test_user_entity.py
│   ├── test_exceptions.py
│   ├── test_password.py
│   ├── test_jwt_service.py
│   └── test_csrf.py
└── integration/
    └── test_auth_endpoints.py
```

**Modify:**
- `src/api/main.py` — add lifespan, register CSRF middleware, exception handlers, auth router

---

## Context: Existing Code

`src/api/config.py` already has these settings (exact field names — use them as-is):
```python
settings.database_url          # str
settings.redis_url             # str
settings.jwt_access_secret_key  # str
settings.jwt_refresh_secret_key # str
settings.jwt_access_expire_minutes  # int (default 30)
settings.jwt_refresh_expire_days    # int (default 7)
settings.cors_origins          # list[str]
settings.app_env               # str ("production" | "development")
```

`src/api/main.py` currently creates a FastAPI app with CORS. Tasks 8–10 will modify it.

`pyproject.toml` has `pythonpath = ["src"]` for pytest, so all imports start from `src/` root (e.g., `from domain.entities.user import User`).

---

## Task 1: Domain Entities + Exceptions

**Files:**
- Create: `src/domain/entities/user.py`
- Create: `src/domain/exceptions.py`
- Create: `tests/unit/test_user_entity.py`
- Create: `tests/unit/test_exceptions.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_user_entity.py
from domain.entities.user import User


def test_user_defaults_have_none_id():
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash="hash",
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
        is_active=True,
    )
    assert user.id is None
    assert user.invite_token is None
    assert user.invite_token_expires_at is None


def test_user_with_admin_role():
    user = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
        role="admin",
        can_create=True,
        can_update=True,
        can_delete=True,
        is_active=True,
    )
    assert user.role == "admin"
    assert user.can_create is True
```

```python
# tests/unit/test_exceptions.py
from domain.exceptions import (
    DomainException,
    ForbiddenException,
    NotAuthenticatedException,
    NotFoundException,
)


def test_not_authenticated_is_domain_exception():
    ex = NotAuthenticatedException()
    assert isinstance(ex, DomainException)
    assert isinstance(ex, Exception)


def test_forbidden_is_domain_exception():
    ex = ForbiddenException()
    assert isinstance(ex, DomainException)


def test_not_found_is_domain_exception():
    ex = NotFoundException()
    assert isinstance(ex, DomainException)
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_user_entity.py tests/unit/test_exceptions.py -v
```
Expected: `ModuleNotFoundError: No module named 'domain.entities.user'`

- [ ] **Step 3: Implement User entity**

```python
# src/domain/entities/user.py
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    email: str
    display_name: str
    password_hash: str
    role: str  # 'admin' | 'manager' | 'user'
    can_create: bool
    can_update: bool
    can_delete: bool
    is_active: bool
    id: int | None = None
    invite_token: str | None = None
    invite_token_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 4: Implement exceptions**

```python
# src/domain/exceptions.py


class DomainException(Exception):
    pass


class NotAuthenticatedException(DomainException):
    pass


class ForbiddenException(DomainException):
    pass


class NotFoundException(DomainException):
    pass
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/unit/test_user_entity.py tests/unit/test_exceptions.py -v
```
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/domain/entities/user.py src/domain/exceptions.py \
        tests/unit/test_user_entity.py tests/unit/test_exceptions.py
git commit -m "feat: add User entity and domain exceptions"
```

---

## Task 2: Password Hashing

**Files:**
- Create: `src/infrastructure/auth/password.py`
- Create: `tests/unit/test_password.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_password.py
from infrastructure.auth.password import hash_password, verify_password


def test_hash_returns_string_different_from_input():
    hashed = hash_password("secret123")
    assert isinstance(hashed, str)
    assert hashed != "secret123"


def test_verify_correct_password():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("secret123")
    assert verify_password("wrong", hashed) is False


def test_same_password_produces_different_hashes():
    h1 = hash_password("secret123")
    h2 = hash_password("secret123")
    assert h1 != h2  # bcrypt random salt
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_password.py -v
```
Expected: `ModuleNotFoundError: No module named 'infrastructure.auth.password'`

- [ ] **Step 3: Implement password module**

```python
# src/infrastructure/auth/password.py
import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/unit/test_password.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/auth/password.py tests/unit/test_password.py
git commit -m "feat: add bcrypt password hashing utility"
```

---

## Task 3: JWT Service

**Files:**
- Create: `src/infrastructure/auth/jwt_service.py`
- Create: `tests/unit/test_jwt_service.py`

The JWT module is named `jwt_service.py` (not `jwt.py`) to avoid shadowing the `jwt` package.

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_jwt_service.py
import pytest
import jwt as pyjwt

from infrastructure.auth.jwt_service import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


def test_create_access_token_returns_string():
    token = create_access_token(user_id=1, role="admin")
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token_has_correct_claims():
    token = create_access_token(user_id=42, role="manager")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "manager"
    assert payload["type"] == "access"


def test_create_refresh_token_returns_token_and_jti():
    token, jti = create_refresh_token(user_id=1)
    assert isinstance(token, str)
    assert isinstance(jti, str)
    assert len(jti) > 0


def test_decode_refresh_token_has_correct_claims():
    token, jti = create_refresh_token(user_id=99)
    payload = decode_refresh_token(token)
    assert payload["sub"] == "99"
    assert payload["jti"] == jti
    assert payload["type"] == "refresh"


def test_decode_access_token_rejects_wrong_secret():
    bad_token = pyjwt.encode({"sub": "1"}, "wrong-secret", algorithm="HS256")
    with pytest.raises(pyjwt.exceptions.InvalidSignatureError):
        decode_access_token(bad_token)


def test_access_token_cannot_decode_as_refresh():
    token = create_access_token(user_id=1, role="user")
    with pytest.raises(pyjwt.exceptions.InvalidSignatureError):
        decode_refresh_token(token)
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_jwt_service.py -v
```
Expected: `ModuleNotFoundError: No module named 'infrastructure.auth.jwt_service'`

- [ ] **Step 3: Implement JWT service**

```python
# src/infrastructure/auth/jwt_service.py
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from api.config import get_settings

settings = get_settings()


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.jwt_access_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_access_secret_key, algorithm="HS256")


def create_refresh_token(user_id: int) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "iat": _now(),
        "exp": _now() + timedelta(days=settings.jwt_refresh_expire_days),
    }
    token = jwt.encode(payload, settings.jwt_refresh_secret_key, algorithm="HS256")
    return token, jti


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_access_secret_key, algorithms=["HS256"])


def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_refresh_secret_key, algorithms=["HS256"])
```

- [ ] **Step 4: Ensure `.env` has JWT secrets set**

The `backend/.env` file must have non-empty values:
```
JWT_ACCESS_SECRET_KEY=dev-access-secret-change-me
JWT_REFRESH_SECRET_KEY=dev-refresh-secret-change-me
```
If `.env` is missing these, add them before running tests.

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/unit/test_jwt_service.py -v
```
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add src/infrastructure/auth/jwt_service.py tests/unit/test_jwt_service.py
git commit -m "feat: add JWT access/refresh token service"
```

---

## Task 4: SQLAlchemy Models + Database Session

**Files:**
- Create: `src/infrastructure/database/models.py`
- Create: `src/infrastructure/database/session.py`

No unit tests for the ORM models (they require a real DB). The Alembic migration in Task 5 validates the schema. Session correctness is validated in integration tests (Task 11).

- [ ] **Step 1: Create ORM models**

```python
# src/infrastructure/database/models.py
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    password_hash = Column(String(255))
    role = Column(String(20), nullable=False, server_default="user")
    can_create = Column(Boolean, nullable=False, server_default="false")
    can_update = Column(Boolean, nullable=False, server_default="false")
    can_delete = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")
    invite_token = Column(String(255), unique=True)
    invite_token_expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SubscriptionModel(Base):
    __tablename__ = "saas_subscriptions"

    id = Column(Integer, primary_key=True)
    service_name = Column(String(255), nullable=False)
    login_account = Column(String(255))
    expiry_date = Column(Date, nullable=False)
    notification_emails = Column(Text)  # JSON-encoded list of email strings
    notification_days = Column(Integer, server_default="30")
    cost = Column(Numeric(10, 2))
    currency = Column(String(10), server_default="TWD")
    notes = Column(Text)
    owner_name = Column(String(255))
    category = Column(String(100))
    department = Column(String(100))
    billing_cycle = Column(String(20))  # monthly|quarterly|semi_annual|annual|biennial
    payment_account = Column(String(255))
    auto_renew = Column(Boolean, server_default="false")
    trial_end_date = Column(Date)
    next_billing_date = Column(Date)
    status = Column(String(20), server_default="active")  # active|renewed|cancelled|suspended
    deleted_at = Column(DateTime(timezone=True))  # NULL = not deleted (soft delete)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payments = relationship("PaymentRecordModel", back_populates="subscription")


class PaymentRecordModel(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("saas_subscriptions.id"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, server_default="TWD")
    source = Column(String(10), nullable=False, server_default="manual")  # auto|manual
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))

    subscription = relationship("SubscriptionModel", back_populates="payments")


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    details = Column(Text)  # JSON-encoded dict
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Create database session factory**

```python
# src/infrastructure/database/session.py
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session
```

- [ ] **Step 3: Verify imports are clean**

```
python -c "from infrastructure.database.models import Base, UserModel, SubscriptionModel, PaymentRecordModel, AuditLogModel; print('OK')"
```
Run from `backend/` with the venv active. Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/infrastructure/database/models.py src/infrastructure/database/session.py
git commit -m "feat: add SQLAlchemy ORM models and async session factory"
```

---

## Task 5: Alembic Setup + Initial Migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/001_initial_schema.py`

Run all commands from `backend/`.

- [ ] **Step 1: Create `alembic.ini`**

```ini
# alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: Create `alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 3: Create `alembic/env.py`**

```python
# alembic/env.py
import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.config import get_settings
from infrastructure.database.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Create initial migration**

```python
# alembic/versions/001_initial_schema.py
"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("can_create", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_update", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_delete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("invite_token", sa.String(255), unique=True),
        sa.Column("invite_token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "saas_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_name", sa.String(255), nullable=False),
        sa.Column("login_account", sa.String(255)),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("notification_emails", sa.Text()),
        sa.Column("notification_days", sa.Integer(), server_default="30"),
        sa.Column("cost", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(10), server_default="TWD"),
        sa.Column("notes", sa.Text()),
        sa.Column("owner_name", sa.String(255)),
        sa.Column("category", sa.String(100)),
        sa.Column("department", sa.String(100)),
        sa.Column("billing_cycle", sa.String(20)),
        sa.Column("payment_account", sa.String(255)),
        sa.Column("auto_renew", sa.Boolean(), server_default="false"),
        sa.Column("trial_end_date", sa.Date()),
        sa.Column("next_billing_date", sa.Date()),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_saas_subscriptions_expiry_date", "saas_subscriptions", ["expiry_date"])
    op.create_index("ix_saas_subscriptions_status", "saas_subscriptions", ["status"])

    op.create_table(
        "payment_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            sa.ForeignKey("saas_subscriptions.id"),
            nullable=False,
        ),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TWD"),
        sa.Column("source", sa.String(10), nullable=False, server_default="manual"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
    )
    op.create_index(
        "ix_payment_records_subscription_id", "payment_records", ["subscription_id"]
    )
    op.create_index("ix_payment_records_payment_date", "payment_records", ["payment_date"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.Integer()),
        sa.Column("details", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("payment_records")
    op.drop_table("saas_subscriptions")
    op.drop_table("users")
```

- [ ] **Step 5: Run migration against the dev database**

`backend/.env` must have `DATABASE_URL` pointing at a live PostgreSQL. If using Docker:
```bash
docker compose -f ../docker-compose.yml -f ../docker-compose.dev.yml up db -d
```

Then run (from `backend/`):
```
alembic upgrade head
```
Expected output ends with: `Running upgrade  -> 001, initial schema`

- [ ] **Step 6: Verify tables exist**

```bash
docker exec -it <db-container-name> psql -U subtrack -d subtrack -c "\dt"
```
Expected: lists `users`, `saas_subscriptions`, `payment_records`, `audit_log`

- [ ] **Step 7: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: add Alembic setup and initial schema migration"
```

---

## Task 6: Redis Client

**Files:**
- Create: `src/infrastructure/cache/redis_client.py`

No unit tests needed — the Redis client is just a connection factory. Integration tests in Task 11 will exercise it.

- [ ] **Step 1: Create Redis client module**

```python
# src/infrastructure/cache/redis_client.py
import redis.asyncio as aioredis

from api.config import get_settings

settings = get_settings()

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis
```

- [ ] **Step 2: Verify import**

```
python -c "from infrastructure.cache.redis_client import get_redis; print('OK')"
```
Run from `backend/` with venv active. Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/infrastructure/cache/redis_client.py
git commit -m "feat: add async Redis client factory"
```

---

## Task 7: User Repository (Interface + SQL Implementation)

**Files:**
- Create: `src/domain/repositories/user_repository.py`
- Create: `src/infrastructure/database/repositories/user_repository.py`
- Create: `tests/unit/test_user_repository_interface.py`

- [ ] **Step 1: Write failing tests for the interface**

```python
# tests/unit/test_user_repository_interface.py
import pytest

from domain.repositories.user_repository import UserRepository


def test_user_repository_is_abstract():
    with pytest.raises(TypeError):
        UserRepository()  # type: ignore[abstract]


def test_concrete_must_implement_get_by_email():
    class Incomplete(UserRepository):
        async def get_by_id(self, id): ...
        async def list_all(self): ...
        async def save(self, entity): ...
        async def delete(self, id): ...
        # missing get_by_email and get_by_invite_token

    with pytest.raises(TypeError):
        Incomplete()
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_user_repository_interface.py -v
```
Expected: `ModuleNotFoundError: No module named 'domain.repositories.user_repository'`

- [ ] **Step 3: Implement UserRepository interface**

```python
# src/domain/repositories/user_repository.py
from abc import abstractmethod

from domain.entities.user import User
from domain.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, int]):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_invite_token(self, token: str) -> User | None: ...
```

- [ ] **Step 4: Run interface tests to verify they pass**

```
pytest tests/unit/test_user_repository_interface.py -v
```
Expected: 2 passed

- [ ] **Step 5: Implement SQL user repository**

```python
# src/infrastructure/database/repositories/user_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.database.models import UserModel


def _to_entity(m: UserModel) -> User:
    return User(
        id=m.id,
        email=m.email,
        display_name=m.display_name,
        password_hash=m.password_hash or "",
        role=m.role,
        can_create=m.can_create,
        can_update=m.can_update,
        can_delete=m.can_delete,
        is_active=m.is_active,
        invite_token=m.invite_token,
        invite_token_expires_at=m.invite_token_expires_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: int) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_invite_token(self, token: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.invite_token == token)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(UserModel))
        return [_to_entity(m) for m in result.scalars().all()]

    async def save(self, entity: User) -> User:
        if entity.id is not None:
            result = await self._session.execute(
                select(UserModel).where(UserModel.id == entity.id)
            )
            model = result.scalar_one()
            model.email = entity.email
            model.display_name = entity.display_name
            model.password_hash = entity.password_hash
            model.role = entity.role
            model.can_create = entity.can_create
            model.can_update = entity.can_update
            model.can_delete = entity.can_delete
            model.is_active = entity.is_active
            model.invite_token = entity.invite_token
            model.invite_token_expires_at = entity.invite_token_expires_at
        else:
            model = UserModel(
                email=entity.email,
                display_name=entity.display_name,
                password_hash=entity.password_hash,
                role=entity.role,
                can_create=entity.can_create,
                can_update=entity.can_update,
                can_delete=entity.can_delete,
                is_active=entity.is_active,
                invite_token=entity.invite_token,
                invite_token_expires_at=entity.invite_token_expires_at,
            )
            self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, id: int) -> None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == id)
        )
        model = result.scalar_one()
        await self._session.delete(model)
        await self._session.commit()
```

- [ ] **Step 6: Run all unit tests**

```
pytest tests/unit/ -v
```
Expected: all existing tests + 2 new = all pass

- [ ] **Step 7: Commit**

```bash
git add src/domain/repositories/user_repository.py \
        src/infrastructure/database/repositories/user_repository.py \
        tests/unit/test_user_repository_interface.py
git commit -m "feat: add UserRepository interface and SQL implementation"
```

---

## Task 8: Exception Handlers + Update main.py

**Files:**
- Create: `src/api/exception_handlers.py`
- Modify: `src/api/main.py`
- Create: `tests/unit/test_exception_handlers.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_exception_handlers.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.exception_handlers import register_exception_handlers
from domain.exceptions import ForbiddenException, NotAuthenticatedException, NotFoundException

_app = FastAPI()
register_exception_handlers(_app)


@_app.get("/not-auth")
def raise_not_auth():
    raise NotAuthenticatedException()


@_app.get("/forbidden")
def raise_forbidden():
    raise ForbiddenException()


@_app.get("/not-found")
def raise_not_found():
    raise NotFoundException()


client = TestClient(_app, raise_server_exceptions=False)


def test_not_authenticated_returns_401():
    r = client.get("/not-auth")
    assert r.status_code == 401
    body = r.json()
    assert body["success"] is False
    assert body["data"] is None


def test_forbidden_returns_403():
    r = client.get("/forbidden")
    assert r.status_code == 403
    body = r.json()
    assert body["success"] is False


def test_not_found_returns_404():
    r = client.get("/not-found")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_exception_handlers.py -v
```
Expected: `ModuleNotFoundError: No module named 'api.exception_handlers'`

- [ ] **Step 3: Implement exception handlers module**

```python
# src/api/exception_handlers.py
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from domain.exceptions import ForbiddenException, NotAuthenticatedException, NotFoundException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotAuthenticatedException)
    async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
        return JSONResponse(
            status_code=401,
            content={"success": False, "data": None, "message": "請先登入", "meta": None},
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_handler(request: Request, exc: ForbiddenException):
        return JSONResponse(
            status_code=403,
            content={"success": False, "data": None, "message": "權限不足", "meta": None},
        )

    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException):
        return JSONResponse(
            status_code=404,
            content={"success": False, "data": None, "message": "資源不存在", "meta": None},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "message": "伺服器錯誤，請稍後再試",
                "meta": None,
            },
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/unit/test_exception_handlers.py -v
```
Expected: 3 passed

- [ ] **Step 5: Update main.py to register exception handlers**

Replace the entire `src/api/main.py` with:

```python
# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.exception_handlers import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="SubTrack API",
        version="1.0.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )

    register_exception_handlers(app)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 6: Run all unit tests including health check**

```
pytest tests/unit/ -v
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/api/exception_handlers.py src/api/main.py \
        tests/unit/test_exception_handlers.py
git commit -m "feat: add domain exception handlers and register in app"
```

---

## Task 9: CSRF Middleware

**Files:**
- Create: `src/api/middleware/csrf.py`
- Create: `tests/unit/test_csrf.py`
- Modify: `src/api/main.py` — add `CSRFMiddleware`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_csrf.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, CSRFMiddleware

_app = FastAPI()
_app.add_middleware(CSRFMiddleware)


@_app.get("/safe")
def safe_get():
    return {"ok": True}


@_app.post("/unsafe")
def unsafe_post():
    return {"ok": True}


@_app.post("/auth/login")
def login_exempt():
    return {"ok": True}


client = TestClient(_app, raise_server_exceptions=False)


def test_get_passes_without_csrf():
    r = client.get("/safe")
    assert r.status_code == 200


def test_post_without_any_token_returns_403():
    r = client.post("/unsafe")
    assert r.status_code == 403
    assert r.json()["success"] is False


def test_post_with_matching_tokens_passes():
    r = client.post(
        "/unsafe",
        cookies={CSRF_COOKIE_NAME: "abc123"},
        headers={CSRF_HEADER_NAME: "abc123"},
    )
    assert r.status_code == 200


def test_post_with_mismatched_tokens_returns_403():
    r = client.post(
        "/unsafe",
        cookies={CSRF_COOKIE_NAME: "abc123"},
        headers={CSRF_HEADER_NAME: "different"},
    )
    assert r.status_code == 403


def test_login_path_is_exempt():
    r = client.post("/auth/login")
    assert r.status_code == 200


def test_post_with_only_header_no_cookie_returns_403():
    r = client.post("/unsafe", headers={CSRF_HEADER_NAME: "abc123"})
    assert r.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_csrf.py -v
```
Expected: `ModuleNotFoundError: No module named 'api.middleware.csrf'`

- [ ] **Step 3: Implement CSRF middleware**

```python
# src/api/middleware/csrf.py
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"

# Paths exempt from CSRF — login and refresh create/renew the session itself
CSRF_EXEMPT_PATHS = {"/api/v1/auth/login", "/api/v1/auth/refresh"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in CSRF_SAFE_METHODS or request.url.path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if (
            not cookie_token
            or not header_token
            or not secrets.compare_digest(cookie_token, header_token)
        ):
            return JSONResponse(
                {"success": False, "data": None, "message": "CSRF token 無效", "meta": None},
                status_code=403,
            )

        return await call_next(request)
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/unit/test_csrf.py -v
```
Expected: 6 passed

- [ ] **Step 5: Wire CSRFMiddleware into main.py**

The middleware must be added **after** CORSMiddleware (Starlette processes middleware in reverse registration order — last added runs first):

```python
# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.exception_handlers import register_exception_handlers
from api.middleware.csrf import CSRFMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="SubTrack API",
        version="1.0.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )
    app.add_middleware(CSRFMiddleware)

    register_exception_handlers(app)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 6: Run all unit tests**

```
pytest tests/unit/ -v
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/api/middleware/csrf.py src/api/main.py tests/unit/test_csrf.py
git commit -m "feat: add CSRF double-submit cookie middleware"
```

---

## Task 10: Auth API Endpoints + Dependencies

**Files:**
- Create: `src/api/v1/schemas/auth.py`
- Create: `src/api/dependencies.py`
- Create: `src/api/v1/routers/auth.py`
- Modify: `src/api/main.py` — include auth router

- [ ] **Step 1: Create auth schemas**

```python
# src/api/v1/schemas/auth.py
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    can_create: bool
    can_update: bool
    can_delete: bool
```

- [ ] **Step 2: Create dependencies**

```python
# src/api/dependencies.py
from typing import Annotated

import jwt
from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.exceptions import ForbiddenException, NotAuthenticatedException
from infrastructure.auth.jwt_service import decode_access_token
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.session import get_db


async def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not access_token:
        raise NotAuthenticatedException()
    try:
        payload = decode_access_token(access_token)
    except jwt.PyJWTError:
        raise NotAuthenticatedException()
    user_id = int(payload["sub"])
    repo = SqlUserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise NotAuthenticatedException()
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise ForbiddenException()
    return current_user


async def require_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in ("admin", "manager"):
        raise ForbiddenException()
    return current_user
```

- [ ] **Step 3: Create auth router**

```python
# src/api/v1/routers/auth.py
import secrets
from datetime import UTC, datetime

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.dependencies import get_current_user
from api.v1.schemas.auth import LoginRequest, UserResponse
from api.v1.schemas.base import ApiResponse
from domain.entities.user import User
from domain.exceptions import NotAuthenticatedException
from infrastructure.auth.jwt_service import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from infrastructure.auth.password import verify_password
from infrastructure.cache.redis_client import get_redis
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.session import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_FAIL_TTL = 60  # seconds window for login failure rate limit
_MAX_FAILS = 5


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    is_prod = settings.app_env == "production"
    response.set_cookie(
        "access_token", access_token,
        httponly=True, secure=is_prod, samesite="lax",
        max_age=settings.jwt_access_expire_minutes * 60,
    )
    response.set_cookie(
        "refresh_token", refresh_token,
        httponly=True, secure=is_prod, samesite="lax",
        max_age=settings.jwt_refresh_expire_days * 86400,
    )
    response.set_cookie(
        "csrf_token", csrf_token,
        httponly=False, secure=is_prod, samesite="lax",
        max_age=settings.jwt_refresh_expire_days * 86400,
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> ApiResponse[UserResponse]:
    ip = request.client.host if request.client else "unknown"
    fail_key = f"login_fail:{ip}"

    fail_count = await redis.get(fail_key)
    if fail_count and int(fail_count) >= _MAX_FAILS:
        return ApiResponse.fail("登入嘗試次數過多，請一分鐘後再試")  # type: ignore[return-value]

    repo = SqlUserRepository(db)
    user = await repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user.password_hash):
        await redis.incr(fail_key)
        await redis.expire(fail_key, _FAIL_TTL)
        raise NotAuthenticatedException()

    await redis.delete(fail_key)

    access_token = create_access_token(user.id, user.role)
    refresh_token, _ = create_refresh_token(user.id)
    csrf_token = secrets.token_urlsafe(32)

    _set_auth_cookies(response, access_token, refresh_token, csrf_token)

    return ApiResponse.ok(
        data=UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            can_create=user.can_create,
            can_update=user.can_update,
            can_delete=user.can_delete,
        )
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    redis: aioredis.Redis = Depends(get_redis),
) -> ApiResponse[None]:
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                ttl = exp - int(datetime.now(UTC).timestamp())
                if ttl > 0:
                    await redis.set(f"blacklist:{jti}", "1", ex=ttl)
        except Exception:
            pass  # invalid token — still clear cookies

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("csrf_token")
    return ApiResponse.ok(message="已登出")


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> ApiResponse[None]:
    if not refresh_token:
        raise NotAuthenticatedException()
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        raise NotAuthenticatedException()

    jti = payload.get("jti")
    if jti and await redis.get(f"blacklist:{jti}"):
        raise NotAuthenticatedException()

    user_id = int(payload["sub"])
    repo = SqlUserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise NotAuthenticatedException()

    new_access = create_access_token(user.id, user.role)
    is_prod = settings.app_env == "production"
    response.set_cookie(
        "access_token", new_access,
        httponly=True, secure=is_prod, samesite="lax",
        max_age=settings.jwt_access_expire_minutes * 60,
    )
    return ApiResponse.ok(message="Token 已更新")


@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    return ApiResponse.ok(
        data=UserResponse(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
            role=current_user.role,
            can_create=current_user.can_create,
            can_update=current_user.can_update,
            can_delete=current_user.can_delete,
        )
    )
```

- [ ] **Step 4: Wire auth router into main.py**

```python
# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.exception_handlers import register_exception_handlers
from api.middleware.csrf import CSRFMiddleware
from api.v1.routers.auth import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="SubTrack API",
        version="1.0.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )
    app.add_middleware(CSRFMiddleware)

    register_exception_handlers(app)
    app.include_router(auth_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Run all unit tests**

```
pytest tests/unit/ -v
```
Expected: all pass (unit tests do not need DB/Redis)

- [ ] **Step 6: Commit**

```bash
git add src/api/v1/schemas/auth.py src/api/dependencies.py \
        src/api/v1/routers/auth.py src/api/main.py
git commit -m "feat: add auth endpoints (login, logout, refresh, me) and dependencies"
```

---

## Task 11: Integration Tests for Auth Flow

**Files:**
- Create: `tests/integration/test_auth_endpoints.py`

Integration tests require a live PostgreSQL and Redis. Run with `DATABASE_URL` and `REDIS_URL` set (use the dev Docker stack).

- [ ] **Step 1: Start dev services**

```bash
# From repo root
docker compose -f docker-compose.yml -f docker-compose.dev.yml up db redis -d
```

- [ ] **Step 2: Seed a test admin user**

```python
# Run once: scripts/seed_test_user.py
# (create this file temporarily — do NOT commit it)
import asyncio
from infrastructure.auth.password import hash_password
from infrastructure.database.models import UserModel
from infrastructure.database.session import AsyncSessionFactory


async def seed():
    async with AsyncSessionFactory() as session:
        user = UserModel(
            email="admin@test.com",
            display_name="Test Admin",
            password_hash=hash_password("testpass123"),
            role="admin",
            can_create=True,
            can_update=True,
            can_delete=True,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print("Seeded admin@test.com / testpass123")


asyncio.run(seed())
```

Run from `backend/`: `python scripts/seed_test_user.py`

- [ ] **Step 3: Write integration tests**

```python
# tests/integration/test_auth_endpoints.py
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_me_without_auth_returns_401():
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["success"] is False


def test_login_with_wrong_password_returns_401():
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "wrong"},
    )
    assert r.status_code == 401


def test_login_with_nonexistent_email_returns_401():
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "noexist@test.com", "password": "any"},
    )
    assert r.status_code == 401


def test_full_login_me_logout_flow():
    # Login
    r = client.post(
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
    r2 = client.get("/api/v1/auth/me")
    assert r2.status_code == 200
    assert r2.json()["data"]["email"] == "admin@test.com"

    # Logout
    r3 = client.post(
        "/api/v1/auth/logout",
        headers={"x-csrf-token": csrf},
    )
    assert r3.status_code == 200

    # /me after logout should fail
    r4 = client.get("/api/v1/auth/me")
    assert r4.status_code == 401
```

- [ ] **Step 4: Run integration tests**

```
pytest tests/integration/test_auth_endpoints.py -v
```
Expected: 4 passed

- [ ] **Step 5: Run full test suite**

```
pytest tests/ -v
```
Expected: all unit + integration tests pass

- [ ] **Step 6: Run ruff lint check**

```
ruff check src/ tests/
```
Expected: `All checks passed.`

- [ ] **Step 7: Commit**

```bash
git add tests/integration/test_auth_endpoints.py
git commit -m "test: add auth endpoint integration tests"
```

---

## Checklist: Spec Coverage

| Spec requirement | Task |
|---|---|
| SQLAlchemy async models (users, subscriptions, payment_records, audit_log) | Task 4 |
| Alembic setup + initial migration | Task 5 |
| Index on expiry_date, status, payment_date, email, created_at | Task 5 |
| Soft delete (deleted_at) on subscriptions | Task 4 + 5 |
| Redis client | Task 6 |
| JWT access token (30 min, httpOnly cookie) | Task 3 + 10 |
| JWT refresh token (7 days, httpOnly cookie) | Task 3 + 10 |
| CSRF double-submit cookie | Task 9 |
| bcrypt rounds >= 12 | Task 2 |
| Login rate limit (5 failures/min/IP, Redis) | Task 10 |
| Refresh token revocation via Redis jti blacklist | Task 10 |
| Exception handlers (401/403/404/500, unified format) | Task 8 |
| `/api/v1/auth/login` | Task 10 |
| `/api/v1/auth/logout` | Task 10 |
| `/api/v1/auth/refresh` | Task 10 |
| `/api/v1/auth/me` | Task 10 |
| `get_current_user`, `require_admin`, `require_manager` dependencies | Task 10 |
| User entity (dataclass, all fields) | Task 1 |
| Domain exceptions hierarchy | Task 1 |
| UserRepository interface + SQL implementation | Task 7 |
| cookie SameSite=Lax, HttpOnly, Secure (prod) | Task 10 |
| JWT secrets separated (access vs refresh) | Task 3 |
