# Payment Records Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add payment record CRUD with per-subscription history in the detail dialog and a global filter page.

**Architecture:** Flat routing under `/api/v1/payments`. No DB schema changes — `payment_records` table already exists. Follows existing clean architecture: domain entity → repository ABC → SQLAlchemy impl → use cases → Pydantic schemas → FastAPI router. Frontend adds two surfaces: `PaymentRecordList` inside `SubscriptionDetailDialog`, and a new `PaymentRecordsPage`.

**Tech Stack:** Python/FastAPI, SQLAlchemy async, Pydantic v2, React 19, TanStack Query v5, react-hook-form + zod, shadcn/ui

---

### Task 1: Domain entity + repository interface

**Files:**
- Create: `backend/src/domain/entities/payment_record.py`
- Create: `backend/src/domain/repositories/payment_record_repository.py`

- [ ] **Step 1: Create the domain entity**

Create `backend/src/domain/entities/payment_record.py`:

```python
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class PaymentRecord:
    subscription_id: int
    payment_date: date
    amount: Decimal
    currency: str
    source: str = "manual"
    notes: str | None = None
    id: int | None = None
    created_at: datetime | None = None
    created_by: int | None = None
    service_name: str | None = None  # populated by JOIN queries; not stored in DB
```

- [ ] **Step 2: Create the repository ABC**

Create `backend/src/domain/repositories/payment_record_repository.py`:

```python
from abc import ABC, abstractmethod
from datetime import date

from domain.entities.payment_record import PaymentRecord


class PaymentRecordRepository(ABC):
    @abstractmethod
    async def save(self, record: PaymentRecord) -> PaymentRecord: ...

    @abstractmethod
    async def get_by_id(self, payment_id: int) -> PaymentRecord | None: ...

    @abstractmethod
    async def list_by_subscription(self, subscription_id: int) -> list[PaymentRecord]: ...

    @abstractmethod
    async def list_by_filters(
        self, from_date: date, to_date: date, service_name: str | None
    ) -> list[PaymentRecord]: ...

    @abstractmethod
    async def delete(self, payment_id: int) -> None: ...
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/domain/entities/payment_record.py backend/src/domain/repositories/payment_record_repository.py
git commit -m "feat: add PaymentRecord entity and PaymentRecordRepository interface"
```

---

### Task 2: SqlPaymentRecordRepository

**Files:**
- Create: `backend/src/infrastructure/database/repositories/payment_record_repository.py`

No unit tests for this task (infra layer requires real DB).

- [ ] **Step 1: Create the SQL implementation**

Create `backend/src/infrastructure/database/repositories/payment_record_repository.py`:

```python
from datetime import UTC, date

from domain.entities.payment_record import PaymentRecord
from domain.exceptions import NotFoundException
from domain.repositories.payment_record_repository import PaymentRecordRepository
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import PaymentRecordModel, SubscriptionModel


def _to_entity(m: PaymentRecordModel, service_name: str | None = None) -> PaymentRecord:
    return PaymentRecord(
        id=m.id,
        subscription_id=m.subscription_id,
        payment_date=m.payment_date,
        amount=m.amount,
        currency=m.currency or "TWD",
        source=m.source or "manual",
        notes=m.notes,
        created_at=m.created_at.replace(tzinfo=UTC) if m.created_at else None,
        created_by=m.created_by,
        service_name=service_name,
    )


class SqlPaymentRecordRepository(PaymentRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _fetch_with_name(self, payment_id: int) -> PaymentRecord:
        result = await self._session.execute(
            select(PaymentRecordModel, SubscriptionModel.service_name)
            .join(
                SubscriptionModel,
                PaymentRecordModel.subscription_id == SubscriptionModel.id,
                isouter=True,
            )
            .where(PaymentRecordModel.id == payment_id)
        )
        row = result.one()
        return _to_entity(row[0], row[1])

    async def save(self, record: PaymentRecord) -> PaymentRecord:
        if record.id is not None:
            result = await self._session.execute(
                select(PaymentRecordModel).where(PaymentRecordModel.id == record.id)
            )
            try:
                model = result.scalar_one()
            except NoResultFound:
                raise NotFoundException()
            model.payment_date = record.payment_date
            model.amount = record.amount
            model.currency = record.currency
            model.notes = record.notes
        else:
            model = PaymentRecordModel(
                subscription_id=record.subscription_id,
                payment_date=record.payment_date,
                amount=record.amount,
                currency=record.currency,
                source=record.source,
                notes=record.notes,
                created_by=record.created_by,
            )
            self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return await self._fetch_with_name(model.id)

    async def get_by_id(self, payment_id: int) -> PaymentRecord | None:
        result = await self._session.execute(
            select(PaymentRecordModel).where(PaymentRecordModel.id == payment_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return await self._fetch_with_name(payment_id)

    async def list_by_subscription(self, subscription_id: int) -> list[PaymentRecord]:
        result = await self._session.execute(
            select(PaymentRecordModel, SubscriptionModel.service_name)
            .join(
                SubscriptionModel,
                PaymentRecordModel.subscription_id == SubscriptionModel.id,
                isouter=True,
            )
            .where(PaymentRecordModel.subscription_id == subscription_id)
            .order_by(PaymentRecordModel.payment_date.desc())
        )
        return [_to_entity(row[0], row[1]) for row in result.all()]

    async def list_by_filters(
        self, from_date: date, to_date: date, service_name: str | None
    ) -> list[PaymentRecord]:
        filters = [
            PaymentRecordModel.payment_date >= from_date,
            PaymentRecordModel.payment_date <= to_date,
        ]
        if service_name:
            filters.append(SubscriptionModel.service_name.ilike(f"%{service_name}%"))
        result = await self._session.execute(
            select(PaymentRecordModel, SubscriptionModel.service_name)
            .join(
                SubscriptionModel,
                PaymentRecordModel.subscription_id == SubscriptionModel.id,
                isouter=True,
            )
            .where(*filters)
            .order_by(PaymentRecordModel.payment_date.desc())
            .limit(500)
        )
        return [_to_entity(row[0], row[1]) for row in result.all()]

    async def delete(self, payment_id: int) -> None:
        result = await self._session.execute(
            select(PaymentRecordModel).where(PaymentRecordModel.id == payment_id)
        )
        try:
            model = result.scalar_one()
        except NoResultFound:
            raise NotFoundException()
        await self._session.delete(model)
        await self._session.commit()
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/infrastructure/database/repositories/payment_record_repository.py
git commit -m "feat: add SqlPaymentRecordRepository"
```

