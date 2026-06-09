# Asset Types — 項目管理擴充 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 SubTrack 從純 SaaS 訂閱擴充為通用「項目管理」，支援 ERP、網域等任意企業資產類型，管理員可自訂類型，`login_account` 改為選填。

**Architecture:** 在現有 `saas_subscriptions` 資料表加 `asset_type_id` FK，新建 `asset_types` 表。Subscription 實體加 `asset_type_id`/`asset_type_name` 欄位，所有讀取訂閱的 query 改用 LEFT JOIN 帶出類型名稱。前端統一清單加類型欄位與篩選。

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic（後端）、React 19 + TanStack Query + react-hook-form + zod（前端）

---

## File Structure

**New files:**
- `backend/src/domain/entities/asset_type.py`
- `backend/src/domain/repositories/asset_type_repository.py`
- `backend/src/infrastructure/database/repositories/asset_type_repository.py`
- `backend/src/application/use_cases/list_asset_types.py`
- `backend/src/application/use_cases/create_asset_type.py`
- `backend/src/application/use_cases/update_asset_type.py`
- `backend/src/application/use_cases/delete_asset_type.py`
- `backend/src/api/v1/schemas/asset_type.py`
- `backend/src/api/v1/routers/asset_types.py`
- `backend/alembic/versions/005_add_asset_types.py`
- `backend/tests/unit/test_asset_type_use_cases.py`
- `frontend/src/api/asset_types.ts`

**Modified files:**
- `backend/src/domain/exceptions.py` — add `ConflictException`
- `backend/src/domain/entities/subscription.py` — add `asset_type_id`, `asset_type_name`; `login_account` → `str | None`
- `backend/src/infrastructure/database/models.py` — add `AssetTypeModel`, `SubscriptionModel.asset_type_id`
- `backend/src/infrastructure/database/repositories/subscription_repository.py` — join asset_types
- `backend/src/application/use_cases/create_subscription.py` — add `asset_type_id` param
- `backend/src/api/v1/schemas/subscription.py` — `asset_type_id`, `asset_type_name`; `login_account` → optional
- `backend/src/api/v1/routers/subscriptions.py` — pass `asset_type_id`
- `backend/src/api/exception_handlers.py` — add ConflictException handler
- `backend/src/api/main.py` — register asset_types router
- `frontend/src/types/api.ts` — add `AssetType`; update `Subscription` type
- `frontend/src/components/subscriptions/SubscriptionForm.tsx` — asset_type field, login_account optional
- `frontend/src/components/subscriptions/SubscriptionTable.tsx` — type column
- `frontend/src/pages/SubscriptionsPage.tsx` — type filter, label
- `frontend/src/pages/DashboardPage.tsx` — type badge in expiring table
- `frontend/src/pages/SystemSettingsPage.tsx` — asset types management section
- `frontend/src/layouts/AppLayout.tsx` — nav label change

---

### Task 1: ConflictException + AssetType domain

**Files:**
- Modify: `backend/src/domain/exceptions.py`
- Create: `backend/src/domain/entities/asset_type.py`
- Create: `backend/src/domain/repositories/asset_type_repository.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/unit/test_asset_type_entity.py`:

```python
from domain.entities.asset_type import AssetType


def test_asset_type_has_name():
    at = AssetType(name="SaaS")
    assert at.name == "SaaS"
    assert at.id is None


def test_asset_type_with_id():
    at = AssetType(name="ERP", id=1)
    assert at.id == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run from `backend/` (venv active):
```
pytest tests/unit/test_asset_type_entity.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'domain.entities.asset_type'`

- [ ] **Step 3: Add ConflictException to exceptions.py**

In `backend/src/domain/exceptions.py`, append:

```python
class ConflictException(DomainException):
    def __init__(self, message: str = "資源衝突") -> None:
        self.message = message
        super().__init__(message)
```

- [ ] **Step 4: Create AssetType entity**

Create `backend/src/domain/entities/asset_type.py`:

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AssetType:
    name: str
    created_by: int | None = None
    id: int | None = None
    created_at: datetime | None = None
```

- [ ] **Step 5: Create repository interface**

Create `backend/src/domain/repositories/asset_type_repository.py`:

```python
from abc import ABC, abstractmethod

from domain.entities.asset_type import AssetType


class AssetTypeRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[AssetType]: ...

    @abstractmethod
    async def get_by_id(self, asset_type_id: int) -> AssetType | None: ...

    @abstractmethod
    async def save(self, entity: AssetType) -> AssetType: ...

    @abstractmethod
    async def delete(self, asset_type_id: int) -> None: ...
```

- [ ] **Step 6: Run test to verify it passes**

```
pytest tests/unit/test_asset_type_entity.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/src/domain/exceptions.py backend/src/domain/entities/asset_type.py backend/src/domain/repositories/asset_type_repository.py backend/tests/unit/test_asset_type_entity.py
git commit -m "feat: add ConflictException, AssetType entity and repository interface"
```

---

### Task 2: AssetTypeModel + migration 005

**Files:**
- Modify: `backend/src/infrastructure/database/models.py`
- Create: `backend/alembic/versions/005_add_asset_types.py`

- [ ] **Step 1: Add AssetTypeModel and asset_type_id to SubscriptionModel in models.py**

At the top of `backend/src/infrastructure/database/models.py`, the imports are already there. Add `AssetTypeModel` before `SubscriptionModel`:

After `UserModel` class (around line 36), insert:

