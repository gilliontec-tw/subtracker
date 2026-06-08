# System Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow admins to configure SMTP, App URL, sender display name, and notification schedule via a web UI stored in a `system_settings` DB table, with per-key fallback to `.env` values.

**Architecture:** Key-value table (`system_settings`) stores settings; `SettingsService` reads each key from DB first, falls back to `.env`. SMTP password is Fernet-encrypted in DB using `SETTINGS_ENCRYPTION_KEY` from `.env`. Admin-only REST API + React settings page.

**Tech Stack:** Python `cryptography` (Fernet), SQLAlchemy async upsert (PostgreSQL dialect), FastAPI `Depends`, React 19 + react-hook-form + TanStack Query v5.

---

## File Map

**Create (backend):**
- `backend/src/domain/entities/system_setting.py` — `SystemSetting` dataclass
- `backend/src/domain/repositories/system_setting_repository.py` — ABC interface
- `backend/src/infrastructure/database/repositories/system_setting_repository.py` — SQL implementation
- `backend/src/application/services/settings_service.py` — core logic: DB→env fallback, Fernet encrypt/decrypt, `SmtpConfig` dataclass
- `backend/src/api/v1/schemas/admin_settings.py` — Pydantic request/response schemas
- `backend/src/api/v1/routers/admin_settings.py` — GET/PUT/POST test-email endpoints
- `backend/alembic/versions/004_add_system_settings.py` — migration
- `backend/tests/unit/test_settings_service.py` — unit tests

**Modify (backend):**
- `backend/pyproject.toml` — add `cryptography>=42.0.0`
- `backend/src/infrastructure/database/models.py` — add `SystemSettingModel`
- `backend/src/api/config.py` — add `settings_encryption_key`, `smtp_sender_name`, `notification_cron_hour`, `notification_cron_minute`
- `backend/src/infrastructure/smtp/smtp_email_sender.py` — add optional `sender_name` param
- `backend/src/api/dependencies.py` — add `get_settings_service` dependency
- `backend/src/api/main.py` — register `admin_settings` router
- `backend/src/api/v1/routers/auth.py` — use `SettingsService` in `forgot_password`
- `backend/src/infrastructure/scheduler/main.py` — read SMTP + cron from `SettingsService` at startup

**Create (frontend):**
- `frontend/src/api/admin_settings.ts` — API functions
- `frontend/src/pages/SystemSettingsPage.tsx` — settings page

**Modify (frontend):**
- `frontend/src/App.tsx` — add `/settings` route
- `frontend/src/layouts/AppLayout.tsx` — add 系統設定 nav link

---