---

### Task 3: CreatePaymentRecordUseCase + tests

**Files:**
- Create: `backend/src/application/use_cases/create_payment_record.py`
- Create: `backend/tests/unit/test_create_payment_record_use_case.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_create_payment_record_use_case.py`:

```python
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.create_payment_record import CreatePaymentRecordUseCase
from domain.entities.payment_record import PaymentRecord
from domain.entities.subscription import Subscription
from domain.exceptions import NotFoundException


def make_sub(**kwargs) -> Subscription:
    defaults = dict(
        id=1,
        service_name="GitHub",
        login_account="u@corp.com",
        expiry_date=date(2027, 1, 1),
        notification_emails=[],
        notification_days=30,
    )
    defaults.update(kwargs)
    return Subscription(**defaults)


def make_record(**kwargs) -> PaymentRecord:
    defaults = dict(
        id=10,
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
    )
    defaults.update(kwargs)
    return PaymentRecord(**defaults)


@pytest.mark.asyncio
async def test_raises_not_found_when_subscription_missing():
    repo = MagicMock()
    sub_repo = MagicMock()
    sub_repo.get_by_id = AsyncMock(return_value=None)
    uc = CreatePaymentRecordUseCase(repo, sub_repo)
    with pytest.raises(NotFoundException):
        await uc.execute(
            subscription_id=999,
            payment_date=date(2026, 5, 1),
            amount=Decimal("1200.00"),
            currency="TWD",
        )


@pytest.mark.asyncio
async def test_saves_with_source_manual_and_returns_record():
    repo = MagicMock()
    sub_repo = MagicMock()
    sub_repo.get_by_id = AsyncMock(return_value=make_sub())
    repo.save = AsyncMock(return_value=make_record())
    uc = CreatePaymentRecordUseCase(repo, sub_repo, actor_user_id=1)
    result = await uc.execute(
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
    )
    assert result.id == 10
    saved = repo.save.call_args[0][0]
    assert saved.source == "manual"
    assert saved.created_by == 1


@pytest.mark.asyncio
async def test_saves_with_notes():
    repo = MagicMock()
    sub_repo = MagicMock()
    sub_repo.get_by_id = AsyncMock(return_value=make_sub())
    repo.save = AsyncMock(return_value=make_record())
    uc = CreatePaymentRecordUseCase(repo, sub_repo)
    await uc.execute(
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
        notes="年繳",
    )
    saved = repo.save.call_args[0][0]
    assert saved.notes == "年繳"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/unit/test_create_payment_record_use_case.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `create_payment_record`

- [ ] **Step 3: Implement the use case**

Create `backend/src/application/use_cases/create_payment_record.py`:

```python
from datetime import date
from decimal import Decimal

from domain.entities.payment_record import PaymentRecord
from domain.exceptions import NotFoundException
from domain.repositories.payment_record_repository import PaymentRecordRepository
from domain.repositories.subscription_repository import SubscriptionRepository