```python
class AssetTypeModel(Base):
    __tablename__ = "asset_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

Then add to `SubscriptionModel` (after the `status` column line, before `deleted_at`):

```python
asset_type_id = Column(Integer, ForeignKey("asset_types.id"), nullable=True)
```

- [ ] **Step 2: Create migration 005**

Create `backend/alembic/versions/005_add_asset_types.py`:

```python
"""add asset_types table and asset_type_id to subscriptions

Revision ID: 005
Revises: 004
Create Date: 2026-06-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "saas_subscriptions",
        sa.Column("asset_type_id", sa.Integer(), sa.ForeignKey("asset_types.id"), nullable=True),
    )
    op.execute("INSERT INTO asset_types (name) VALUES ('SaaS'), ('ERP'), ('網域')")


def downgrade() -> None:
    op.drop_column("saas_subscriptions", "asset_type_id")
    op.drop_table("asset_types")
```

- [ ] **Step 3: Verify migration runs (if local DB is available)**

If you have a local Postgres running with the `backend/.env`:
```
cd backend
alembic upgrade head
```
Expected: applies migration 005 without error.

If no local DB, skip — migration will run on deploy.

- [ ] **Step 4: Commit**

```bash
git add backend/src/infrastructure/database/models.py backend/alembic/versions/005_add_asset_types.py
git commit -m "feat: add AssetTypeModel and migration 005"
```

---

### Task 3: SqlAssetTypeRepository

**Files:**
- Create: `backend/src/infrastructure/database/repositories/asset_type_repository.py`
- Create: `backend/tests/unit/test_asset_type_repository_interface.py`

- [ ] **Step 1: Write failing test (interface contract)**

Create `backend/tests/unit/test_asset_type_repository_interface.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from domain.entities.asset_type import AssetType
from domain.repositories.asset_type_repository import AssetTypeRepository


@pytest.fixture
def repo():
    r = MagicMock(spec=AssetTypeRepository)
    r.list_all = AsyncMock(return_value=[AssetType(name="SaaS", id=1)])
    r.get_by_id = AsyncMock(return_value=AssetType(name="SaaS", id=1))
    r.save = AsyncMock(side_effect=lambda e: AssetType(name=e.name, id=1))
    r.delete = AsyncMock(return_value=None)
    return r


@pytest.mark.asyncio
async def test_list_all_returns_list(repo):
    result = await repo.list_all()
    assert isinstance(result, list)
    assert result[0].name == "SaaS"


@pytest.mark.asyncio
async def test_get_by_id_returns_entity(repo):
    result = await repo.get_by_id(1)
    assert result is not None
    assert result.id == 1


@pytest.mark.asyncio
async def test_save_returns_entity_with_id(repo):
    entity = AssetType(name="ERP")
    result = await repo.save(entity)
    assert result.id == 1


@pytest.mark.asyncio
async def test_delete_called(repo):
    await repo.delete(1)
    repo.delete.assert_called_once_with(1)
```

- [ ] **Step 2: Run test to verify it passes (uses mock)**

```
pytest tests/unit/test_asset_type_repository_interface.py -v
```
Expected: PASS (4 tests) — tests the interface via mock.

- [ ] **Step 3: Create SqlAssetTypeRepository**

Create `backend/src/infrastructure/database/repositories/asset_type_repository.py`:

```python
from domain.entities.asset_type import AssetType
from domain.exceptions import ConflictException, NotFoundException
from domain.repositories.asset_type_repository import AssetTypeRepository
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import AssetTypeModel, SubscriptionModel


def _to_entity(m: AssetTypeModel) -> AssetType:
    return AssetType(
        id=m.id,
        name=m.name,
        created_by=m.created_by,
        created_at=m.created_at,
    )


class SqlAssetTypeRepository(AssetTypeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[AssetType]:
        result = await self._session.execute(
            select(AssetTypeModel).order_by(AssetTypeModel.id)
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def get_by_id(self, asset_type_id: int) -> AssetType | None:
        result = await self._session.execute(
            select(AssetTypeModel).where(AssetTypeModel.id == asset_type_id)
        )
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def save(self, entity: AssetType) -> AssetType:
        if entity.id is not None:
            result = await self._session.execute(
                select(AssetTypeModel).where(AssetTypeModel.id == entity.id)
            )
            try:
                model = result.scalar_one()
            except NoResultFound:
                raise NotFoundException()
            model.name = entity.name
        else:
            model = AssetTypeModel(
                name=entity.name,
                created_by=entity.created_by,
            )
            self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise ConflictException("此名稱已存在")
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, asset_type_id: int) -> None:
        count_result = await self._session.execute(
            select(func.count())
            .select_from(SubscriptionModel)
            .where(
                SubscriptionModel.asset_type_id == asset_type_id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )
        if count_result.scalar_one() > 0:
            raise ConflictException("此類型尚有項目使用，無法刪除")
        result = await self._session.execute(
            select(AssetTypeModel).where(AssetTypeModel.id == asset_type_id)
        )
        try:
            model = result.scalar_one()
        except NoResultFound:
            raise NotFoundException()
        await self._session.delete(model)
        await self._session.commit()
```

- [ ] **Step 4: Run tests**

```
pytest tests/unit/test_asset_type_repository_interface.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/infrastructure/database/repositories/asset_type_repository.py backend/tests/unit/test_asset_type_repository_interface.py
git commit -m "feat: add SqlAssetTypeRepository"
```

---

### Task 4: AssetType use cases

**Files:**
- Create: `backend/src/application/use_cases/list_asset_types.py`
- Create: `backend/src/application/use_cases/create_asset_type.py`
- Create: `backend/src/application/use_cases/update_asset_type.py`
- Create: `backend/src/application/use_cases/delete_asset_type.py`
- Create: `backend/tests/unit/test_asset_type_use_cases.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_asset_type_use_cases.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.create_asset_type import CreateAssetTypeUseCase
from application.use_cases.delete_asset_type import DeleteAssetTypeUseCase
from application.use_cases.list_asset_types import ListAssetTypesUseCase
from application.use_cases.update_asset_type import UpdateAssetTypeUseCase
from domain.entities.asset_type import AssetType
from domain.exceptions import ConflictException, NotFoundException


@pytest.fixture
def repo():
    return MagicMock()


@pytest.mark.asyncio
async def test_list_returns_all(repo):
    repo.list_all = AsyncMock(return_value=[AssetType(name="SaaS", id=1)])
    result = await ListAssetTypesUseCase(repo).execute()
    assert len(result) == 1
    assert result[0].name == "SaaS"


@pytest.mark.asyncio
async def test_create_saves_entity(repo):
    repo.save = AsyncMock(return_value=AssetType(name="ERP", id=2))
    result = await CreateAssetTypeUseCase(repo).execute(name="ERP", created_by=1)
    assert result.id == 2
    repo.save.assert_called_once()
    entity = repo.save.call_args[0][0]
    assert entity.name == "ERP"
    assert entity.created_by == 1


@pytest.mark.asyncio
async def test_update_saves_new_name(repo):
    repo.get_by_id = AsyncMock(return_value=AssetType(name="SaaS", id=1))
    repo.save = AsyncMock(return_value=AssetType(name="Cloud SaaS", id=1))
    result = await UpdateAssetTypeUseCase(repo).execute(asset_type_id=1, name="Cloud SaaS")
    assert result.name == "Cloud SaaS"
    entity = repo.save.call_args[0][0]
    assert entity.name == "Cloud SaaS"


@pytest.mark.asyncio
async def test_update_raises_not_found_when_missing(repo):
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundException):
        await UpdateAssetTypeUseCase(repo).execute(asset_type_id=99, name="X")


@pytest.mark.asyncio
async def test_delete_delegates_to_repo(repo):
    repo.delete = AsyncMock(return_value=None)
    await DeleteAssetTypeUseCase(repo).execute(asset_type_id=1)
    repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_propagates_conflict(repo):
    repo.delete = AsyncMock(side_effect=ConflictException("此類型尚有項目使用，無法刪除"))
    with pytest.raises(ConflictException):
        await DeleteAssetTypeUseCase(repo).execute(asset_type_id=1)
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_asset_type_use_cases.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create list_asset_types.py**

Create `backend/src/application/use_cases/list_asset_types.py`:

```python
from domain.entities.asset_type import AssetType
from domain.repositories.asset_type_repository import AssetTypeRepository


class ListAssetTypesUseCase:
    def __init__(self, repo: AssetTypeRepository) -> None:
        self._repo = repo

    async def execute(self) -> list[AssetType]:
        return await self._repo.list_all()
```

- [ ] **Step 4: Create create_asset_type.py**

Create `backend/src/application/use_cases/create_asset_type.py`:

```python
from domain.entities.asset_type import AssetType
from domain.repositories.asset_type_repository import AssetTypeRepository


class CreateAssetTypeUseCase:
    def __init__(self, repo: AssetTypeRepository) -> None:
        self._repo = repo

    async def execute(self, name: str, created_by: int | None = None) -> AssetType:
        entity = AssetType(name=name, created_by=created_by)
        return await self._repo.save(entity)
```

- [ ] **Step 5: Create update_asset_type.py**

Create `backend/src/application/use_cases/update_asset_type.py`:

```python
from domain.entities.asset_type import AssetType
from domain.exceptions import NotFoundException
from domain.repositories.asset_type_repository import AssetTypeRepository


class UpdateAssetTypeUseCase:
    def __init__(self, repo: AssetTypeRepository) -> None:
        self._repo = repo

    async def execute(self, asset_type_id: int, name: str) -> AssetType:
        entity = await self._repo.get_by_id(asset_type_id)
        if entity is None:
            raise NotFoundException()
        entity.name = name
        return await self._repo.save(entity)
```

- [ ] **Step 6: Create delete_asset_type.py**

Create `backend/src/application/use_cases/delete_asset_type.py`:

```python
from domain.repositories.asset_type_repository import AssetTypeRepository


class DeleteAssetTypeUseCase:
    def __init__(self, repo: AssetTypeRepository) -> None:
        self._repo = repo

    async def execute(self, asset_type_id: int) -> None:
        await self._repo.delete(asset_type_id)
```

- [ ] **Step 7: Run tests to verify they pass**

```
pytest tests/unit/test_asset_type_use_cases.py -v
```
Expected: PASS (6 tests)

- [ ] **Step 8: Commit**

```bash
git add backend/src/application/use_cases/list_asset_types.py backend/src/application/use_cases/create_asset_type.py backend/src/application/use_cases/update_asset_type.py backend/src/application/use_cases/delete_asset_type.py backend/tests/unit/test_asset_type_use_cases.py
git commit -m "feat: add AssetType use cases"
```

---

### Task 5: API — schemas, router, exception handler, register

**Files:**
- Create: `backend/src/api/v1/schemas/asset_type.py`
- Create: `backend/src/api/v1/routers/asset_types.py`
- Modify: `backend/src/api/exception_handlers.py`
- Modify: `backend/src/api/main.py`

- [ ] **Step 1: Create schemas/asset_type.py**

Create `backend/src/api/v1/schemas/asset_type.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field


class AssetTypeResponse(BaseModel):
    id: int
    name: str
    created_at: datetime | None


class AssetTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class AssetTypeUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
```

- [ ] **Step 2: Create routers/asset_types.py**

Create `backend/src/api/v1/routers/asset_types.py`:

```python
from application.use_cases.create_asset_type import CreateAssetTypeUseCase
from application.use_cases.delete_asset_type import DeleteAssetTypeUseCase
from application.use_cases.list_asset_types import ListAssetTypesUseCase
from application.use_cases.update_asset_type import UpdateAssetTypeUseCase
from domain.entities.user import User
from fastapi import APIRouter, Depends
from infrastructure.database.repositories.asset_type_repository import SqlAssetTypeRepository
from infrastructure.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, require_admin
from api.v1.schemas.asset_type import AssetTypeCreate, AssetTypeResponse, AssetTypeUpdate
from api.v1.schemas.base import ApiResponse

router = APIRouter(prefix="/api/v1/asset-types", tags=["asset-types"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> SqlAssetTypeRepository:
    return SqlAssetTypeRepository(db)


@router.get("", response_model=ApiResponse[list[AssetTypeResponse]])
async def list_asset_types(
    _: User = Depends(get_current_user),
    repo: SqlAssetTypeRepository = Depends(_get_repo),
) -> ApiResponse[list[AssetTypeResponse]]:
    items = await ListAssetTypesUseCase(repo).execute()
    return ApiResponse.ok(data=[AssetTypeResponse(**vars(t)) for t in items])


@router.post("", response_model=ApiResponse[AssetTypeResponse], status_code=201)
async def create_asset_type(
    body: AssetTypeCreate,
    current_user: User = Depends(require_admin),
    repo: SqlAssetTypeRepository = Depends(_get_repo),
) -> ApiResponse[AssetTypeResponse]:
    result = await CreateAssetTypeUseCase(repo).execute(
        name=body.name, created_by=current_user.id
    )
    return ApiResponse.ok(data=AssetTypeResponse(**vars(result)))


@router.patch("/{asset_type_id}", response_model=ApiResponse[AssetTypeResponse])
async def update_asset_type(
    asset_type_id: int,
    body: AssetTypeUpdate,
    _: User = Depends(require_admin),
    repo: SqlAssetTypeRepository = Depends(_get_repo),
) -> ApiResponse[AssetTypeResponse]:
    result = await UpdateAssetTypeUseCase(repo).execute(
        asset_type_id=asset_type_id, name=body.name
    )
    return ApiResponse.ok(data=AssetTypeResponse(**vars(result)))


@router.delete("/{asset_type_id}", response_model=ApiResponse[None])
async def delete_asset_type(
    asset_type_id: int,
    _: User = Depends(require_admin),
    repo: SqlAssetTypeRepository = Depends(_get_repo),
) -> ApiResponse[None]:
    await DeleteAssetTypeUseCase(repo).execute(asset_type_id=asset_type_id)
    return ApiResponse.ok(message="已刪除")
```

- [ ] **Step 3: Add ConflictException handler to exception_handlers.py**

In `backend/src/api/exception_handlers.py`:

Add to imports:
```python
from domain.exceptions import (
    BadRequestException,
    ConflictException,
    DuplicateEmailException,
    ForbiddenException,
    LastAdminException,
    NotAuthenticatedException,
    NotFoundException,
)
```

Add handler inside `register_exception_handlers`, after the `last_admin_handler`:

```python
    @app.exception_handler(ConflictException)
    async def conflict_handler(request: Request, exc: ConflictException):
        return JSONResponse(
            status_code=409,
            content={"success": False, "data": None, "message": exc.message, "meta": None},
        )
```

- [ ] **Step 4: Register router in main.py**

In `backend/src/api/main.py`, add import:
```python
from api.v1.routers.asset_types import router as asset_types_router
```

And in `create_app()`, after `app.include_router(admin_settings_router)`:
```python
    app.include_router(asset_types_router)
```

- [ ] **Step 5: Run all tests**

```
pytest -v
```
Expected: all existing tests PASS + the new tests from Tasks 1–4.

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/v1/schemas/asset_type.py backend/src/api/v1/routers/asset_types.py backend/src/api/exception_handlers.py backend/src/api/main.py
git commit -m "feat: add asset-types API router and ConflictException handler"
```

---

### Task 6: Subscription entity + repository — add asset_type fields

**Files:**
- Modify: `backend/src/domain/entities/subscription.py`
- Modify: `backend/src/infrastructure/database/repositories/subscription_repository.py`

- [ ] **Step 1: Write failing test**

In `backend/tests/unit/test_subscription_entity.py`, add:

```python
def test_subscription_login_account_is_optional():
    from domain.entities.subscription import Subscription
    from datetime import date
    s = Subscription(
        service_name="Domain",
        login_account=None,
        expiry_date=date(2027, 1, 1),
        notification_emails=[],
        notification_days=30,
    )
    assert s.login_account is None


def test_subscription_has_asset_type_fields():
    from domain.entities.subscription import Subscription
    from datetime import date
    s = Subscription(
        service_name="ERP",
        login_account=None,
        expiry_date=date(2027, 1, 1),
        notification_emails=[],
        notification_days=30,
        asset_type_id=2,
        asset_type_name="ERP",
    )
    assert s.asset_type_id == 2
    assert s.asset_type_name == "ERP"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/unit/test_subscription_entity.py -v -k "asset_type or login_account_is_optional"
```
Expected: FAIL

- [ ] **Step 3: Update Subscription entity**

In `backend/src/domain/entities/subscription.py`, change:

```python
    login_account: str
```
to:
```python
    login_account: str | None = None
```

And add two fields after `status`:
```python
    asset_type_id: int | None = None
    asset_type_name: str | None = None
```

The full field list (showing only changed/added lines):
```python
@dataclass
class Subscription:
    service_name: str
    login_account: str | None  # changed from str
    expiry_date: date
    notification_emails: list[str]
    notification_days: int

    cost: Decimal | None = None
    currency: str = "TWD"
    exchange_rate: Decimal | None = None
    notes: str | None = None
    owner_name: str | None = None
    login_password: str | None = None
    department: str | None = None
    billing_cycle: str | None = None
    payment_account: str | None = None
    auto_renew: bool = False
    trial_end_date: date | None = None
    next_billing_date: date | None = None
    last_notified_date: date | None = None
    status: str = "active"
    asset_type_id: int | None = None      # new
    asset_type_name: str | None = None    # new

    id: int | None = None
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

Note: `login_account` must remain a positional-style field (no default), but since it now has `str | None` type, callers can pass `None`. Actually in Python dataclasses, fields without defaults must come before fields with defaults. Since `login_account` has no default value currently, we just change the type annotation — no default needed.

- [ ] **Step 4: Update subscription_repository.py**

Replace the entire file content of `backend/src/infrastructure/database/repositories/subscription_repository.py`:

```python
import json
from datetime import UTC, date, datetime

from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException
from domain.repositories.subscription_repository import SubscriptionRepository
from sqlalchemy import func, or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import AssetTypeModel, SubscriptionModel


def _to_entity(m: SubscriptionModel, asset_type_name: str | None = None) -> Subscription:
    return Subscription(
        id=m.id,
        service_name=m.service_name,
        login_account=m.login_account,
        expiry_date=m.expiry_date,
        notification_emails=json.loads(m.notification_emails) if m.notification_emails else [],
        notification_days=m.notification_days if m.notification_days is not None else 30,
        cost=m.cost,
        currency=m.currency or "TWD",
        exchange_rate=m.exchange_rate,
        notes=m.notes,
        owner_name=m.owner_name,
        login_password=m.login_password,
        department=m.department,
        billing_cycle=m.billing_cycle,
        payment_account=m.payment_account,
        auto_renew=m.auto_renew or False,
        trial_end_date=m.trial_end_date,
        next_billing_date=m.next_billing_date,
        last_notified_date=m.last_notified_date,
        status=m.status or "active",
        asset_type_id=m.asset_type_id,
        asset_type_name=asset_type_name,
        deleted_at=m.deleted_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _with_type_join(stmt):
    return stmt.outerjoin(
        AssetTypeModel, SubscriptionModel.asset_type_id == AssetTypeModel.id
    ).add_columns(AssetTypeModel.name.label("asset_type_name"))


class SqlSubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: int) -> Subscription | None:
        result = await self._session.execute(
            _with_type_join(
                select(SubscriptionModel).where(
                    SubscriptionModel.id == id,
                    SubscriptionModel.deleted_at.is_(None),
                )
            )
        )
        row = result.one_or_none()
        return _to_entity(row[0], row[1]) if row else None

    async def list_all(self) -> list[Subscription]:
        result = await self._session.execute(
            _with_type_join(
                select(SubscriptionModel)
                .where(SubscriptionModel.deleted_at.is_(None))
                .order_by(SubscriptionModel.expiry_date)
            )
        )
        return [_to_entity(row[0], row[1]) for row in result.all()]

    async def list_paginated(
        self,
        limit: int,
        offset: int,
        show_suspended: bool,
    ) -> tuple[list[Subscription], int]:
        base_filter = [SubscriptionModel.deleted_at.is_(None)]
        if not show_suspended:
            base_filter.append(SubscriptionModel.status != "suspended")

        count_result = await self._session.execute(
            select(func.count()).select_from(SubscriptionModel).where(*base_filter)
        )
        total = count_result.scalar_one()

        data_result = await self._session.execute(
            _with_type_join(
                select(SubscriptionModel)
                .where(*base_filter)
                .order_by(SubscriptionModel.expiry_date)
                .limit(limit)
                .offset(offset)
            )
        )
        items = [_to_entity(row[0], row[1]) for row in data_result.all()]
        return items, total

    async def save(self, entity: Subscription) -> Subscription:
        emails_json = json.dumps(entity.notification_emails)
        if entity.id is not None:
            result = await self._session.execute(
                select(SubscriptionModel).where(
                    SubscriptionModel.id == entity.id,
                    SubscriptionModel.deleted_at.is_(None),
                )
            )
            try:
                model = result.scalar_one()
            except NoResultFound:
                raise NotFoundException()
            model.service_name = entity.service_name
            model.login_account = entity.login_account
            model.expiry_date = entity.expiry_date
            model.notification_emails = emails_json
            model.notification_days = entity.notification_days
            model.cost = entity.cost
            model.currency = entity.currency
            model.exchange_rate = entity.exchange_rate
            model.notes = entity.notes
            model.owner_name = entity.owner_name
            model.login_password = entity.login_password
            model.department = entity.department
            model.billing_cycle = entity.billing_cycle
            model.payment_account = entity.payment_account
            model.auto_renew = entity.auto_renew
            model.trial_end_date = entity.trial_end_date
            model.next_billing_date = entity.next_billing_date
            model.last_notified_date = entity.last_notified_date
            model.status = entity.status
            model.asset_type_id = entity.asset_type_id
        else:
            model = SubscriptionModel(
                service_name=entity.service_name,
                login_account=entity.login_account,
                expiry_date=entity.expiry_date,
                notification_emails=emails_json,
                notification_days=entity.notification_days,
                cost=entity.cost,
                currency=entity.currency,
                exchange_rate=entity.exchange_rate,
                notes=entity.notes,
                owner_name=entity.owner_name,
                login_password=entity.login_password,
                department=entity.department,
                billing_cycle=entity.billing_cycle,
                payment_account=entity.payment_account,
                auto_renew=entity.auto_renew,
                trial_end_date=entity.trial_end_date,
                next_billing_date=entity.next_billing_date,
                last_notified_date=entity.last_notified_date,
                status=entity.status,
                asset_type_id=entity.asset_type_id,
            )
            self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return await self.get_by_id(model.id) or _to_entity(model)

    async def delete(self, id: int) -> None:
        result = await self._session.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.id == id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )
        try:
            model = result.scalar_one()
        except NoResultFound:
            raise NotFoundException()
        model.deleted_at = datetime.now(UTC)
        await self._session.commit()

    async def list_due_for_notification(self, today: date) -> list[Subscription]:
        result = await self._session.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.deleted_at.is_(None),
                SubscriptionModel.status == "active",
                SubscriptionModel.notification_emails.isnot(None),
                SubscriptionModel.notification_emails != "[]",
                SubscriptionModel.expiry_date >= today,
                or_(
                    SubscriptionModel.last_notified_date.is_(None),
                    SubscriptionModel.last_notified_date < today,
                ),
            )
        )
        candidates = [_to_entity(m) for m in result.scalars().all()]
        return [
            s
            for s in candidates
            if s.notification_days > 0
            and (s.expiry_date - today).days <= s.notification_days
            and s.notification_emails
        ]

    async def mark_notified(self, id: int, today: date) -> None:
        result = await self._session.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.id == id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model:
            model.last_notified_date = today
            await self._session.commit()
```

- [ ] **Step 5: Run all tests**

```
pytest -v
```
Expected: all tests PASS. Tests that previously used `login_account=""` still pass because `""` is a valid `str | None`.

- [ ] **Step 6: Commit**

```bash
git add backend/src/domain/entities/subscription.py backend/src/infrastructure/database/repositories/subscription_repository.py
git commit -m "feat: add asset_type fields to Subscription entity and repository joins"
```

---

### Task 7: Subscription API schema + use cases + router

**Files:**
- Modify: `backend/src/api/v1/schemas/subscription.py`
- Modify: `backend/src/application/use_cases/create_subscription.py`
- Modify: `backend/src/api/v1/routers/subscriptions.py`

- [ ] **Step 1: Update subscription.py schemas**

In `backend/src/api/v1/schemas/subscription.py`:

**`SubscriptionCreate`** — change `login_account: str = ""` to `login_account: str | None = None`, add `asset_type_id`:
```python
class SubscriptionCreate(BaseModel):
    service_name: str
    expiry_date: date
    login_account: str | None = None
    notification_emails: list[str] = []
    notification_days: int = 30
    cost: Decimal | None = None
    currency: CurrencyType = "TWD"
    exchange_rate: Decimal | None = None
    notes: str | None = None
    owner_name: str | None = None
    login_password: str | None = None
    department: str | None = None
    billing_cycle: str | None = None
    payment_account: str | None = None
    auto_renew: bool = False
    trial_end_date: date | None = None
    next_billing_date: date | None = None
    status: str = "active"
    asset_type_id: int | None = None
```

**`SubscriptionUpdate`** — add `asset_type_id`:
```python
class SubscriptionUpdate(BaseModel):
    service_name: str | None = None
    expiry_date: date | None = None
    login_account: str | None = None
    notification_emails: list[str] | None = None
    notification_days: int | None = None
    cost: Decimal | None = None
    currency: CurrencyType | None = None
    exchange_rate: Decimal | None = None
    notes: str | None = None
    owner_name: str | None = None
    login_password: str | None = None
    department: str | None = None
    billing_cycle: str | None = None
    payment_account: str | None = None
    auto_renew: bool | None = None
    trial_end_date: date | None = None
    next_billing_date: date | None = None
    status: str | None = None
    asset_type_id: int | None = None
```

**`SubscriptionResponse`** — change `login_account: str` to `login_account: str | None`, add `asset_type_id` and `asset_type_name`:
```python
class SubscriptionResponse(BaseModel):
    id: int
    service_name: str
    login_account: str | None
    expiry_date: date
    notification_emails: list[str]
    notification_days: int
    cost: Decimal | None
    currency: str
    exchange_rate: Decimal | None
    notes: str | None
    owner_name: str | None
    login_password: str | None
    department: str | None
    billing_cycle: str | None
    payment_account: str | None
    auto_renew: bool
    trial_end_date: date | None
    next_billing_date: date | None
    status: str
    asset_type_id: int | None
    asset_type_name: str | None
    created_at: datetime | None
    updated_at: datetime | None
```

- [ ] **Step 2: Update create_subscription.py use case**

In `backend/src/application/use_cases/create_subscription.py`:

Change `login_account: str` parameter to `login_account: str | None = None` and add `asset_type_id: int | None = None`:

```python
    async def execute(
        self,
        service_name: str,
        login_account: str | None = None,
        expiry_date: date = ...,  # still required, just showing changed params
        ...
        asset_type_id: int | None = None,
    ) -> Subscription:
```

The full updated signature:
```python
    async def execute(
        self,
        service_name: str,
        expiry_date: date,
        login_account: str | None = None,
        notification_emails: list[str] | None = None,
        notification_days: int = 30,
        cost: Decimal | None = None,
        currency: str = "TWD",
        exchange_rate: Decimal | None = None,
        notes: str | None = None,
        owner_name: str | None = None,
        login_password: str | None = None,
        department: str | None = None,
        billing_cycle: str | None = None,
        payment_account: str | None = None,
        auto_renew: bool = False,
        trial_end_date: date | None = None,
        next_billing_date: date | None = None,
        status: str = "active",
        asset_type_id: int | None = None,
    ) -> Subscription:
        entity = Subscription(
            service_name=service_name,
            login_account=login_account,
            expiry_date=expiry_date,
            notification_emails=notification_emails or [],
            notification_days=notification_days,
            cost=cost,
            currency=currency,
            exchange_rate=exchange_rate,
            notes=notes,
            owner_name=owner_name,
            login_password=login_password,
            department=department,
            billing_cycle=billing_cycle,
            payment_account=payment_account,
            auto_renew=auto_renew,
            trial_end_date=trial_end_date,
            next_billing_date=next_billing_date,
            status=status,
            asset_type_id=asset_type_id,
        )
        result = await self._repo.save(entity)
        if self._audit_repo is not None:
            await self._audit_repo.save(
                AuditEntry(
                    user_id=self._actor_user_id,
                    action="create",
                    resource_type="subscription",
                    resource_id=result.id,
                    details={
                        "user_email": self._actor_email,
                        "service_name": result.service_name,
                    },
                )
            )
        return result
```

- [ ] **Step 3: No router changes needed**

Both endpoints use `**body.model_dump()` / `**body.model_dump(exclude_unset=True)`, so adding `asset_type_id` to the Pydantic schemas in Step 1 is all that's needed — the router automatically passes the new field to the use case. No changes to `subscriptions.py` router required.

- [ ] **Step 4: Run all tests**

```
pytest -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/v1/schemas/subscription.py backend/src/application/use_cases/create_subscription.py backend/src/api/v1/routers/subscriptions.py
git commit -m "feat: add asset_type_id to subscription schema and use cases"
```

---

### Task 8: Frontend — types + API layer

**Files:**
- Modify: `frontend/src/types/api.ts`
- Create: `frontend/src/api/asset_types.ts`

- [ ] **Step 1: Update types/api.ts**

Add `AssetType` interface and update `Subscription`:

After the existing imports/types, add:
```typescript
export interface AssetType {
  id: number
  name: string
  created_at: string | null
}
```

In the `Subscription` interface, change:
```typescript
  login_account: string
```
to:
```typescript
  login_account: string | null
```

And add after `status`:
```typescript
  asset_type_id: number | null
  asset_type_name: string | null
```

- [ ] **Step 2: Create api/asset_types.ts**

Create `frontend/src/api/asset_types.ts`:

```typescript
import { api } from './client'
import type { ApiResponse, AssetType } from '@/types/api'

export async function listAssetTypes(): Promise<AssetType[]> {
  const { data } = await api.get<ApiResponse<AssetType[]>>('/api/v1/asset-types')
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function createAssetType(name: string): Promise<AssetType> {
  const { data } = await api.post<ApiResponse<AssetType>>('/api/v1/asset-types', { name })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function updateAssetType(id: number, name: string): Promise<AssetType> {
  const { data } = await api.patch<ApiResponse<AssetType>>(`/api/v1/asset-types/${id}`, { name })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function deleteAssetType(id: number): Promise<void> {
  await api.delete(`/api/v1/asset-types/${id}`)
}
```

- [ ] **Step 3: TypeScript check**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors (or only pre-existing errors from login_account usages not yet fixed).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/api/asset_types.ts
git commit -m "feat: add AssetType types and API client"
```

---

### Task 9: SubscriptionForm — asset_type field + login_account optional

**Files:**
- Modify: `frontend/src/components/subscriptions/SubscriptionForm.tsx`

The form currently has `login_account: z.string().min(1, '帳號為必填')`. Change to optional and add `asset_type_id`.

- [ ] **Step 1: Update SubscriptionForm.tsx**

**a) Add import at top:**
```typescript
import { useQuery } from '@tanstack/react-query'
import { listAssetTypes } from '@/api/asset_types'
```

**b) Update zod schema** — change `login_account` validation and add `asset_type_id`:
```typescript
const schema = z.object({
  service_name: z.string().min(1, '服務名稱為必填'),
  expiry_date: z.string().min(1, '到期日為必填'),
  login_account: z.string().optional(),   // was .min(1, '帳號為必填')
  login_password: z.string().optional(),
  owner_name: z.string().min(1, '負責人為必填'),
  department: z.string().min(1, '部門為必填'),
  billing_cycle: z.enum(BILLING_CYCLES, { error: '請選擇計費週期' }),
  cost: z.string().optional(),
  currency: z.enum(CURRENCIES),
  exchange_rate: z.string().optional(),
  payment_account: z.string().optional(),
  auto_renew: z.boolean(),
  trial_end_date: z.string().optional(),
  next_billing_date: z.string().optional(),
  notification_emails: z.string().optional(),
  notification_days: z.string().refine((v) => parseInt(v) > 0, '必須大於 0 天'),
  status: z.enum(STATUSES),
  notes: z.string().optional(),
  asset_type_id: z.string().optional(),   // stored as string from Select, converted in buildPayload
})
```

**c) Update `buildPayload`** — add `asset_type_id`:
```typescript
function buildPayload(values: FormValues): Record<string, unknown> {
  return {
    service_name: values.service_name,
    login_account: values.login_account || null,
    login_password: values.login_password || undefined,
    expiry_date: values.expiry_date,
    owner_name: values.owner_name,
    department: values.department,
    billing_cycle: values.billing_cycle,
    cost: values.cost || undefined,
    currency: values.currency,
    exchange_rate: values.currency !== 'TWD' && values.exchange_rate ? values.exchange_rate : undefined,
    // ... keep existing fields unchanged ...
    asset_type_id: values.asset_type_id ? parseInt(values.asset_type_id) : null,
  }
}
```

**d) Add query for asset types inside the component function** (after existing hooks):
```typescript
  const { data: assetTypes = [] } = useQuery({
    queryKey: ['asset-types'],
    queryFn: listAssetTypes,
  })
```

**e) Add asset_type_id default in `useForm` defaultValues** (or in initialValues when editing):
When the form is used for editing, it receives an existing subscription. Add default for `asset_type_id`:
```typescript
asset_type_id: initialValues?.asset_type_id ? String(initialValues.asset_type_id) : '',
```

**f) Add the asset type `<Select>` field to the form JSX**, near the top of the form (after service_name, before login_account):

```tsx
{/* 類型 */}
<div className="space-y-1">
  <label className="text-sm font-medium">類型（選填）</label>
  <Select
    value={watch('asset_type_id') ?? ''}
    onValueChange={(v) => setValue('asset_type_id', v, { shouldValidate: true })}
  >
    <SelectTrigger>
      <SelectValue placeholder="選擇類型" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="">未分類</SelectItem>
      {assetTypes.map((t) => (
        <SelectItem key={t.id} value={String(t.id)}>
          {t.name}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>
```

**g) Update login_account field label** to「登入帳號（選填）」and remove any required indicator.

To do this, find the login_account field JSX in the form and change the label text:
```tsx
<label className="text-sm font-medium">登入帳號（選填）</label>
```

- [ ] **Step 2: TypeScript check**

```
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/subscriptions/SubscriptionForm.tsx
git commit -m "feat: add asset_type field and make login_account optional in SubscriptionForm"
```

---

### Task 10: SubscriptionsPage — type column + filter

**Files:**
- Modify: `frontend/src/pages/SubscriptionsPage.tsx`
- Modify: `frontend/src/components/subscriptions/SubscriptionTable.tsx`

- [ ] **Step 1: Add type filter to SubscriptionsPage.tsx**

**a) Add imports:**
```typescript
import { useQuery } from '@tanstack/react-query'
import { listAssetTypes } from '@/api/asset_types'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
```

**b) Add state:**
```typescript
const [assetTypeFilter, setAssetTypeFilter] = useState<string>('')
```

**c) Add asset types query:**
```typescript
const { data: assetTypes = [] } = useQuery({
  queryKey: ['asset-types'],
  queryFn: listAssetTypes,
})
```

**d) Add type filter to the filtered logic:**
```typescript
const filtered = subscriptions
  .filter((s) =>
    s.service_name.toLowerCase().includes(q) ||
    (s.login_account ?? '').toLowerCase().includes(q) ||
    (s.department ?? '').toLowerCase().includes(q) ||
    (s.owner_name ?? '').toLowerCase().includes(q),
  )
  .filter((s) =>
    assetTypeFilter === '' || String(s.asset_type_id ?? '') === assetTypeFilter
  )
```

**e) Add `<Select>` filter control in the filter row** (after the search input):
```tsx
<Select value={assetTypeFilter} onValueChange={setAssetTypeFilter}>
  <SelectTrigger className="w-36">
    <SelectValue placeholder="全部類型" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="">全部類型</SelectItem>
    {assetTypes.map((t) => (
      <SelectItem key={t.id} value={String(t.id)}>
        {t.name}
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

**f) Update CSV download headers** — add `類型` to headers and rows:
```typescript
const headers = ['類型', '服務名稱', '登入帳號', '部門', ...]
const rows = items.map((s) => [
  s.asset_type_name ?? '',
  s.service_name,
  s.login_account ?? '',
  ...
])
```

**g) Change page title** from `訂閱管理` to `項目管理`:
```tsx
<h2 className="text-2xl font-bold">項目管理</h2>
```

**h) Change "新增訂閱" button text** to `新增項目`:
```tsx
<Button onClick={() => navigate('/subscriptions/new')}>
  <Plus className="size-4" />
  新增項目
</Button>
```

- [ ] **Step 2: Add type column to SubscriptionTable.tsx**

**a) Add `TypeBadge` component** after `StatusBadge`:
```tsx
function TypeBadge({ name }: { name: string | null | undefined }) {
  if (!name) return <span className="text-slate-400">—</span>
  return (
    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
      {name}
    </span>
  )
}
```

**b) Add `'asset_type_name'` to `SortKey` type:**
```typescript
type SortKey = 'service_name' | 'login_account' | 'department' | 'owner_name' | 'cost' | 'billing_cycle' | 'expiry_date' | 'status' | 'asset_type_name'
```

**c) Add `<TableHead>` for 類型** in the header row, before 服務名稱 or after — choose after 服務名稱 for visibility.

**d) Add `<TableCell>` in body rows:**
```tsx
<TableCell><TypeBadge name={s.asset_type_name} /></TableCell>
```

**e) Handle `login_account` nullable** — wherever `s.login_account` is rendered directly, add `?? '—'`:
In SubscriptionTable, find `{s.login_account}` and change to `{s.login_account ?? '—'}`.

- [ ] **Step 3: TypeScript check**

```
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SubscriptionsPage.tsx frontend/src/components/subscriptions/SubscriptionTable.tsx
git commit -m "feat: add type column and filter to subscription list page"
```

---

### Task 11: DashboardPage — type badge + login_account null safety

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Update DashboardPage.tsx**

**a) Add imports for asset types query and Select:**
```typescript
import { useQuery } from '@tanstack/react-query'
import { listAssetTypes } from '@/api/asset_types'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
```

**b) Add state and query inside the component function** (after the existing queries for subscriptions/payments):
```typescript
  const [typeFilter, setTypeFilter] = useState<string>('')
  const { data: assetTypes = [] } = useQuery({
    queryKey: ['asset-types'],
    queryFn: listAssetTypes,
  })
```

**c) Filter `expiringSubscriptions`** — `computeStats` returns `DashboardStats` which has `expiringSubscriptions`. After calling `computeStats(subscriptions)`, filter the expiring list:
```typescript
  const stats = useMemo(() => computeStats(subs), [subs])
  const filteredExpiring = useMemo(
    () => typeFilter
      ? stats.expiringSubscriptions.filter((s) => String(s.asset_type_id ?? '') === typeFilter)
      : stats.expiringSubscriptions,
    [stats.expiringSubscriptions, typeFilter],
  )
```
Pass `filteredExpiring` to `<ExpiringTable items={filteredExpiring} ...>` instead of `stats.expiringSubscriptions`.

**d) Add type filter `<Select>` above the ExpiringTable**, inside the section that renders it:
```tsx
<div className="flex items-center gap-3 mb-3">
  <Select value={typeFilter} onValueChange={setTypeFilter}>
    <SelectTrigger className="w-36">
      <SelectValue placeholder="全部類型" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="">全部類型</SelectItem>
      {assetTypes.map((t) => (
        <SelectItem key={t.id} value={String(t.id)}>
          {t.name}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>
```

**e) Update `ExpiringTable` component** — add `asset_type_name` column header and cell:

In the `<thead>` row, add after the `服務名稱` header:
```tsx
<th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white">類型</th>
```

In the `<tbody>` row, add after the service_name cell:
```tsx
<td className="px-4 py-3">
  {item.asset_type_name ? (
    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
      {item.asset_type_name}
    </span>
  ) : (
    <span className="text-slate-400">—</span>
  )}
</td>
```

**f) Fix `login_account` null safety** in the expiring table row:
```tsx
<td className="px-4 py-3 text-slate-600">{item.login_account ?? '—'}</td>
```

**g) Check `dashboardStats.ts`** — if `expiringSubscriptions` items are typed as `Subscription`, the `asset_type_name` field is now available automatically. No change needed there unless the type was explicitly narrow.

- [ ] **Step 2: TypeScript check**

```
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: add type badge to dashboard expiring items"
```

---

### Task 12: SystemSettingsPage — asset types management section

**Files:**
- Modify: `frontend/src/pages/SystemSettingsPage.tsx`

This section is admin-only (page already guards `currentUser?.role !== 'admin'`).

- [ ] **Step 1: Update SystemSettingsPage.tsx**

**a) Add imports at top:**
```typescript
import { useState } from 'react'  // already imported via useEffect, check
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'  // already imported
import { listAssetTypes, createAssetType, updateAssetType, deleteAssetType } from '@/api/asset_types'
```

**b) Add asset types query and state inside the component** (after existing hooks):
```typescript
  const { data: assetTypes = [] } = useQuery({
    queryKey: ['asset-types'],
    queryFn: listAssetTypes,
  })
  const [newTypeName, setNewTypeName] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingName, setEditingName] = useState('')
```

**c) Add mutations:**
```typescript
  const { mutate: doCreateType, isPending: isCreating } = useMutation({
    mutationFn: () => createAssetType(newTypeName.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-types'] })
      setNewTypeName('')
      toast({ title: '類型已新增' })
    },
    onError: (e: Error) => toast({ title: e.message, variant: 'destructive' }),
  })

  const { mutate: doUpdateType } = useMutation({
    mutationFn: () => updateAssetType(editingId!, editingName.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-types'] })
      setEditingId(null)
      toast({ title: '已更新' })
    },
    onError: (e: Error) => toast({ title: e.message, variant: 'destructive' }),
  })

  const { mutate: doDeleteType } = useMutation({
    mutationFn: (id: number) => deleteAssetType(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asset-types'] })
      toast({ title: '已刪除' })
    },
    onError: (e: Error) => toast({ title: e.message, variant: 'destructive' }),
  })
```

**d) Add the section JSX** before the `<div className="border-t pt-6">` save button block:

```tsx
{/* 項目類型管理 */}
<section className="space-y-4">
  <h3 className="text-base font-semibold">項目類型</h3>
  <div className="rounded-lg border p-4 space-y-3">
    {assetTypes.length === 0 && (
      <p className="text-sm text-muted-foreground">尚無類型</p>
    )}
    {assetTypes.map((t) => (
      <div key={t.id} className="flex items-center gap-2">
        {editingId === t.id ? (
          <>
            <Input
              value={editingName}
              onChange={(e) => setEditingName(e.target.value)}
              className="h-8 max-w-xs"
              onKeyDown={(e) => { if (e.key === 'Enter') doUpdateType() }}
            />
            <Button type="button" size="sm" onClick={() => doUpdateType()}>儲存</Button>
            <Button type="button" size="sm" variant="outline" onClick={() => setEditingId(null)}>取消</Button>
          </>
        ) : (
          <>
            <span className="flex-1 text-sm">{t.name}</span>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => { setEditingId(t.id); setEditingName(t.name) }}
            >
              編輯
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="text-destructive hover:text-destructive"
              onClick={() => doDeleteType(t.id)}
            >
              刪除
            </Button>
          </>
        )}
      </div>
    ))}
    <div className="flex items-center gap-2 border-t pt-3">
      <Input
        placeholder="新增類型名稱..."
        value={newTypeName}
        onChange={(e) => setNewTypeName(e.target.value)}
        className="h-8 max-w-xs"
        onKeyDown={(e) => { if (e.key === 'Enter' && newTypeName.trim()) doCreateType() }}
      />
      <Button
        type="button"
        size="sm"
        disabled={!newTypeName.trim() || isCreating}
        onClick={() => doCreateType()}
      >
        新增
      </Button>
    </div>
  </div>
</section>
```

- [ ] **Step 2: TypeScript check**

```
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SystemSettingsPage.tsx
git commit -m "feat: add asset types management section to SystemSettingsPage"
```

---

### Task 13: Nav + label changes

**Files:**
- Modify: `frontend/src/layouts/AppLayout.tsx`
- Modify: `frontend/src/pages/SubscriptionNewPage.tsx`
- Modify: `frontend/src/pages/SubscriptionEditPage.tsx`

- [ ] **Step 1: Update AppLayout.tsx nav labels**

In both `desktopNavLinks` and `mobileNavLinks`, change:
```tsx
<NavLink to="/subscriptions" ...>訂閱列表</NavLink>
```
to:
```tsx
<NavLink to="/subscriptions" ...>項目管理</NavLink>
```

(There are two occurrences — desktop and mobile. Change both.)

- [ ] **Step 2: Update SubscriptionNewPage.tsx title**

Change:
```tsx
<h2 className="text-2xl font-bold">新增訂閱</h2>
```
to:
```tsx
<h2 className="text-2xl font-bold">新增項目</h2>
```

Also update the `toast` message from `訂閱已建立` to `項目已建立`.

- [ ] **Step 3: Update SubscriptionEditPage.tsx title**

In `frontend/src/pages/SubscriptionEditPage.tsx`, change the page title from `編輯訂閱` to `編輯項目` and the success toast from `訂閱已更新` to `項目已更新`.

- [ ] **Step 4: TypeScript check + lint**

```
npx tsc --noEmit && npm run lint
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/layouts/AppLayout.tsx frontend/src/pages/SubscriptionNewPage.tsx frontend/src/pages/SubscriptionEditPage.tsx
git commit -m "feat: rename nav and page titles from 訂閱 to 項目管理"
```

---

## End-to-End Smoke Test

After all tasks, verify manually:

1. Migrations applied (`alembic upgrade head` on target DB)
2. Start API: `uvicorn api.main:app --reload`
3. `GET /api/v1/asset-types` returns `[{id:1,name:"SaaS"},{id:2,name:"ERP"},{id:3,name:"網域"}]`
4. Create new item with type "網域" and no login_account — succeeds
5. Dashboard shows type badge next to expiring items
6. System Settings → 項目類型 section: create, rename, delete a type
7. Delete a type in use → shows error toast