## Task 1: Add `cryptography` dependency + DB model + Alembic migration

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/src/infrastructure/database/models.py`
- Create: `backend/alembic/versions/004_add_system_settings.py`

- [ ] **Step 1: Add `cryptography` to dependencies**

In `backend/pyproject.toml`, add to `dependencies` list:
```toml
"cryptography>=42.0.0",
```

- [ ] **Step 2: Install the new dependency**

Run from `backend/` with venv active:
```bash
pip install -e ".[dev]"
```
Expected: installs `cryptography` without errors.

- [ ] **Step 3: Add `SystemSettingModel` to models.py**

In `backend/src/infrastructure/database/models.py`, add at the end of the file:
```python
class SystemSettingModel(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 4: Create Alembic migration**

Create `backend/alembic/versions/004_add_system_settings.py`:
```python
"""add system_settings table

Revision ID: 004
Revises: 003
Create Date: 2026-06-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
```

- [ ] **Step 5: Run migration to verify SQL is valid**

```bash
alembic upgrade head
```
Expected: `Running upgrade 003 -> 004, add system_settings table` with no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/src/infrastructure/database/models.py backend/alembic/versions/004_add_system_settings.py
git commit -m "feat: add system_settings table and cryptography dependency"
```

---

## Task 2: Domain layer — entity + repository interface

**Files:**
- Create: `backend/src/domain/entities/system_setting.py`
- Create: `backend/src/domain/repositories/system_setting_repository.py`

- [ ] **Step 1: Create the entity**

Create `backend/src/domain/entities/system_setting.py`:
```python
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SystemSetting:
    key: str
    value: str | None
    updated_at: datetime | None = None
```

- [ ] **Step 2: Create the repository interface**

Create `backend/src/domain/repositories/system_setting_repository.py`:
```python
from abc import ABC, abstractmethod


class SystemSettingRepository(ABC):
    @abstractmethod
    async def get(self, key: str) -> str | None: ...

    @abstractmethod
    async def set(self, key: str, value: str) -> None: ...

    @abstractmethod
    async def get_all(self) -> dict[str, str]: ...
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/domain/entities/system_setting.py backend/src/domain/repositories/system_setting_repository.py
git commit -m "feat: system_setting domain entity and repository interface"
```

---

## Task 3: SQL repository implementation

**Files:**
- Create: `backend/src/infrastructure/database/repositories/system_setting_repository.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_system_setting_repository.py`:

> Note: SQL repositories are NOT unit-tested in this project (they need a real DB). This task has no unit test — the repository is verified by the integration test in Task 4 (SettingsService tests mock it).

Skip to Step 2.

- [ ] **Step 2: Implement the repository**

Create `backend/src/infrastructure/database/repositories/system_setting_repository.py`:
```python
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.system_setting_repository import SystemSettingRepository
from infrastructure.database.models import SystemSettingModel


class SqlSystemSettingRepository(SystemSettingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> str | None:
        result = await self._session.execute(
            select(SystemSettingModel.value).where(SystemSettingModel.key == key)
        )
        return result.scalar_one_or_none()

    async def set(self, key: str, value: str) -> None:
        stmt = (
            pg_insert(SystemSettingModel)
            .values(key=key, value=value, updated_at=datetime.now(UTC))
            .on_conflict_do_update(
                index_elements=["key"],
                set_={"value": value, "updated_at": datetime.now(UTC)},
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_all(self) -> dict[str, str]:
        result = await self._session.execute(
            select(SystemSettingModel.key, SystemSettingModel.value)
        )
        return {row.key: row.value for row in result.all() if row.value is not None}
```

- [ ] **Step 3: Verify import is clean**

```bash
cd backend && python -c "from infrastructure.database.repositories.system_setting_repository import SqlSystemSettingRepository; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/src/infrastructure/database/repositories/system_setting_repository.py
git commit -m "feat: SqlSystemSettingRepository implementation"
```

---

## Task 4: SettingsService + unit tests

**Files:**
- Create: `backend/src/application/services/settings_service.py`
- Create: `backend/tests/unit/test_settings_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_settings_service.py`:
```python
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet

from application.services.settings_service import SettingsService
from api.config import Settings


def make_env(settings_encryption_key: str = "", **kwargs) -> Settings:
    defaults = dict(
        smtp_host="env-host",
        smtp_port=587,
        smtp_user="env-user",
        smtp_password="env-pass",
        smtp_from="noreply@corp.com",
        smtp_sender_name="SubTrack",
        app_url="http://localhost",
        notification_cron_hour=8,
        notification_cron_minute=0,
        settings_encryption_key=settings_encryption_key,
        database_url="",
        redis_url="",
        jwt_access_secret_key="",
        jwt_refresh_secret_key="",
        jwt_access_expire_minutes=30,
        jwt_refresh_expire_days=7,
        cors_origins=[],
        app_env="development",
    )
    defaults.update(kwargs)
    return Settings.model_construct(**defaults)


@pytest.mark.asyncio
async def test_get_returns_db_value_when_present():
    repo = AsyncMock()
    repo.get.return_value = "smtp.gmail.com"
    svc = SettingsService(repo, make_env())
    assert await svc.get("smtp_host") == "smtp.gmail.com"


@pytest.mark.asyncio
async def test_get_falls_back_to_env_when_db_empty():
    repo = AsyncMock()
    repo.get.return_value = None
    svc = SettingsService(repo, make_env(smtp_host="env.smtp.com"))
    assert await svc.get("smtp_host") == "env.smtp.com"


@pytest.mark.asyncio
async def test_get_smtp_password_decrypts_db_value():
    key = Fernet.generate_key()
    encrypted = Fernet(key).encrypt(b"secret123").decode()
    repo = AsyncMock()
    repo.get.return_value = encrypted
    svc = SettingsService(repo, make_env(settings_encryption_key=key.decode()))
    assert await svc.get("smtp_password") == "secret123"


@pytest.mark.asyncio
async def test_get_smtp_password_falls_back_to_env_when_no_key():
    repo = AsyncMock()
    repo.get.return_value = None
    svc = SettingsService(repo, make_env(smtp_password="env-pass", settings_encryption_key=""))
    assert await svc.get("smtp_password") == "env-pass"


@pytest.mark.asyncio
async def test_set_smtp_password_raises_when_no_encryption_key():
    repo = AsyncMock()
    svc = SettingsService(repo, make_env(settings_encryption_key=""))
    with pytest.raises(ValueError, match="加密金鑰"):
        await svc.set("smtp_password", "secret")


@pytest.mark.asyncio
async def test_set_smtp_password_encrypts_before_saving():
    key = Fernet.generate_key()
    repo = AsyncMock()
    svc = SettingsService(repo, make_env(settings_encryption_key=key.decode()))
    await svc.set("smtp_password", "secret123")
    saved_value = repo.set.call_args[0][1]
    decrypted = Fernet(key).decrypt(saved_value.encode()).decode()
    assert decrypted == "secret123"


@pytest.mark.asyncio
async def test_set_non_password_key_saves_directly():
    repo = AsyncMock()
    svc = SettingsService(repo, make_env())
    await svc.set("smtp_host", "smtp.example.com")
    repo.set.assert_called_once_with("smtp_host", "smtp.example.com")


@pytest.mark.asyncio
async def test_encryption_key_configured_true_when_key_set():
    repo = AsyncMock()
    key = Fernet.generate_key().decode()
    svc = SettingsService(repo, make_env(settings_encryption_key=key))
    assert svc.encryption_key_configured is True


@pytest.mark.asyncio
async def test_encryption_key_configured_false_when_key_empty():
    repo = AsyncMock()
    svc = SettingsService(repo, make_env(settings_encryption_key=""))
    assert svc.encryption_key_configured is False


@pytest.mark.asyncio
async def test_get_smtp_config_returns_resolved_values():
    repo = AsyncMock()
    repo.get.return_value = None  # all keys fall back to env
    svc = SettingsService(
        repo,
        make_env(smtp_host="host", smtp_port=465, smtp_user="user",
                 smtp_password="pass", smtp_from="from@x.com", smtp_sender_name="MyApp"),
    )
    cfg = await svc.get_smtp_config()
    assert cfg.host == "host"
    assert cfg.port == 465
    assert cfg.sender_name == "MyApp"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/unit/test_settings_service.py -v
```
Expected: `ImportError` or `ModuleNotFoundError` (SettingsService doesn't exist yet).

- [ ] **Step 3: Implement SettingsService**

Create `backend/src/application/services/settings_service.py`:
```python
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken

from api.config import Settings
from domain.repositories.system_setting_repository import SystemSettingRepository

_ENV_FALLBACKS = {
    "smtp_host": lambda s: s.smtp_host or None,
    "smtp_port": lambda s: str(s.smtp_port),
    "smtp_user": lambda s: s.smtp_user or None,
    "smtp_password": lambda s: s.smtp_password or None,
    "smtp_from": lambda s: s.smtp_from or None,
    "smtp_sender_name": lambda s: s.smtp_sender_name or "SubTrack",
    "app_url": lambda s: s.app_url or None,
    "notification_cron_hour": lambda s: str(s.notification_cron_hour),
    "notification_cron_minute": lambda s: str(s.notification_cron_minute),
}

_SMTP_PASSWORD_KEY = "smtp_password"


@dataclass
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    from_addr: str
    sender_name: str


class SettingsService:
    def __init__(self, repo: SystemSettingRepository, env: Settings) -> None:
        self._repo = repo
        self._env = env
        self._fernet = Fernet(env.settings_encryption_key.encode()) if env.settings_encryption_key else None

    @property
    def encryption_key_configured(self) -> bool:
        return self._fernet is not None

    async def get(self, key: str) -> str | None:
        db_value = await self._repo.get(key)
        if db_value is not None:
            if key == _SMTP_PASSWORD_KEY and self._fernet:
                try:
                    return self._fernet.decrypt(db_value.encode()).decode()
                except InvalidToken:
                    return None
            elif key == _SMTP_PASSWORD_KEY:
                # DB has encrypted value but no key to decrypt — skip
                return None
            return db_value
        fallback_fn = _ENV_FALLBACKS.get(key)
        return fallback_fn(self._env) if fallback_fn else None

    async def set(self, key: str, value: str) -> None:
        if key == _SMTP_PASSWORD_KEY:
            if not self._fernet:
                raise ValueError("加密金鑰未設定（SETTINGS_ENCRYPTION_KEY），無法儲存密碼")
            value = self._fernet.encrypt(value.encode()).decode()
        await self._repo.set(key, value)

    async def get_smtp_config(self) -> SmtpConfig:
        return SmtpConfig(
            host=await self.get("smtp_host") or "",
            port=int(await self.get("smtp_port") or "587"),
            user=await self.get("smtp_user") or "",
            password=await self.get("smtp_password") or "",
            from_addr=await self.get("smtp_from") or "",
            sender_name=await self.get("smtp_sender_name") or "SubTrack",
        )
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/unit/test_settings_service.py -v
```
Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/application/services/settings_service.py backend/tests/unit/test_settings_service.py
git commit -m "feat: SettingsService with DB/env fallback and Fernet password encryption"
```

---

## Task 5: Update `config.py` + `SmtpEmailSender`

**Files:**
- Modify: `backend/src/api/config.py`
- Modify: `backend/src/infrastructure/smtp/smtp_email_sender.py`

- [ ] **Step 1: Add new fields to config.py**

Replace the entire content of `backend/src/api/config.py` with:
```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    redis_url: str = ""

    jwt_access_secret_key: str = ""
    jwt_refresh_secret_key: str = ""
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    cors_origins: list[str] = []

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_sender_name: str = "SubTrack"

    app_env: str = "production"
    app_url: str = "http://localhost:5173"

    settings_encryption_key: str = ""

    notification_cron_hour: int = 8
    notification_cron_minute: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

- [ ] **Step 2: Update SmtpEmailSender to accept sender_name**

Replace the entire content of `backend/src/infrastructure/smtp/smtp_email_sender.py` with:
```python
import asyncio
import smtplib
from email.mime.text import MIMEText

from application.interfaces.email_sender import EmailSender


class SmtpEmailSender(EmailSender):
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        sender_name: str = "",
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from = f"{sender_name} <{from_addr}>" if sender_name else from_addr

    async def send(self, to: list[str], subject: str, body: str) -> None:
        await asyncio.to_thread(self._send_sync, to, subject, body)

    def _send_sync(self, to: list[str], subject: str, body: str) -> None:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = ", ".join(to)
        with smtplib.SMTP(self._host, self._port) as server:
            server.starttls()
            server.login(self._username, self._password)
            server.sendmail(self._from, to, msg.as_string())
```

- [ ] **Step 3: Add `get_settings_service` to dependencies.py**

In `backend/src/api/dependencies.py`, add these imports at the top with the existing imports:
```python
from application.services.settings_service import SettingsService
from infrastructure.database.repositories.system_setting_repository import SqlSystemSettingRepository
```

Add this function at the end of the file:
```python
async def get_settings_service(db: AsyncSession = Depends(get_db)) -> SettingsService:
    from api.config import settings as env_settings
    repo = SqlSystemSettingRepository(db)
    return SettingsService(repo, env_settings)
```

- [ ] **Step 4: Run all existing tests**

```bash
pytest -v
```
Expected: all tests PASS (no breakage from these changes).

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/config.py backend/src/infrastructure/smtp/smtp_email_sender.py backend/src/api/dependencies.py
git commit -m "feat: add smtp_sender_name, settings_encryption_key, cron config fields, get_settings_service dep"
```

---

## Task 6: Admin settings schemas + GET/PUT router

**Files:**
- Create: `backend/src/api/v1/schemas/admin_settings.py`
- Create: `backend/src/api/v1/routers/admin_settings.py`

- [ ] **Step 1: Create schemas**

Create `backend/src/api/v1/schemas/admin_settings.py`:
```python
from pydantic import BaseModel


class SettingsResponse(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password_set: bool
    smtp_from: str
    smtp_sender_name: str
    app_url: str
    notification_cron_hour: int
    notification_cron_minute: int
    encryption_key_configured: bool


class SettingsUpdateRequest(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_sender_name: str | None = None
    app_url: str | None = None
    notification_cron_hour: int | None = None
    notification_cron_minute: int | None = None


class TestEmailRequest(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str | None = None
    smtp_from: str
    smtp_sender_name: str = "SubTrack"
```

- [ ] **Step 2: Create the router with GET and PUT**

Create `backend/src/api/v1/routers/admin_settings.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_settings_service, require_admin
from api.v1.schemas.admin_settings import SettingsResponse, SettingsUpdateRequest, TestEmailRequest
from api.v1.schemas.base import ApiResponse
from application.services.settings_service import SettingsService
from domain.entities.user import User
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender

router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin-settings"])

_NON_PASSWORD_KEYS = [
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_from",
    "smtp_sender_name",
    "app_url",
    "notification_cron_hour",
    "notification_cron_minute",
]


@router.get("", response_model=ApiResponse[SettingsResponse])
async def get_settings(
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(get_settings_service),
) -> ApiResponse[SettingsResponse]:
    password = await svc.get("smtp_password")
    return ApiResponse.ok(
        data=SettingsResponse(
            smtp_host=await svc.get("smtp_host") or "",
            smtp_port=int(await svc.get("smtp_port") or "587"),
            smtp_user=await svc.get("smtp_user") or "",
            smtp_password_set=bool(password),
            smtp_from=await svc.get("smtp_from") or "",
            smtp_sender_name=await svc.get("smtp_sender_name") or "SubTrack",
            app_url=await svc.get("app_url") or "",
            notification_cron_hour=int(await svc.get("notification_cron_hour") or "8"),
            notification_cron_minute=int(await svc.get("notification_cron_minute") or "0"),
            encryption_key_configured=svc.encryption_key_configured,
        )
    )


@router.put("", response_model=ApiResponse[None])
async def update_settings(
    body: SettingsUpdateRequest,
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(get_settings_service),
) -> ApiResponse[None]:
    if body.smtp_password:
        if not svc.encryption_key_configured:
            raise HTTPException(status_code=400, detail="加密金鑰未設定（SETTINGS_ENCRYPTION_KEY），無法儲存密碼")
        await svc.set("smtp_password", body.smtp_password)

    field_map: dict[str, str | None] = {
        "smtp_host": body.smtp_host,
        "smtp_port": str(body.smtp_port) if body.smtp_port is not None else None,
        "smtp_user": body.smtp_user,
        "smtp_from": body.smtp_from,
        "smtp_sender_name": body.smtp_sender_name,
        "app_url": body.app_url,
        "notification_cron_hour": str(body.notification_cron_hour) if body.notification_cron_hour is not None else None,
        "notification_cron_minute": str(body.notification_cron_minute) if body.notification_cron_minute is not None else None,
    }
    for key, value in field_map.items():
        if value is not None:
            await svc.set(key, value)

    return ApiResponse.ok(message="設定已儲存")
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/api/v1/schemas/admin_settings.py backend/src/api/v1/routers/admin_settings.py
git commit -m "feat: admin settings schemas and GET/PUT endpoints"
```

---

## Task 7: Test-email endpoint

**Files:**
- Modify: `backend/src/api/v1/routers/admin_settings.py`

- [ ] **Step 1: Add POST /test-email to the router**

In `backend/src/api/v1/routers/admin_settings.py`, add this endpoint after the PUT endpoint:
```python
@router.post("/test-email", response_model=ApiResponse[None])
async def test_email(
    body: TestEmailRequest,
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(get_settings_service),
) -> ApiResponse[None]:
    password = body.smtp_password
    if not password:
        password = await svc.get("smtp_password") or ""

    sender = SmtpEmailSender(
        host=body.smtp_host,
        port=body.smtp_port,
        username=body.smtp_user,
        password=password,
        from_addr=body.smtp_from,
        sender_name=body.smtp_sender_name,
    )
    try:
        await sender.send(
            to=[current_user.email],
            subject="SubTrack 郵件設定測試",
            body="這是一封測試信，確認您的 SMTP 設定正確。\n\n如果您收到這封信，表示 SMTP 設定無誤。",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"寄信失敗：{e}")

    return ApiResponse.ok(message=f"測試信已寄至 {current_user.email}")
```

- [ ] **Step 2: Run all tests**

```bash
pytest -v
```
Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/src/api/v1/routers/admin_settings.py
git commit -m "feat: test-email endpoint"
```

---

## Task 8: Wire backend — register router + update auth.py + scheduler

**Files:**
- Modify: `backend/src/api/main.py`
- Modify: `backend/src/api/v1/routers/auth.py`
- Modify: `backend/src/infrastructure/scheduler/main.py`

- [ ] **Step 1: Register the router in main.py**

In `backend/src/api/main.py`, add import:
```python
from api.v1.routers.admin_settings import router as admin_settings_router
```

Then in `create_app()`, after `app.include_router(payments_router)`, add:
```python
    app.include_router(admin_settings_router)
```

- [ ] **Step 2: Update `forgot_password` in auth.py to use SettingsService**

In `backend/src/api/v1/routers/auth.py`, add these imports at the top (with existing imports):
```python
from api.dependencies import get_settings_service
from application.services.settings_service import SettingsService
```

Replace the `forgot_password` endpoint (currently lines 172–187) with:
```python
@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    svc: SettingsService = Depends(get_settings_service),
) -> ApiResponse[None]:
    repo = SqlUserRepository(db)
    smtp_config = await svc.get_smtp_config()
    email_sender = SmtpEmailSender(
        host=smtp_config.host,
        port=smtp_config.port,
        username=smtp_config.user,
        password=smtp_config.password,
        from_addr=smtp_config.from_addr,
        sender_name=smtp_config.sender_name,
    )
    app_url = await svc.get("app_url") or settings.app_url
    use_case = RequestPasswordResetUseCase(repo, email_sender, app_url)
    await use_case.execute(email=str(body.email))
    return ApiResponse.ok(message="若此 Email 已註冊，重設連結已寄出，請查收信箱")
```

- [ ] **Step 3: Update scheduler to use SettingsService**

Replace the entire content of `backend/src/infrastructure/scheduler/main.py` with:
```python
"""Long-running scheduler container: fires CheckAndNotifyUseCase once per day."""

import asyncio
import logging
import signal
from datetime import date, datetime

from api.config import get_settings
from application.services.settings_service import SettingsService
from application.use_cases.check_and_notify import CheckAndNotifyUseCase
from infrastructure.database.repositories.subscription_repository import SqlSubscriptionRepository
from infrastructure.database.repositories.system_setting_repository import SqlSystemSettingRepository
from infrastructure.database.session import AsyncSessionFactory
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

POLL_INTERVAL = 30

_shutdown = asyncio.Event()


def _handle_signal(sig: int, _frame: object) -> None:
    log.info("Received signal %s, shutting down…", signal.Signals(sig).name)
    _shutdown.set()


async def _read_schedule() -> tuple[int, int]:
    env = get_settings()
    async with AsyncSessionFactory() as session:
        svc = SettingsService(SqlSystemSettingRepository(session), env)
        hour = int(await svc.get("notification_cron_hour") or str(env.notification_cron_hour))
        minute = int(await svc.get("notification_cron_minute") or str(env.notification_cron_minute))
    return hour, minute


async def run_notifications() -> None:
    env = get_settings()
    async with AsyncSessionFactory() as session:
        svc = SettingsService(SqlSystemSettingRepository(session), env)
        smtp_config = await svc.get_smtp_config()
        sender = SmtpEmailSender(
            host=smtp_config.host,
            port=smtp_config.port,
            username=smtp_config.user,
            password=smtp_config.password,
            from_addr=smtp_config.from_addr,
            sender_name=smtp_config.sender_name,
        )
        repo = SqlSubscriptionRepository(session)
        use_case = CheckAndNotifyUseCase(repo, sender)
        sent = await use_case.execute()
    log.info("Notifications sent: %d", sent)


async def scheduler_loop(target_hour: int, target_minute: int) -> None:
    last_run_date: date | None = None
    log.info("Scheduler started — will run daily at %02d:%02d", target_hour, target_minute)

    while not _shutdown.is_set():
        now = datetime.now()
        today = now.date()

        if now.hour == target_hour and now.minute == target_minute and last_run_date != today:
            log.info("Triggering daily notification job")
            try:
                await run_notifications()
                last_run_date = today
            except Exception:
                log.exception("Notification job failed")

        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=POLL_INTERVAL)
        except TimeoutError:
            pass


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    env = get_settings()
    try:
        target_hour, target_minute = asyncio.run(_read_schedule())
    except Exception:
        log.exception("Failed to read schedule from DB, using env defaults")
        target_hour = env.notification_cron_hour
        target_minute = env.notification_cron_minute

    asyncio.run(scheduler_loop(target_hour, target_minute))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests**

```bash
pytest -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/main.py backend/src/api/v1/routers/auth.py backend/src/infrastructure/scheduler/main.py
git commit -m "feat: wire SettingsService into router, auth, and scheduler"
```

---

## Task 9: Frontend API client

**Files:**
- Create: `frontend/src/api/admin_settings.ts`

- [ ] **Step 1: Implement the API client**

Create `frontend/src/api/admin_settings.ts`:
```typescript
import type { AxiosError } from 'axios'
import { api } from './client'
import type { ApiResponse } from '@/types/api'

export interface SystemSettings {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password_set: boolean
  smtp_from: string
  smtp_sender_name: string
  app_url: string
  notification_cron_hour: number
  notification_cron_minute: number
  encryption_key_configured: boolean
}

export interface SettingsUpdatePayload {
  smtp_host?: string
  smtp_port?: number
  smtp_user?: string
  smtp_password?: string
  smtp_from?: string
  smtp_sender_name?: string
  app_url?: string
  notification_cron_hour?: number
  notification_cron_minute?: number
}

export interface TestEmailPayload {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password?: string
  smtp_from: string
  smtp_sender_name: string
}

function extractMessage(err: unknown, fallback: string): never {
  const detail = (err as AxiosError<{ detail?: string }>)?.response?.data?.detail
  const message = detail ?? (err as AxiosError<ApiResponse<null>>)?.response?.data?.message ?? fallback
  throw new Error(message)
}

export async function getSystemSettings(): Promise<SystemSettings> {
  const { data } = await api.get<ApiResponse<SystemSettings>>('/api/v1/admin/settings')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function updateSystemSettings(payload: SettingsUpdatePayload): Promise<void> {
  try {
    const { data } = await api.put<ApiResponse<null>>('/api/v1/admin/settings', payload)
    if (!data.success) throw new Error(data.message)
  } catch (err) {
    return extractMessage(err, '儲存設定失敗')
  }
}

export async function testSmtpEmail(payload: TestEmailPayload): Promise<string> {
  try {
    const { data } = await api.post<ApiResponse<null>>('/api/v1/admin/settings/test-email', payload)
    if (!data.success) throw new Error(data.message)
    return data.message
  } catch (err) {
    return extractMessage(err, '測試寄信失敗')
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles cleanly**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/admin_settings.ts
git commit -m "feat: admin settings API client"
```

---

## Task 10: SystemSettingsPage

**Files:**
- Create: `frontend/src/pages/SystemSettingsPage.tsx`

- [ ] **Step 1: Implement the page**

Create `frontend/src/pages/SystemSettingsPage.tsx`:
```tsx
import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuthStore } from '@/stores/authStore'
import { getSystemSettings, updateSystemSettings, testSmtpEmail } from '@/api/admin_settings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useToast } from '@/hooks/use-toast'

const schema = z.object({
  smtp_host: z.string(),
  smtp_port: z.coerce.number().int().min(1).max(65535),
  smtp_user: z.string(),
  smtp_password: z.string(),
  smtp_from: z.string(),
  smtp_sender_name: z.string(),
  app_url: z.string(),
  notification_cron_hour: z.coerce.number().int().min(0).max(23),
  notification_cron_minute: z.coerce.number().int().min(0).max(59),
})

type FormValues = z.infer<typeof schema>

function FormField({
  label,
  error,
  children,
  hint,
}: {
  label: string
  error?: string
  children: React.ReactNode
  hint?: string
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

export default function SystemSettingsPage() {
  const currentUser = useAuthStore((s) => s.currentUser)
  const { toast } = useToast()

  const { data: settings, isLoading } = useQuery({
    queryKey: ['system-settings'],
    queryFn: getSystemSettings,
  })

  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      smtp_host: '',
      smtp_port: 587,
      smtp_user: '',
      smtp_password: '',
      smtp_from: '',
      smtp_sender_name: 'SubTrack',
      app_url: '',
      notification_cron_hour: 8,
      notification_cron_minute: 0,
    },
  })

  useEffect(() => {
    if (settings) {
      reset({
        smtp_host: settings.smtp_host,
        smtp_port: settings.smtp_port,
        smtp_user: settings.smtp_user,
        smtp_password: '',
        smtp_from: settings.smtp_from,
        smtp_sender_name: settings.smtp_sender_name,
        app_url: settings.app_url,
        notification_cron_hour: settings.notification_cron_hour,
        notification_cron_minute: settings.notification_cron_minute,
      })
    }
  }, [settings, reset])

  const { mutate: doSave, isPending: isSaving } = useMutation({
    mutationFn: (values: FormValues) =>
      updateSystemSettings({
        smtp_host: values.smtp_host || undefined,
        smtp_port: values.smtp_port || undefined,
        smtp_user: values.smtp_user || undefined,
        smtp_password: values.smtp_password || undefined,
        smtp_from: values.smtp_from || undefined,
        smtp_sender_name: values.smtp_sender_name || undefined,
        app_url: values.app_url || undefined,
        notification_cron_hour: values.notification_cron_hour,
        notification_cron_minute: values.notification_cron_minute,
      }),
    onSuccess: () => toast({ title: '設定已儲存' }),
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  const { mutate: doTestEmail, isPending: isTesting } = useMutation({
    mutationFn: () => {
      const v = getValues()
      return testSmtpEmail({
        smtp_host: v.smtp_host,
        smtp_port: v.smtp_port,
        smtp_user: v.smtp_user,
        smtp_password: v.smtp_password || undefined,
        smtp_from: v.smtp_from,
        smtp_sender_name: v.smtp_sender_name,
      })
    },
    onSuccess: (msg) => toast({ title: msg }),
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  if (currentUser?.role !== 'admin') return <Navigate to="/dashboard" replace />
  if (isLoading) return <div className="text-muted-foreground">載入中...</div>

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-xl font-semibold">系統設定</h1>

      <form onSubmit={handleSubmit((v) => doSave(v))} className="space-y-8">

        {/* 郵件伺服器 */}
        <section className="space-y-4">
          <h3 className="text-base font-semibold">郵件伺服器（SMTP）</h3>

          {settings && !settings.encryption_key_configured && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              尚未設定加密金鑰（<code>SETTINGS_ENCRYPTION_KEY</code>），密碼無法儲存至資料庫，目前使用 .env 設定。
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="SMTP Host" error={errors.smtp_host?.message}>
              <Input {...register('smtp_host')} placeholder="smtp.gmail.com" />
            </FormField>

            <FormField label="SMTP Port" error={errors.smtp_port?.message}>
              <Input type="number" {...register('smtp_port')} placeholder="587" />
            </FormField>

            <FormField label="帳號" error={errors.smtp_user?.message}>
              <Input {...register('smtp_user')} placeholder="noreply@corp.com" />
            </FormField>

            <FormField
              label="密碼"
              error={errors.smtp_password?.message}
              hint={settings?.smtp_password_set ? '留空則不變' : '尚未設定'}
            >
              <Input
                type="password"
                autoComplete="new-password"
                {...register('smtp_password')}
                placeholder={settings?.smtp_password_set ? '留空則不變' : '請輸入密碼'}
              />
            </FormField>

            <FormField label="寄件人 Email" error={errors.smtp_from?.message}>
              <Input {...register('smtp_from')} placeholder="noreply@corp.com" />
            </FormField>

            <FormField
              label="寄件人顯示名稱"
              error={errors.smtp_sender_name?.message}
              hint='顯示在收件人信箱，例如「SubTrack」'
            >
              <Input {...register('smtp_sender_name')} placeholder="SubTrack" />
            </FormField>
          </div>

          <Button
            type="button"
            variant="outline"
            disabled={isTesting}
            onClick={() => doTestEmail()}
          >
            {isTesting ? '寄送中...' : '測試寄信'}
          </Button>
        </section>

        {/* 應用程式設定 */}
        <section className="space-y-4">
          <h3 className="text-base font-semibold">應用程式設定</h3>
          <FormField
            label="App URL"
            error={errors.app_url?.message}
            hint="用於產生邀請連結和重設密碼連結，例如 http://192.168.1.7"
          >
            <Input {...register('app_url')} placeholder="http://192.168.1.7" />
          </FormField>
        </section>

        {/* 通知排程 */}
        <section className="space-y-4">
          <h3 className="text-base font-semibold">通知排程</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="發送時間（小時，0–23）"
              error={errors.notification_cron_hour?.message}
            >
              <Input type="number" min={0} max={23} {...register('notification_cron_hour')} />
            </FormField>

            <FormField
              label="發送時間（分鐘，0–59）"
              error={errors.notification_cron_minute?.message}
            >
              <Input type="number" min={0} max={59} {...register('notification_cron_minute')} />
            </FormField>
          </div>
          <p className="text-xs text-muted-foreground">
            修改後需重新啟動 scheduler 服務才會生效（<code>docker compose restart scheduler</code>）
          </p>
        </section>

        <div className="border-t pt-6">
          <Button type="submit" disabled={isSaving}>
            {isSaving ? '儲存中...' : '儲存所有設定'}
          </Button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Check TypeScript**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SystemSettingsPage.tsx
git commit -m "feat: SystemSettingsPage with SMTP, app URL, and cron schedule sections"
```

---

## Task 11: Wire frontend — routes + nav links

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: Add route to App.tsx**

In `frontend/src/App.tsx`:

Add import at the top with the other page imports:
```tsx
import SystemSettingsPage from '@/pages/SystemSettingsPage'
```

Add route inside the `<Route element={<AppLayout />}>` block, after the `/payments` route:
```tsx
<Route path="/settings" element={<SystemSettingsPage />} />
```

- [ ] **Step 2: Add nav link to AppLayout.tsx**

In `frontend/src/layouts/AppLayout.tsx`, in both `desktopNavLinks` and `mobileNavLinks`, add `系統設定` inside the existing admin block.

`desktopNavLinks` — change from:
```tsx
  {currentUser?.role === 'admin' && (
    <>
      <NavLink to="/users" className={navLinkClass}>使用者管理</NavLink>
      <NavLink to="/audit-log" className={navLinkClass}>稽核日誌</NavLink>
    </>
  )}
```
to:
```tsx
  {currentUser?.role === 'admin' && (
    <>
      <NavLink to="/users" className={navLinkClass}>使用者管理</NavLink>
      <NavLink to="/audit-log" className={navLinkClass}>稽核日誌</NavLink>
      <NavLink to="/settings" className={navLinkClass}>系統設定</NavLink>
    </>
  )}
```

`mobileNavLinks` — same change (the mobile block at lines 104–110):
```tsx
  {currentUser?.role === 'admin' && (
    <>
      <NavLink to="/users" className={navLinkClass} onClick={() => setMobileOpen(false)}>使用者管理</NavLink>
      <NavLink to="/audit-log" className={navLinkClass} onClick={() => setMobileOpen(false)}>稽核日誌</NavLink>
      <NavLink to="/settings" className={navLinkClass} onClick={() => setMobileOpen(false)}>系統設定</NavLink>
    </>
  )}
```

- [ ] **Step 3: TypeScript check + lint**

```bash
cd frontend && npx tsc --noEmit && npm run lint
```
Expected: no errors.

- [ ] **Step 4: Start dev server and manually test**

```bash
npm run dev
```

Open `http://localhost:5173`, log in as admin. Verify:
1. "系統設定" link appears in nav (desktop and mobile)
2. Page loads with current SMTP values from `.env`
3. Changing SMTP host and saving shows "設定已儲存" toast
4. Reload page — changed value appears
5. "測試寄信" button sends to admin's email (check toast for success/error)
6. Password field shows placeholder "留空則不變" if a password is already set
7. Saving with empty password field does NOT clear the existing password
8. Non-admin user cannot access `/settings` (redirects to `/dashboard`)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/layouts/AppLayout.tsx
git commit -m "feat: add /settings route and nav link for admin"
```

- [ ] **Step 6: Push and deploy to VM**

```bash
git push
ssh root@192.168.1.7
cd /opt/subtrack
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

- [ ] **Step 7: Run migration on VM**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend alembic upgrade head
```
Expected: `Running upgrade 003 -> 004, add system_settings table`

- [ ] **Step 8: Add SETTINGS_ENCRYPTION_KEY to VM .env**

On VM, generate a key:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add the output to `backend/.env`:
```
SETTINGS_ENCRYPTION_KEY=<the generated key>
```

Restart backend:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart backend
```

- [ ] **Step 9: Verify on VM**

Open `http://192.168.1.7`, log in as admin, navigate to 系統設定. Verify settings load and save correctly.