class CreatePaymentRecordUseCase:
    def __init__(
        self,
        repo: PaymentRecordRepository,
        sub_repo: SubscriptionRepository,
        actor_user_id: int | None = None,
    ) -> None:
        self._repo = repo
        self._sub_repo = sub_repo
        self._actor_user_id = actor_user_id

    async def execute(
        self,
        subscription_id: int,
        payment_date: date,
        amount: Decimal,
        currency: str = "TWD",
        notes: str | None = None,
    ) -> PaymentRecord:
        sub = await self._sub_repo.get_by_id(subscription_id)
        if sub is None:
            raise NotFoundException()
        record = PaymentRecord(
            subscription_id=subscription_id,
            payment_date=payment_date,
            amount=amount,
            currency=currency,
            source="manual",
            notes=notes,
            created_by=self._actor_user_id,
        )
        return await self._repo.save(record)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_create_payment_record_use_case.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/src/application/use_cases/create_payment_record.py backend/tests/unit/test_create_payment_record_use_case.py
git commit -m "feat: add CreatePaymentRecordUseCase"
```

---

### Task 4: UpdatePaymentRecordUseCase + tests

**Files:**
- Create: `backend/src/application/use_cases/update_payment_record.py`
- Create: `backend/tests/unit/test_update_payment_record_use_case.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_update_payment_record_use_case.py`:

```python
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.update_payment_record import UpdatePaymentRecordUseCase
from domain.entities.payment_record import PaymentRecord
from domain.exceptions import NotFoundException


def make_record(**kwargs) -> PaymentRecord:
    defaults = dict(
        id=10,
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
    )
    defaults.update(kwargs)
    return PaymentRecord(**defaults)


@pytest.mark.asyncio
async def test_raises_not_found_when_payment_missing():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    uc = UpdatePaymentRecordUseCase(repo)
    with pytest.raises(NotFoundException):
        await uc.execute(payment_id=999, amount=Decimal("500.00"))


@pytest.mark.asyncio
async def test_applies_partial_updates_and_saves():
    repo = MagicMock()
    original = make_record()
    updated = make_record(amount=Decimal("999.00"), notes="edited")
    repo.get_by_id = AsyncMock(return_value=original)
    repo.save = AsyncMock(return_value=updated)
    uc = UpdatePaymentRecordUseCase(repo)
    result = await uc.execute(payment_id=10, amount=Decimal("999.00"), notes="edited")
    assert result.amount == Decimal("999.00")
    saved = repo.save.call_args[0][0]
    assert saved.amount == Decimal("999.00")
    assert saved.notes == "edited"


@pytest.mark.asyncio
async def test_unspecified_fields_are_unchanged():
    repo = MagicMock()
    original = make_record(currency="USD", notes="original")
    repo.get_by_id = AsyncMock(return_value=original)
    repo.save = AsyncMock(return_value=original)
    uc = UpdatePaymentRecordUseCase(repo)
    await uc.execute(payment_id=10, notes="changed")
    saved = repo.save.call_args[0][0]
    assert saved.currency == "USD"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_update_payment_record_use_case.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement the use case**

Create `backend/src/application/use_cases/update_payment_record.py`:

```python
from domain.entities.payment_record import PaymentRecord
from domain.exceptions import NotFoundException
from domain.repositories.payment_record_repository import PaymentRecordRepository


class UpdatePaymentRecordUseCase:
    def __init__(self, repo: PaymentRecordRepository) -> None:
        self._repo = repo

    async def execute(self, payment_id: int, **updates) -> PaymentRecord:
        record = await self._repo.get_by_id(payment_id)
        if record is None:
            raise NotFoundException()
        for field, value in updates.items():
            setattr(record, field, value)
        return await self._repo.save(record)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_update_payment_record_use_case.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/src/application/use_cases/update_payment_record.py backend/tests/unit/test_update_payment_record_use_case.py
git commit -m "feat: add UpdatePaymentRecordUseCase"
```

---

### Task 5: DeletePaymentRecordUseCase + tests

**Files:**
- Create: `backend/src/application/use_cases/delete_payment_record.py`
- Create: `backend/tests/unit/test_delete_payment_record_use_case.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_delete_payment_record_use_case.py`:

```python
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.delete_payment_record import DeletePaymentRecordUseCase
from domain.entities.payment_record import PaymentRecord
from domain.exceptions import NotFoundException


def make_record(**kwargs) -> PaymentRecord:
    defaults = dict(
        id=10,
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
    )
    defaults.update(kwargs)
    return PaymentRecord(**defaults)


@pytest.mark.asyncio
async def test_raises_not_found_when_payment_missing():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    uc = DeletePaymentRecordUseCase(repo)
    with pytest.raises(NotFoundException):
        await uc.execute(payment_id=999)


@pytest.mark.asyncio
async def test_calls_delete_with_correct_id():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=make_record(id=10))
    repo.delete = AsyncMock()
    uc = DeletePaymentRecordUseCase(repo)
    await uc.execute(payment_id=10)
    repo.delete.assert_called_once_with(10)


@pytest.mark.asyncio
async def test_returns_none():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=make_record())
    repo.delete = AsyncMock()
    uc = DeletePaymentRecordUseCase(repo)
    result = await uc.execute(payment_id=10)
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_delete_payment_record_use_case.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement the use case**

Create `backend/src/application/use_cases/delete_payment_record.py`:

```python
from domain.exceptions import NotFoundException
from domain.repositories.payment_record_repository import PaymentRecordRepository


