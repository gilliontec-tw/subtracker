# Expiry Notification Email Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send daily email reminders to configured recipients when a subscription's expiry date is within its `notification_days` window, deduplicating within the same calendar day.

**Architecture:** A standalone `scripts/run_notifications.py` entry point queries all active subscriptions due for notification via a new `list_due_for_notification` repository method, calls `CheckAndNotifyUseCase` which delegates email sending to an `EmailSender` interface, and writes `last_notified_date = today` after each successful send. Notifications stop naturally when the expiry date is updated (renewal) or status becomes non-active.

**Tech Stack:** Python `smtplib` (STARTTLS, port 587), SQLAlchemy async, Alembic migration, pytest + `unittest.mock`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `alembic/versions/003_add_last_notified_date.py` | DB migration: add `last_notified_date` column |
| Modify | `src/infrastructure/database/models.py` | Add `last_notified_date` to `SubscriptionModel` |
| Modify | `src/domain/entities/subscription.py` | Add `last_notified_date: date \| None = None` field |
| Modify | `src/domain/repositories/subscription_repository.py` | Add `list_due_for_notification` + `mark_notified` abstract methods |
| Modify | `src/infrastructure/database/repositories/subscription_repository.py` | Implement both methods; update `_to_entity` and `save` |
| Create | `src/application/interfaces/email_sender.py` | Abstract `EmailSender` interface |
| Create | `src/infrastructure/smtp/smtp_email_sender.py` | `SmtpEmailSender` using `smtplib` STARTTLS |
| Create | `src/application/use_cases/check_and_notify.py` | `CheckAndNotifyUseCase` orchestrating query → send → mark |
| Create | `scripts/run_notifications.py` | CLI entry point (scheduled via Windows Task Scheduler) |
| Modify | `.env` | Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` |
| Create | `tests/unit/test_check_and_notify_use_case.py` | Unit tests for use case |
| Create | `tests/unit/test_smtp_email_sender.py` | Unit tests for SMTP sender |
| Modify | `tests/unit/test_subscription_entity.py` | Assert `last_notified_date` defaults to `None` |

---

### Task 1: Alembic migration + model column

**Files:**
- Create: `backend/alembic/versions/003_add_last_notified_date.py`
- Modify: `backend/src/infrastructure/database/models.py`

- [ ] **Step 1: Create the migration file**

Create `backend/alembic/versions/003_add_last_notified_date.py`:

```python
"""add last_notified_date to saas_subscriptions

Revision ID: 003
Revises: 002
Create Date: 2026-05-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "saas_subscriptions",
        sa.Column("last_notified_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("saas_subscriptions", "last_notified_date")
```

- [ ] **Step 2: Add column to SQLAlchemy model**

In `backend/src/infrastructure/database/models.py`, add this line inside `SubscriptionModel`, after `next_billing_date`:

```python
last_notified_date = Column(Date)
```

The full `SubscriptionModel` class after edit (columns only, relationships unchanged):

```python
class SubscriptionModel(Base):
    __tablename__ = "saas_subscriptions"

    id = Column(Integer, primary_key=True)
    service_name = Column(String(255), nullable=False)
    login_account = Column(String(255))
    expiry_date = Column(Date, nullable=False)
    notification_emails = Column(Text)
    notification_days = Column(Integer, server_default="30")
    cost = Column(Numeric(10, 2))
    currency = Column(String(10), server_default="TWD")
    exchange_rate = Column(Numeric(12, 6))
    notes = Column(Text)
    owner_name = Column(String(255))
    category = Column(String(100))
    department = Column(String(100))
    billing_cycle = Column(String(20))
    payment_account = Column(String(255))
    auto_renew = Column(Boolean, server_default="false")
    trial_end_date = Column(Date)
    next_billing_date = Column(Date)
    last_notified_date = Column(Date)
    status = Column(String(20), server_default="active")
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payments = relationship("PaymentRecordModel", back_populates="subscription")
```

- [ ] **Step 3: Run the migration**

From `backend/` directory:

```bash
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003, add last_notified_date to saas_subscriptions
```

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/003_add_last_notified_date.py backend/src/infrastructure/database/models.py
git commit -m "feat: add last_notified_date column to saas_subscriptions"
```

---

### Task 2: Domain entity + repository interface

**Files:**
- Modify: `backend/src/domain/entities/subscription.py`
- Modify: `backend/src/domain/repositories/subscription_repository.py`
- Modify: `backend/tests/unit/test_subscription_entity.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_subscription_entity.py`:

```python
def test_last_notified_date_defaults_to_none():
    sub = make_subscription()
    assert sub.last_notified_date is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_subscription_entity.py::test_last_notified_date_defaults_to_none -v`

Expected: `FAILED` — `TypeError: Subscription.__init__() got an unexpected keyword argument` or `AttributeError`.

- [ ] **Step 3: Add field to Subscription entity**

In `backend/src/domain/entities/subscription.py`, add `last_notified_date` as the last optional field before `id`:

```python
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

SUPPORTED_CURRENCIES = ("TWD", "USD", "EUR", "JPY", "GBP", "CNY")


@dataclass
class Subscription:
    service_name: str
    login_account: str
    expiry_date: date
    notification_emails: list[str]
    notification_days: int

    cost: Decimal | None = None
    currency: str = "TWD"
    exchange_rate: Decimal | None = None
    notes: str | None = None
    owner_name: str | None = None
    category: str | None = None
    department: str | None = None
    billing_cycle: str | None = None
    payment_account: str | None = None
    auto_renew: bool = False
    trial_end_date: date | None = None
    next_billing_date: date | None = None
    last_notified_date: date | None = None
    status: str = "active"

    id: int | None = None
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_subscription_entity.py -v`

Expected: All tests `PASSED`.

- [ ] **Step 5: Add abstract methods to repository interface**

Replace the contents of `backend/src/domain/repositories/subscription_repository.py`:

```python
from abc import abstractmethod
from datetime import date

from domain.entities.subscription import Subscription
from domain.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription, int]):
    @abstractmethod
    async def list_paginated(
        self,
        limit: int,
        offset: int,
        show_cancelled: bool,
    ) -> tuple[list[Subscription], int]: ...

    @abstractmethod
    async def list_due_for_notification(self, today: date) -> list[Subscription]: ...

    @abstractmethod
    async def mark_notified(self, id: int, today: date) -> None: ...
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/domain/entities/subscription.py backend/src/domain/repositories/subscription_repository.py backend/tests/unit/test_subscription_entity.py
git commit -m "feat: add last_notified_date to entity and notification methods to repo interface"
```

---

### Task 3: Repository implementation

**Files:**
- Modify: `backend/src/infrastructure/database/repositories/subscription_repository.py`

- [ ] **Step 1: Update `_to_entity` to map `last_notified_date`**

In `backend/src/infrastructure/database/repositories/subscription_repository.py`, update `_to_entity` to include `last_notified_date`:

```python
def _to_entity(m: SubscriptionModel) -> Subscription:
    return Subscription(
        id=m.id,
        service_name=m.service_name,
        login_account=m.login_account or "",
        expiry_date=m.expiry_date,
        notification_emails=json.loads(m.notification_emails) if m.notification_emails else [],
        notification_days=m.notification_days if m.notification_days is not None else 30,
        cost=m.cost,
        currency=m.currency or "TWD",
        exchange_rate=m.exchange_rate,
        notes=m.notes,
        owner_name=m.owner_name,
        category=m.category,
        department=m.department,
        billing_cycle=m.billing_cycle,
        payment_account=m.payment_account,
        auto_renew=m.auto_renew or False,
        trial_end_date=m.trial_end_date,
        next_billing_date=m.next_billing_date,
        last_notified_date=m.last_notified_date,
        status=m.status or "active",
        deleted_at=m.deleted_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )
```

- [ ] **Step 2: Implement `list_due_for_notification`**

Add the following imports at the top of the file (after existing imports):

```python
from sqlalchemy import or_
```

Add this method inside `SqlSubscriptionRepository`:

```python
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
        s for s in candidates
        if s.notification_days > 0
        and (s.expiry_date - today).days <= s.notification_days
        and s.notification_emails
    ]
```

- [ ] **Step 3: Implement `mark_notified`**

Add this method inside `SqlSubscriptionRepository`:

```python
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

The `date` type needs to be imported. Add `from datetime import date` if not already present (check: the file currently imports `from datetime import UTC, datetime` — update to `from datetime import UTC, date, datetime`).

- [ ] **Step 4: Update `save` to persist `last_notified_date`**

In the `save` method, in the **update branch** (where `model.*` assignments happen), add:

```python
model.last_notified_date = entity.last_notified_date
```

In the **create branch** (inside `SubscriptionModel(...)` constructor), add:

```python
last_notified_date=entity.last_notified_date,
```

- [ ] **Step 5: Run existing tests to verify nothing is broken**

Run: `pytest tests/unit/ -v`

Expected: All tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/src/infrastructure/database/repositories/subscription_repository.py
git commit -m "feat: implement list_due_for_notification and mark_notified in SqlSubscriptionRepository"
```

---

### Task 4: EmailSender interface + SmtpEmailSender

**Files:**
- Create: `backend/src/application/interfaces/email_sender.py`
- Create: `backend/src/infrastructure/smtp/smtp_email_sender.py`
- Create: `backend/tests/unit/test_smtp_email_sender.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_smtp_email_sender.py`:

```python
from unittest.mock import MagicMock, patch

import pytest
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender


@pytest.fixture
def sender():
    return SmtpEmailSender(
        host="smtp.test.com",
        port=587,
        username="user@test.com",
        password="secret",
        from_addr="user@test.com",
    )


@pytest.mark.asyncio
async def test_connects_to_configured_host_and_port(sender):
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        await sender.send(to=["dest@test.com"], subject="Test", body="Hello")

        mock_smtp_class.assert_called_once_with("smtp.test.com", 587)


@pytest.mark.asyncio
async def test_uses_starttls_and_login(sender):
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        await sender.send(to=["dest@test.com"], subject="Test", body="Hello")

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.com", "secret")


@pytest.mark.asyncio
async def test_sends_to_all_recipients(sender):
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        await sender.send(
            to=["a@test.com", "b@test.com"],
            subject="Test",
            body="Hello",
        )

        call_args = mock_server.sendmail.call_args
        assert call_args[0][1] == ["a@test.com", "b@test.com"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_smtp_email_sender.py -v`

Expected: `ERROR` — `ModuleNotFoundError: No module named 'infrastructure.smtp.smtp_email_sender'`

- [ ] **Step 3: Create EmailSender interface**

Create `backend/src/application/interfaces/email_sender.py`:

```python
from abc import ABC, abstractmethod


class EmailSender(ABC):
    @abstractmethod
    async def send(self, to: list[str], subject: str, body: str) -> None: ...
```

- [ ] **Step 4: Create SmtpEmailSender**

Create `backend/src/infrastructure/smtp/smtp_email_sender.py`:

```python
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
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
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from = from_addr

    async def send(self, to: list[str], subject: str, body: str) -> None:
        await asyncio.to_thread(self._send_sync, to, subject, body)

    def _send_sync(self, to: list[str], subject: str, body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = ", ".join(to)
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(self._host, self._port) as server:
            server.starttls()
            server.login(self._username, self._password)
            server.sendmail(self._from, to, msg.as_string())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_smtp_email_sender.py -v`

Expected: All 3 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/src/application/interfaces/email_sender.py backend/src/infrastructure/smtp/smtp_email_sender.py backend/tests/unit/test_smtp_email_sender.py
git commit -m "feat: add EmailSender interface and SmtpEmailSender implementation"
```

---

### Task 5: CheckAndNotifyUseCase

**Files:**
- Create: `backend/src/application/use_cases/check_and_notify.py`
- Create: `backend/tests/unit/test_check_and_notify_use_case.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_check_and_notify_use_case.py`:

```python
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.check_and_notify import CheckAndNotifyUseCase
from domain.entities.subscription import Subscription


TODAY = date(2026, 5, 28)


def make_subscription(**kwargs) -> Subscription:
    defaults = dict(
        id=1,
        service_name="GitHub",
        login_account="user@corp.com",
        expiry_date=date(2026, 6, 5),
        notification_emails=["admin@corp.com"],
        notification_days=14,
        status="active",
    )
    defaults.update(kwargs)
    return Subscription(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def sender():
    return MagicMock()


@pytest.fixture
def use_case(repo, sender):
    return CheckAndNotifyUseCase(repo, sender)


@pytest.mark.asyncio
async def test_sends_email_for_due_subscription(use_case, repo, sender):
    sub = make_subscription()
    repo.list_due_for_notification = AsyncMock(return_value=[sub])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    count = await use_case.execute(today=TODAY)

    sender.send.assert_called_once()
    call_kwargs = sender.send.call_args[1]
    assert call_kwargs["to"] == ["admin@corp.com"]
    assert "GitHub" in call_kwargs["subject"]
    assert count == 1


@pytest.mark.asyncio
async def test_marks_notified_after_send(use_case, repo, sender):
    sub = make_subscription()
    repo.list_due_for_notification = AsyncMock(return_value=[sub])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    await use_case.execute(today=TODAY)

    repo.mark_notified.assert_called_once_with(1, TODAY)


@pytest.mark.asyncio
async def test_returns_count_of_sent_emails(use_case, repo, sender):
    subs = [make_subscription(id=1), make_subscription(id=2, service_name="Slack")]
    repo.list_due_for_notification = AsyncMock(return_value=subs)
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    count = await use_case.execute(today=TODAY)

    assert count == 2
    assert repo.mark_notified.call_count == 2


@pytest.mark.asyncio
async def test_no_emails_when_nothing_due(use_case, repo, sender):
    repo.list_due_for_notification = AsyncMock(return_value=[])
    sender.send = AsyncMock()

    count = await use_case.execute(today=TODAY)

    sender.send.assert_not_called()
    assert count == 0


@pytest.mark.asyncio
async def test_uses_todays_date_when_not_provided(use_case, repo, sender):
    repo.list_due_for_notification = AsyncMock(return_value=[])
    sender.send = AsyncMock()

    await use_case.execute()

    called_today = repo.list_due_for_notification.call_args[0][0]
    assert called_today == date.today()


@pytest.mark.asyncio
async def test_subject_includes_days_remaining(use_case, repo, sender):
    sub = make_subscription(expiry_date=date(2026, 6, 4))  # 7 days from TODAY
    repo.list_due_for_notification = AsyncMock(return_value=[sub])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    await use_case.execute(today=TODAY)

    call_kwargs = sender.send.call_args[1]
    assert "7" in call_kwargs["subject"]


@pytest.mark.asyncio
async def test_body_contains_service_and_expiry_info(use_case, repo, sender):
    sub = make_subscription()
    repo.list_due_for_notification = AsyncMock(return_value=[sub])
    repo.mark_notified = AsyncMock()
    sender.send = AsyncMock()

    await use_case.execute(today=TODAY)

    call_kwargs = sender.send.call_args[1]
    assert "GitHub" in call_kwargs["body"]
    assert "2026-06-05" in call_kwargs["body"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_check_and_notify_use_case.py -v`

Expected: `ERROR` — `ModuleNotFoundError: No module named 'application.use_cases.check_and_notify'`

- [ ] **Step 3: Implement CheckAndNotifyUseCase**

Create `backend/src/application/use_cases/check_and_notify.py`:

```python
from datetime import date

from application.interfaces.email_sender import EmailSender
from domain.entities.subscription import Subscription
from domain.repositories.subscription_repository import SubscriptionRepository


def _format_body(sub: Subscription, today: date) -> str:
    days = (sub.expiry_date - today).days
    cost_str = f"{sub.currency} {sub.cost}" if sub.cost else "—"
    return (
        f"您好，\n\n"
        f"提醒您，以下訂閱即將到期：\n\n"
        f"服務名稱：{sub.service_name}\n"
        f"到期日：{sub.expiry_date}（{days} 天後）\n"
        f"負責人：{sub.owner_name or '—'}\n"
        f"部門：{sub.department or '—'}\n"
        f"費用：{cost_str}\n\n"
        f"請確認是否需要續約。若已完成續約，請至 SubTrack 更新到期日，即可停止後續提醒。\n\n"
        f"此郵件由 SubTrack 自動發送，請勿回覆。"
    )


class CheckAndNotifyUseCase:
    def __init__(self, repo: SubscriptionRepository, email_sender: EmailSender) -> None:
        self._repo = repo
        self._sender = email_sender

    async def execute(self, today: date | None = None) -> int:
        if today is None:
            today = date.today()
        due = await self._repo.list_due_for_notification(today)
        sent = 0
        for sub in due:
            days = (sub.expiry_date - today).days
            subject = f"[SubTrack] {sub.service_name} 訂閱將於 {days} 天後到期"
            body = _format_body(sub, today)
            await self._sender.send(to=sub.notification_emails, subject=subject, body=body)
            await self._repo.mark_notified(sub.id, today)
            sent += 1
        return sent
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_check_and_notify_use_case.py -v`

Expected: All 7 tests `PASSED`.

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `pytest tests/unit/ -v`

Expected: All tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/src/application/use_cases/check_and_notify.py backend/tests/unit/test_check_and_notify_use_case.py
git commit -m "feat: add CheckAndNotifyUseCase with email body formatting"
```

---

### Task 6: Notification script + .env

**Files:**
- Create: `backend/scripts/run_notifications.py`
- Modify: `backend/.env`

- [ ] **Step 1: Add SMTP settings to `.env`**

Add to `backend/.env`:

```dotenv
SMTP_HOST=pollux4.url.com.tw
SMTP_PORT=587
SMTP_USER=service@gilliontec.com.tw
SMTP_PASSWORD=Gillion000!@
SMTP_FROM=service@gilliontec.com.tw
```

- [ ] **Step 2: Create the notification script**

Create `backend/scripts/run_notifications.py`:

```python
"""Run from backend/ directory: python scripts/run_notifications.py"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.config import get_settings
from application.use_cases.check_and_notify import CheckAndNotifyUseCase
from infrastructure.database.repositories.subscription_repository import SqlSubscriptionRepository
from infrastructure.database.session import AsyncSessionFactory
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender


async def main() -> None:
    settings = get_settings()
    sender = SmtpEmailSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        from_addr=settings.smtp_from,
    )
    async with AsyncSessionFactory() as session:
        repo = SqlSubscriptionRepository(session)
        use_case = CheckAndNotifyUseCase(repo, sender)
        sent = await use_case.execute()
    print(f"通知已發送：{sent} 封")


asyncio.run(main())
```

- [ ] **Step 3: Run the script to verify it works end-to-end**

From `backend/` directory:

```bash
python scripts/run_notifications.py
```

Expected output (if no subscriptions are due):
```
通知已發送：0 封
```

If there are subscriptions within their notification window: one email per subscription should arrive at the configured `notification_emails`.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/run_notifications.py backend/.env
git commit -m "feat: add run_notifications.py script and SMTP env config"
```

---

## Windows Task Scheduler Setup (manual, post-implementation)

To schedule the script to run daily at 08:00:

1. Open **Task Scheduler** → Create Basic Task
2. Name: `SubTrack Notifications`
3. Trigger: Daily at 08:00
4. Action: Start a program
   - Program: `C:\path\to\python.exe`
   - Arguments: `scripts/run_notifications.py`
   - Start in: `C:\path\to\saas-tracker\backend`
5. Save

To test manually at any time: `python scripts/run_notifications.py` from the `backend/` directory.