class DeletePaymentRecordUseCase:
    def __init__(self, repo: PaymentRecordRepository) -> None:
        self._repo = repo

    async def execute(self, payment_id: int) -> None:
        record = await self._repo.get_by_id(payment_id)
        if record is None:
            raise NotFoundException()
        await self._repo.delete(payment_id)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_delete_payment_record_use_case.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/src/application/use_cases/delete_payment_record.py backend/tests/unit/test_delete_payment_record_use_case.py
git commit -m "feat: add DeletePaymentRecordUseCase"
```

---

### Task 6: ListPaymentRecordsUseCase + tests

**Files:**
- Create: `backend/src/application/use_cases/list_payment_records.py`
- Create: `backend/tests/unit/test_list_payment_records_use_case.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_list_payment_records_use_case.py`:

```python
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.list_payment_records import ListPaymentRecordsUseCase
from domain.entities.payment_record import PaymentRecord


def make_record(**kwargs) -> PaymentRecord:
    defaults = dict(
        id=1,
        subscription_id=1,
        payment_date=date(2026, 5, 1),
        amount=Decimal("1200.00"),
        currency="TWD",
    )
    defaults.update(kwargs)
    return PaymentRecord(**defaults)


@pytest.mark.asyncio
async def test_subscription_id_path_calls_list_by_subscription():
    repo = MagicMock()
    repo.list_by_subscription = AsyncMock(return_value=[make_record()])
    uc = ListPaymentRecordsUseCase(repo)
    result = await uc.execute(subscription_id=1)
    repo.list_by_subscription.assert_called_once_with(1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_date_range_path_calls_list_by_filters():
    repo = MagicMock()
    repo.list_by_filters = AsyncMock(return_value=[make_record()])
    uc = ListPaymentRecordsUseCase(repo)
    from_date = date(2026, 5, 1)
    to_date = date(2026, 5, 31)
    result = await uc.execute(from_date=from_date, to_date=to_date, service_name="GitHub")
    repo.list_by_filters.assert_called_once_with(from_date, to_date, "GitHub")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_no_params_returns_empty_list():
    repo = MagicMock()
    uc = ListPaymentRecordsUseCase(repo)
    result = await uc.execute()
    assert result == []
    repo.list_by_subscription.assert_not_called() if hasattr(repo, 'list_by_subscription') else None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_list_payment_records_use_case.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement the use case**

Create `backend/src/application/use_cases/list_payment_records.py`:

```python
from datetime import date

from domain.entities.payment_record import PaymentRecord
from domain.repositories.payment_record_repository import PaymentRecordRepository


class ListPaymentRecordsUseCase:
    def __init__(self, repo: PaymentRecordRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        subscription_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        service_name: str | None = None,
    ) -> list[PaymentRecord]:
        if subscription_id is not None:
            return await self._repo.list_by_subscription(subscription_id)
        if from_date is not None and to_date is not None:
            return await self._repo.list_by_filters(from_date, to_date, service_name)
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_list_payment_records_use_case.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Run all unit tests to make sure nothing is broken**

```bash
pytest tests/unit/ -q
```

Expected: all existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add backend/src/application/use_cases/list_payment_records.py backend/tests/unit/test_list_payment_records_use_case.py
git commit -m "feat: add ListPaymentRecordsUseCase"
```

---

### Task 7: API schemas, router, and main.py

**Files:**
- Create: `backend/src/api/v1/schemas/payment_record.py`
- Create: `backend/src/api/v1/routers/payments.py`
- Modify: `backend/src/api/main.py`

- [ ] **Step 1: Create Pydantic schemas**

Create `backend/src/api/v1/schemas/payment_record.py`:

```python
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class PaymentRecordCreate(BaseModel):
    subscription_id: int
    payment_date: date
    amount: Decimal
    currency: str = "TWD"
    notes: str | None = None


class PaymentRecordUpdate(BaseModel):
    payment_date: date | None = None
    amount: Decimal | None = None
    currency: str | None = None
    notes: str | None = None


class PaymentRecordResponse(BaseModel):
    id: int
    subscription_id: int
    service_name: str | None
    payment_date: date
    amount: Decimal
    currency: str
    notes: str | None
    source: str
    created_at: datetime
```

- [ ] **Step 2: Create the router**

Create `backend/src/api/v1/routers/payments.py`:

```python
from datetime import date

from application.use_cases.create_payment_record import CreatePaymentRecordUseCase
from application.use_cases.delete_payment_record import DeletePaymentRecordUseCase
from application.use_cases.list_payment_records import ListPaymentRecordsUseCase
from application.use_cases.update_payment_record import UpdatePaymentRecordUseCase
from domain.entities.user import User
from fastapi import APIRouter, Depends, Query
from infrastructure.database.repositories.payment_record_repository import (
    SqlPaymentRecordRepository,
)
from infrastructure.database.repositories.subscription_repository import (
    SqlSubscriptionRepository,
)
from infrastructure.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_current_user,
    require_can_create,
    require_can_delete,
    require_can_update,
)
from api.v1.schemas.base import ApiResponse
from api.v1.schemas.payment_record import (
    PaymentRecordCreate,
    PaymentRecordResponse,
    PaymentRecordUpdate,
)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.get("", response_model=ApiResponse[list[PaymentRecordResponse]])
async def list_payments(
    subscription_id: int | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service_name: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[PaymentRecordResponse]]:
    repo = SqlPaymentRecordRepository(db)
    use_case = ListPaymentRecordsUseCase(repo)
    records = await use_case.execute(
        subscription_id=subscription_id,
        from_date=from_date,
        to_date=to_date,
        service_name=service_name,
    )
    return ApiResponse.ok(data=[PaymentRecordResponse(**vars(r)) for r in records])


@router.post("", response_model=ApiResponse[PaymentRecordResponse], status_code=201)
async def create_payment(
    body: PaymentRecordCreate,
    current_user: User = Depends(require_can_create),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaymentRecordResponse]:
    sub_repo = SqlSubscriptionRepository(db)
    repo = SqlPaymentRecordRepository(db)
    use_case = CreatePaymentRecordUseCase(repo, sub_repo, actor_user_id=current_user.id)
    record = await use_case.execute(**body.model_dump())
    return ApiResponse.ok(data=PaymentRecordResponse(**vars(record)))


@router.put("/{id}", response_model=ApiResponse[PaymentRecordResponse])
async def update_payment(
    id: int,
    body: PaymentRecordUpdate,
    _: User = Depends(require_can_update),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaymentRecordResponse]:
    repo = SqlPaymentRecordRepository(db)
    use_case = UpdatePaymentRecordUseCase(repo)
    record = await use_case.execute(payment_id=id, **body.model_dump(exclude_unset=True))
    return ApiResponse.ok(data=PaymentRecordResponse(**vars(record)))


@router.delete("/{id}", response_model=ApiResponse[None])
async def delete_payment(
    id: int,
    _: User = Depends(require_can_delete),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    repo = SqlPaymentRecordRepository(db)
    use_case = DeletePaymentRecordUseCase(repo)
    await use_case.execute(payment_id=id)
    return ApiResponse.ok(message="付款紀錄已刪除")
```

- [ ] **Step 3: Register router in main.py**

In `backend/src/api/main.py`, add after the existing imports and `include_router` calls:

Add import at line 8 (after `audit_log` import):
```python
from api.v1.routers.payments import router as payments_router
```

Add inside `create_app()` after `app.include_router(audit_log_router)`:
```python
    app.include_router(payments_router)
```

- [ ] **Step 4: Run all unit tests**

```bash
cd backend && pytest tests/unit/ -q
```

Expected: all existing tests pass (same count as before)

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/v1/schemas/payment_record.py backend/src/api/v1/routers/payments.py backend/src/api/main.py
git commit -m "feat: add payments API schemas, router, and register in main"
```

---

### Task 8: Frontend types + API client

**Files:**
- Modify: `frontend/src/types/api.ts`
- Create: `frontend/src/api/payment_records.ts`

- [ ] **Step 1: Add PaymentRecord type**

In `frontend/src/types/api.ts`, add after the `AuditLogEntry` interface (at the end of the file):

```typescript
export interface PaymentRecord {
  id: number
  subscription_id: number
  service_name: string | null
  payment_date: string
  amount: string
  currency: string
  notes: string | null
  source: string
  created_at: string
}
```

- [ ] **Step 2: Create the API client**

Create `frontend/src/api/payment_records.ts`:

```typescript
import { api } from './client'
import type { ApiResponse, PaymentRecord } from '@/types/api'

export async function listBySubscription(subscriptionId: number): Promise<PaymentRecord[]> {
  const { data } = await api.get<ApiResponse<PaymentRecord[]>>('/api/v1/payments', {
    params: { subscription_id: subscriptionId },
  })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function listByFilters(
  fromDate: string,
  toDate: string,
  serviceName?: string,
): Promise<PaymentRecord[]> {
  const { data } = await api.get<ApiResponse<PaymentRecord[]>>('/api/v1/payments', {
    params: {
      from_date: fromDate,
      to_date: toDate,
      ...(serviceName ? { service_name: serviceName } : {}),
    },
  })
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function createPayment(body: {
  subscription_id: number
  payment_date: string
  amount: string
  currency: string
  notes?: string
}): Promise<PaymentRecord> {
  const { data } = await api.post<ApiResponse<PaymentRecord>>('/api/v1/payments', body)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function updatePayment(
  id: number,
  body: Partial<{ payment_date: string; amount: string; currency: string; notes: string | null }>,
): Promise<PaymentRecord> {
  const { data } = await api.put<ApiResponse<PaymentRecord>>(`/api/v1/payments/${id}`, body)
  if (!data.success || !data.data) throw new Error(data.message)
  return data.data
}

export async function deletePayment(id: number): Promise<void> {
  const { data } = await api.delete<ApiResponse<null>>(`/api/v1/payments/${id}`)
  if (!data.success) throw new Error(data.message)
}
```

- [ ] **Step 3: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/api/payment_records.ts
git commit -m "feat: add PaymentRecord type and API client"
```

---

### Task 9: PaymentRecordFormDialog

**Files:**
- Create: `frontend/src/components/payments/PaymentRecordFormDialog.tsx`

This dialog handles both create (when `subscriptionId` prop is set) and edit (when `record` prop is set).

- [ ] **Step 1: Create the component**

Create `frontend/src/components/payments/PaymentRecordFormDialog.tsx`:

```typescript
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createPayment, updatePayment } from '@/api/payment_records'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import type { PaymentRecord } from '@/types/api'

const CURRENCIES = ['TWD', 'USD', 'EUR', 'JPY', 'GBP', 'CNY']

function pad(n: number) {
  return String(n).padStart(2, '0')
}

function todayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const schema = z.object({
  payment_date: z.string().min(1, '必填'),
  amount: z
    .string()
    .min(1, '必填')
    .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, '請輸入有效金額'),
  currency: z.string().min(1, '必填'),
  notes: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  subscriptionId?: number
  record?: PaymentRecord
}

export default function PaymentRecordFormDialog({
  open,
  onOpenChange,
  subscriptionId,
  record,
}: Props) {
  const isEdit = !!record
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { payment_date: todayStr(), currency: 'TWD', notes: '' },
  })

  const currency = watch('currency')

  useEffect(() => {
    if (open) {
      reset(
        record
          ? {
              payment_date: record.payment_date,
              amount: record.amount,
              currency: record.currency,
              notes: record.notes ?? '',
            }
          : { payment_date: todayStr(), amount: '', currency: 'TWD', notes: '' },
      )
    }
  }, [open, record, reset])

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) => {
      if (isEdit && record) {
        return updatePayment(record.id, {
          ...values,
          notes: values.notes || null,
        })
      }
      return createPayment({
        subscription_id: subscriptionId!,
        ...values,
        notes: values.notes || undefined,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] })
      toast({ title: isEdit ? '付款紀錄已更新' : '付款紀錄已新增' })
      onOpenChange(false)
    },
    onError: () => {
      toast({ title: isEdit ? '更新失敗' : '新增失敗', variant: 'destructive' })
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{isEdit ? '編輯付款紀錄' : '新增付款紀錄'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4 pt-2">
          <div>
            <label className="text-sm font-medium">付款日期</label>
            <Input type="date" {...register('payment_date')} className="mt-1" />
            {errors.payment_date && (
              <p className="mt-1 text-xs text-destructive">{errors.payment_date.message}</p>
            )}
          </div>
          <div>
            <label className="text-sm font-medium">金額</label>
            <Input type="number" step="0.01" min="0.01" {...register('amount')} className="mt-1" />
            {errors.amount && (
              <p className="mt-1 text-xs text-destructive">{errors.amount.message}</p>
            )}
          </div>
          <div>
            <label className="text-sm font-medium">幣別</label>
            <Select
              value={currency}
              onValueChange={(v) => setValue('currency', v, { shouldValidate: true })}
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm font-medium">備註</label>
            <Input {...register('notes')} className="mt-1" placeholder="選填" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? '儲存中...' : '儲存'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/payments/PaymentRecordFormDialog.tsx
git commit -m "feat: add PaymentRecordFormDialog"
```

---

### Task 10: PaymentRecordList + wire into SubscriptionDetailDialog

**Files:**
- Create: `frontend/src/components/payments/PaymentRecordList.tsx`
- Modify: `frontend/src/components/subscriptions/SubscriptionDetailDialog.tsx`

- [ ] **Step 1: Create PaymentRecordList**

Create `frontend/src/components/payments/PaymentRecordList.tsx`:

```typescript
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listBySubscription, deletePayment } from '@/api/payment_records'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Pencil, Trash2, Plus } from 'lucide-react'
import PaymentRecordFormDialog from './PaymentRecordFormDialog'
import { useAuthStore } from '@/stores/authStore'
import { useToast } from '@/hooks/use-toast'
import type { PaymentRecord } from '@/types/api'

interface Props {
  subscriptionId: number
}

export default function PaymentRecordList({ subscriptionId }: Props) {
  const { currentUser } = useAuthStore()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<PaymentRecord | undefined>(undefined)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['payments', 'subscription', subscriptionId],
    queryFn: () => listBySubscription(subscriptionId),
  })

  const { mutate: doDelete, isPending: isDeleting } = useMutation({
    mutationFn: deletePayment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] })
      toast({ title: '付款紀錄已刪除' })
      setDeletingId(null)
    },
    onError: () => {
      toast({ title: '刪除失敗', variant: 'destructive' })
      setDeletingId(null)
    },
  })

  const records = data ?? []
  const canCreate = currentUser?.can_create || currentUser?.role === 'admin'
  const canUpdate = currentUser?.can_update || currentUser?.role === 'admin'
  const canDelete = currentUser?.can_delete || currentUser?.role === 'admin'
  const hasActions = canUpdate || canDelete

  return (
    <div className="mt-4 border-t pt-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium">付款紀錄</span>
        {canCreate && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setEditing(undefined)
              setFormOpen(true)
            }}
          >
            <Plus className="mr-1 size-3" />
            新增付款
          </Button>
        )}
      </div>

      {isLoading && <p className="text-xs text-muted-foreground">載入中...</p>}
      {!isLoading && records.length === 0 && (
        <p className="py-2 text-xs text-muted-foreground">尚無付款紀錄</p>
      )}
      {!isLoading && records.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">付款日期</TableHead>
              <TableHead className="text-xs">金額</TableHead>
              <TableHead className="text-xs">幣別</TableHead>
              <TableHead className="text-xs">備註</TableHead>
              {hasActions && <TableHead className="text-right text-xs">操作</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="text-xs">{r.payment_date}</TableCell>
                <TableCell className="text-xs">{r.amount}</TableCell>
                <TableCell className="text-xs">{r.currency}</TableCell>
                <TableCell className="text-xs">{r.notes ?? '—'}</TableCell>
                {hasActions && (
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      {canUpdate && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-6"
                          onClick={() => {
                            setEditing(r)
                            setFormOpen(true)
                          }}
                        >
                          <Pencil className="size-3" />
                        </Button>
                      )}
                      {canDelete && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-6"
                          onClick={() => setDeletingId(r.id)}
                        >
                          <Trash2 className="size-3 text-destructive" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <PaymentRecordFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        subscriptionId={subscriptionId}
        record={editing}
      />

      <Dialog open={deletingId !== null} onOpenChange={(open) => { if (!open) setDeletingId(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>確認刪除</DialogTitle>
            <DialogDescription>確定要刪除此付款紀錄嗎？此操作無法復原。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingId(null)} disabled={isDeleting}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={() => deletingId !== null && doDelete(deletingId)}
              disabled={isDeleting}
            >
              {isDeleting ? '刪除中...' : '確認刪除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
```

- [ ] **Step 2: Wire into SubscriptionDetailDialog**

In `frontend/src/components/subscriptions/SubscriptionDetailDialog.tsx`:

Add import after the existing imports:
```typescript
import PaymentRecordList from '@/components/payments/PaymentRecordList'
```

Add `<PaymentRecordList>` just before `</DialogContent>` (after the closing `</div>` of the rows section):

Change the end of the JSX from:
```typescript
        </div>
      </DialogContent>
    </Dialog>
```

To:
```typescript
        </div>
        <PaymentRecordList subscriptionId={sub.id} />
      </DialogContent>
    </Dialog>
```

- [ ] **Step 3: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/payments/PaymentRecordList.tsx frontend/src/components/subscriptions/SubscriptionDetailDialog.tsx
git commit -m "feat: add PaymentRecordList and wire into SubscriptionDetailDialog"
```

---

### Task 11: PaymentRecordsPage + nav link + route

**Files:**
- Create: `frontend/src/pages/PaymentRecordsPage.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create PaymentRecordsPage**

Create `frontend/src/pages/PaymentRecordsPage.tsx`:

```typescript
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listByFilters, deletePayment } from '@/api/payment_records'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Pencil, Trash2 } from 'lucide-react'
import PaymentRecordFormDialog from '@/components/payments/PaymentRecordFormDialog'
import { useAuthStore } from '@/stores/authStore'
import { useToast } from '@/hooks/use-toast'
import type { PaymentRecord } from '@/types/api'

function pad(n: number) {
  return String(n).padStart(2, '0')
}

function localDateStr(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function defaultRange() {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 30)
  return { from: localDateStr(from), to: localDateStr(to) }
}

export default function PaymentRecordsPage() {
  const def = defaultRange()
  const [fromDate, setFromDate] = useState(def.from)
  const [toDate, setToDate] = useState(def.to)
  const [serviceName, setServiceName] = useState('')
  const [queryParams, setQueryParams] = useState({
    from: def.from,
    to: def.to,
    service: '',
  })
  const [editing, setEditing] = useState<PaymentRecord | undefined>(undefined)
  const [formOpen, setFormOpen] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const { currentUser } = useAuthStore()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const canUpdate = currentUser?.can_update || currentUser?.role === 'admin'
  const canDelete = currentUser?.can_delete || currentUser?.role === 'admin'
  const hasActions = canUpdate || canDelete

  const { data, isLoading, isError } = useQuery({
    queryKey: ['payments', 'global', queryParams.from, queryParams.to, queryParams.service],
    queryFn: () =>
      listByFilters(queryParams.from, queryParams.to, queryParams.service || undefined),
  })

  const { mutate: doDelete, isPending: isDeleting } = useMutation({
    mutationFn: deletePayment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] })
      toast({ title: '付款紀錄已刪除' })
      setDeletingId(null)
    },
    onError: () => {
      toast({ title: '刪除失敗', variant: 'destructive' })
      setDeletingId(null)
    },
  })

  const records = data ?? []

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">付款紀錄</h2>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="date"
          value={fromDate}
          max={toDate}
          onChange={(e) => setFromDate(e.target.value)}
          className="rounded-md border px-3 py-1.5 text-sm"
        />
        <span className="text-sm text-muted-foreground">至</span>
        <input
          type="date"
          value={toDate}
          min={fromDate}
          onChange={(e) => setToDate(e.target.value)}
          className="rounded-md border px-3 py-1.5 text-sm"
        />
        <Input
          placeholder="訂閱名稱"
          value={serviceName}
          onChange={(e) => setServiceName(e.target.value)}
          className="max-w-40"
        />
        <Button
          onClick={() =>
            setQueryParams({ from: fromDate, to: toDate, service: serviceName })
          }
        >
          查詢
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground">載入中...</p>}
      {isError && <p className="text-destructive">載入失敗，請重新整理頁面</p>}
      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="whitespace-nowrap">付款日期</TableHead>
              <TableHead className="whitespace-nowrap">訂閱名稱</TableHead>
              <TableHead className="whitespace-nowrap">金額</TableHead>
              <TableHead className="whitespace-nowrap">幣別</TableHead>
              <TableHead>備註</TableHead>
              {hasActions && <TableHead className="text-right">操作</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={hasActions ? 6 : 5}
                  className="py-8 text-center text-muted-foreground"
                >
                  此區間內沒有付款紀錄
                </TableCell>
              </TableRow>
            )}
            {records.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="whitespace-nowrap text-sm">{r.payment_date}</TableCell>
                <TableCell className="text-sm">{r.service_name ?? '—'}</TableCell>
                <TableCell className="text-sm">{r.amount}</TableCell>
                <TableCell className="text-sm">{r.currency}</TableCell>
                <TableCell className="text-sm">{r.notes ?? '—'}</TableCell>
                {hasActions && (
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      {canUpdate && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            setEditing(r)
                            setFormOpen(true)
                          }}
                        >
                          <Pencil className="size-4" />
                        </Button>
                      )}
                      {canDelete && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeletingId(r.id)}
                        >
                          <Trash2 className="size-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <PaymentRecordFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        record={editing}
      />

      <Dialog
        open={deletingId !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingId(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>確認刪除</DialogTitle>
            <DialogDescription>確定要刪除此付款紀錄嗎？此操作無法復原。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeletingId(null)}
              disabled={isDeleting}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={() => deletingId !== null && doDelete(deletingId)}
              disabled={isDeleting}
            >
              {isDeleting ? '刪除中...' : '確認刪除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
```

- [ ] **Step 2: Add nav link in AppLayout.tsx**

In `frontend/src/layouts/AppLayout.tsx`, add "付款紀錄" link visible to all authenticated users. Add after the "訂閱列表" link and before the admin-only block:

Change:
```typescript
              <Link
                to="/subscriptions"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                訂閱列表
              </Link>
              {currentUser?.role === 'admin' && (
```

To:
```typescript
              <Link
                to="/subscriptions"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                訂閱列表
              </Link>
              <Link
                to="/payments"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                付款紀錄
              </Link>
              {currentUser?.role === 'admin' && (
```

- [ ] **Step 3: Add route in App.tsx**

In `frontend/src/App.tsx`:

Add import after `AuditLogPage` import:
```typescript
import PaymentRecordsPage from '@/pages/PaymentRecordsPage'
```

Add route after `<Route path="/audit-log" element={<AuditLogPage />} />`:
```typescript
              <Route path="/payments" element={<PaymentRecordsPage />} />
```

- [ ] **Step 4: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 5: Run all backend unit tests**

```bash
cd backend && pytest tests/unit/ -q
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PaymentRecordsPage.tsx frontend/src/layouts/AppLayout.tsx frontend/src/App.tsx
git commit -m "feat: add PaymentRecordsPage, nav link, and route"
```
