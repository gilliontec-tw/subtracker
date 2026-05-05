# Feature Enhancements Implementation Plan (A1/A2/A3/A4/D1/D2/E2/E3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add subscription status tags + cost tracking to the data model (A1/A2), pure-JS search/filter/sort/pagination/delete modal to index page (A3/A4/E2/E3), self-service change-password page (D1), and an admin-visible audit log that records who changed what (D2).

**Architecture:** A1/A2 extend the `Subscription` entity and DB schema with new columns (`status`, `cost`, `currency`); all layers from entity to template are updated in one task each. A3/A4/E2/E3 are pure client-side JS added to `index.html`; no backend changes required. D1 adds one use case + one route + one template. D2 adds a new `AuditEntry` entity, `audit_log` DB table, repository, and wires silent logging into the three subscription mutation routes; admin can view at `/admin/audit-log`.

**Tech Stack:** FastAPI, Jinja2, SQLAlchemy 2, pyodbc (SQL Server), Bootstrap 5.3, vanilla JS

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `src/application/use_cases/auth/change_password.py` | ChangePasswordUseCase |
| `src/interfaces/web/templates/account/__init__` | (directory placeholder) |
| `src/interfaces/web/templates/account/change_password.html` | Change-password form |
| `src/domain/entities/audit_entry.py` | AuditEntry dataclass |
| `src/domain/repositories/audit_log_repository.py` | Abstract AuditLogRepository |
| `src/infrastructure/database/sql_audit_log_repository.py` | SQLAlchemy AuditLogRepository |
| `src/interfaces/web/templates/admin/audit_log.html` | Admin audit log viewer |
| `tests/unit/auth/test_change_password.py` | Tests for ChangePasswordUseCase |

### Modified Files
| File | Change |
|------|--------|
| `src/domain/entities/subscription.py` | Add `SubscriptionStatus` enum + `status`, `cost`, `currency` fields |
| `src/infrastructure/database/models.py` | Add `status`/`cost`/`currency` cols to SubscriptionModel; add AuditLogModel |
| `src/infrastructure/database/sql_subscription_repository.py` | Wire new fields in `_to_entity`, `add`, `update` |
| `src/application/use_cases/create_subscription.py` | Add `status`, `cost`, `currency` params |
| `src/application/use_cases/update_subscription.py` | Add `status`, `cost`, `currency` params |
| `src/interfaces/web/dependencies.py` | Add `get_change_password_uc`, `get_audit_log_repo` |
| `src/interfaces/web/routes/subscriptions.py` | Add form fields; wire audit logging |
| `src/interfaces/web/routes/auth.py` | Add `/account/password` GET/POST |
| `src/interfaces/web/routes/admin.py` | Add `/admin/audit-log` route |
| `src/interfaces/web/templates/base.html` | Add Bootstrap JS bundle; add 修改密碼 + 操作紀錄 links |
| `src/interfaces/web/templates/index.html` | Status badge col, cost col, search/filter/sort/pagination/delete modal |
| `src/interfaces/web/templates/create.html` | Add status select, cost/currency fields |
| `src/interfaces/web/templates/edit.html` | Add status select, cost/currency fields |

---

## Task 1: A1 + A2 — Subscription Status & Cost (Entity → DB → Use Cases → Routes → Templates)

**Files:**
- Modify: `src/domain/entities/subscription.py`
- Modify: `src/infrastructure/database/models.py`
- Modify: `src/infrastructure/database/sql_subscription_repository.py`
- Modify: `src/application/use_cases/create_subscription.py`
- Modify: `src/application/use_cases/update_subscription.py`
- Modify: `src/interfaces/web/routes/subscriptions.py`
- Modify: `src/interfaces/web/templates/create.html`
- Modify: `src/interfaces/web/templates/edit.html`
- Modify: `src/interfaces/web/templates/index.html`
- Modify: `tests/unit/test_subscription_entity.py`
- SQL: manual ALTER TABLE in SSMS

---

- [ ] **Step 1: Write failing tests**

Add these two tests at the bottom of `tests/unit/test_subscription_entity.py`:

```python
from src.domain.entities.subscription import Subscription, NotificationDays, SubscriptionStatus
from decimal import Decimal

def test_subscription_status_defaults_to_active():
    sub = make_sub(date(2026, 12, 31), NotificationDays.SEVEN)
    assert sub.status == SubscriptionStatus.ACTIVE


def test_subscription_cost_defaults_to_none():
    sub = make_sub(date(2026, 12, 31), NotificationDays.SEVEN)
    assert sub.cost is None
    assert sub.currency == "TWD"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd /c/Users/Gillion-ADM-015/Desktop/Claude/saas-tracker
python -m pytest tests/unit/test_subscription_entity.py::test_subscription_status_defaults_to_active tests/unit/test_subscription_entity.py::test_subscription_cost_defaults_to_none -v
```
Expected: `ERROR ... cannot import name 'SubscriptionStatus'`

- [ ] **Step 3: Replace `src/domain/entities/subscription.py`**

```python
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import IntEnum, Enum


class NotificationDays(IntEnum):
    THREE = 3
    SEVEN = 7
    FOURTEEN = 14
    THIRTY = 30
    NINETY = 90
    ONE_TWENTY = 120


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    RENEWED = "renewed"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


@dataclass
class Subscription:
    service_name: str
    login_account: str
    expiry_date: date
    notification_emails: str  # 逗號分隔，例如 "alice@co.com,bob@co.com"
    notification_days: NotificationDays
    id: int | None = None
    is_active: bool = True
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    cost: Decimal | None = None
    currency: str = "TWD"
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def should_notify_today(self, today: date) -> bool:
        trigger = self.expiry_date - timedelta(days=self.notification_days.value)
        return today == trigger
```

- [ ] **Step 4: Run entity tests to confirm they pass**

```
python -m pytest tests/unit/test_subscription_entity.py -v
```
Expected: all entity tests pass (including the 2 new ones).

- [ ] **Step 5: Add columns to `src/infrastructure/database/models.py`**

Replace the full file with:

```python
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class SubscriptionModel(Base):
    __tablename__ = "saas_subscriptions"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    service_name        = Column(String(200), nullable=False)
    login_account       = Column(String(200), nullable=False)
    expiry_date         = Column(Date, nullable=False)
    notification_emails = Column(String(1000), nullable=False)
    notification_days   = Column(Integer, nullable=False)
    is_active           = Column(Boolean, nullable=False, default=True)
    status              = Column(String(20), nullable=False, default="active")
    cost                = Column(Numeric(10, 2), nullable=True)
    currency            = Column(String(10), nullable=True, default="TWD")
    notes               = Column(String(1000), nullable=True)
    created_at          = Column(DateTime, nullable=False, default=datetime.now)
    updated_at          = Column(DateTime, nullable=True, onupdate=datetime.now)


class UserModel(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    email           = Column(String(200), nullable=False, unique=True)
    display_name    = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(20), nullable=False, default="user")
    can_create      = Column(Boolean, nullable=False, default=False)
    can_update      = Column(Boolean, nullable=False, default=False)
    can_delete      = Column(Boolean, nullable=False, default=False)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime, nullable=False, default=datetime.now)
    last_login_at   = Column(DateTime, nullable=True)


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, nullable=False)
    user_email  = Column(String(200), nullable=False)
    action      = Column(String(20), nullable=False)   # create | update | delete
    target_type = Column(String(50), nullable=False)   # subscription
    target_id   = Column(Integer, nullable=False)
    target_name = Column(String(200), nullable=False)
    created_at  = Column(DateTime, nullable=False, default=datetime.now)
```

- [ ] **Step 6: Run ALTER TABLE in SSMS**

Connect to your SQL Server, select `subscription_tracker` database, and run:

```sql
USE subscription_tracker;
GO
ALTER TABLE saas_subscriptions ADD status   NVARCHAR(20)   NOT NULL DEFAULT 'active';
ALTER TABLE saas_subscriptions ADD cost     DECIMAL(10,2)  NULL;
ALTER TABLE saas_subscriptions ADD currency NVARCHAR(10)   NULL DEFAULT 'TWD';
GO
```
Expected: `Commands completed successfully.`

- [ ] **Step 7: Update `src/infrastructure/database/sql_subscription_repository.py`**

Replace the full file:

```python
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from src.domain.entities.subscription import Subscription, NotificationDays, SubscriptionStatus
from src.domain.repositories.subscription_repository import SubscriptionRepository
from src.infrastructure.database.models import SubscriptionModel


class SqlSubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, model: SubscriptionModel) -> Subscription:
        return Subscription(
            id=model.id,
            service_name=model.service_name,
            login_account=model.login_account,
            expiry_date=model.expiry_date,
            notification_emails=model.notification_emails,
            notification_days=NotificationDays(model.notification_days),
            is_active=model.is_active,
            status=SubscriptionStatus(model.status) if model.status else SubscriptionStatus.ACTIVE,
            cost=Decimal(str(model.cost)) if model.cost is not None else None,
            currency=model.currency or "TWD",
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def add(self, subscription: Subscription) -> Subscription:
        model = SubscriptionModel(
            service_name=subscription.service_name,
            login_account=subscription.login_account,
            expiry_date=subscription.expiry_date,
            notification_emails=subscription.notification_emails,
            notification_days=subscription.notification_days.value,
            status=subscription.status.value,
            cost=subscription.cost,
            currency=subscription.currency,
            notes=subscription.notes,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, subscription_id: int) -> Subscription | None:
        model = self._session.get(SubscriptionModel, subscription_id)
        return self._to_entity(model) if model else None

    def get_all_active(self) -> list[Subscription]:
        models = (
            self._session.query(SubscriptionModel)
            .filter(SubscriptionModel.is_active == True)
            .order_by(SubscriptionModel.expiry_date)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def update(self, subscription: Subscription) -> Subscription:
        model = self._session.get(SubscriptionModel, subscription.id)
        if model is None:
            raise ValueError(f"Subscription {subscription.id} not found")
        model.service_name        = subscription.service_name
        model.login_account       = subscription.login_account
        model.expiry_date         = subscription.expiry_date
        model.notification_emails = subscription.notification_emails
        model.notification_days   = subscription.notification_days.value
        model.status              = subscription.status.value
        model.cost                = subscription.cost
        model.currency            = subscription.currency
        model.notes               = subscription.notes
        model.updated_at          = datetime.now()
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def deactivate(self, subscription_id: int) -> None:
        model = self._session.get(SubscriptionModel, subscription_id)
        if model:
            model.is_active  = False
            model.updated_at = datetime.now()
            self._session.commit()
```

- [ ] **Step 8: Update `src/application/use_cases/create_subscription.py`**

```python
from datetime import date
from decimal import Decimal
from src.domain.entities.subscription import Subscription, NotificationDays, SubscriptionStatus
from src.domain.repositories.subscription_repository import SubscriptionRepository


class CreateSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    def execute(
        self,
        service_name: str,
        login_account: str,
        expiry_date: date,
        notification_emails: str,
        notification_days: NotificationDays,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        cost: Decimal | None = None,
        currency: str = "TWD",
        notes: str | None = None,
    ) -> Subscription:
        entity = Subscription(
            service_name=service_name,
            login_account=login_account,
            expiry_date=expiry_date,
            notification_emails=notification_emails,
            notification_days=notification_days,
            status=status,
            cost=cost,
            currency=currency,
            notes=notes,
        )
        return self._repo.add(entity)
```

- [ ] **Step 9: Update `src/application/use_cases/update_subscription.py`**

```python
from datetime import date
from decimal import Decimal
from src.domain.entities.subscription import NotificationDays, SubscriptionStatus
from src.domain.repositories.subscription_repository import SubscriptionRepository


class UpdateSubscriptionUseCase:
    def __init__(self, repo: SubscriptionRepository) -> None:
        self._repo = repo

    def execute(
        self,
        subscription_id: int,
        service_name: str,
        login_account: str,
        expiry_date: date,
        notification_emails: str,
        notification_days: NotificationDays,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        cost: Decimal | None = None,
        currency: str = "TWD",
        notes: str | None = None,
    ):
        entity = self._repo.get_by_id(subscription_id)
        if entity is None:
            raise ValueError(f"Subscription {subscription_id} not found")
        entity.service_name       = service_name
        entity.login_account      = login_account
        entity.expiry_date        = expiry_date
        entity.notification_emails = notification_emails
        entity.notification_days  = notification_days
        entity.status             = status
        entity.cost               = cost
        entity.currency           = currency
        entity.notes              = notes
        return self._repo.update(entity)
```

- [ ] **Step 10: Update `src/interfaces/web/routes/subscriptions.py`**

Replace the full file:

```python
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from src.domain.entities.subscription import NotificationDays, SubscriptionStatus
from src.interfaces.web.dependencies import (
    get_create_uc, get_delete_uc, get_list_uc, get_single_uc, get_update_uc,
    get_current_user, require_create, require_update, require_delete,
)

router = APIRouter()
templates = Jinja2Templates(directory="src/interfaces/web/templates")

NOTIFICATION_OPTIONS = [
    (3,   "3 天前"),
    (7,   "7 天前"),
    (14,  "14 天前"),
    (30,  "1 個月前"),
    (90,  "3 個月前"),
    (120, "4 個月前"),
]

STATUS_OPTIONS = [
    ("active",    "使用中"),
    ("renewed",   "已續約"),
    ("cancelled", "已取消"),
    ("suspended", "暫停"),
]

CURRENCY_OPTIONS = ["TWD", "USD", "EUR", "JPY"]


@router.get("/")
def index(request: Request, uc=Depends(get_list_uc), current_user=Depends(get_current_user)):
    subscriptions = uc.execute()
    today = date.today()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "subscriptions": subscriptions,
        "today": today,
        "current_user": current_user,
    })


@router.get("/subscriptions/create")
def create_form(request: Request, current_user=Depends(require_create)):
    return templates.TemplateResponse("create.html", {
        "request": request,
        "notification_options": NOTIFICATION_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "currency_options": CURRENCY_OPTIONS,
        "current_user": current_user,
    })


@router.post("/subscriptions/create")
def create_submit(
    request: Request,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    notification_emails: str = Form(...),
    notification_days: int = Form(...),
    status: str = Form("active"),
    cost: str | None = Form(None),
    currency: str = Form("TWD"),
    notes: str | None = Form(None),
    uc=Depends(get_create_uc),
    current_user=Depends(require_create),
):
    uc.execute(
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
        notification_emails=notification_emails,
        notification_days=NotificationDays(notification_days),
        status=SubscriptionStatus(status),
        cost=Decimal(cost) if cost and cost.strip() else None,
        currency=currency,
        notes=notes or None,
    )
    return RedirectResponse("/", status_code=303)


@router.get("/subscriptions/{subscription_id}/edit")
def edit_form(
    request: Request,
    subscription_id: int,
    uc=Depends(get_single_uc),
    current_user=Depends(require_update),
):
    sub = uc.execute(subscription_id)
    return templates.TemplateResponse("edit.html", {
        "request": request,
        "sub": sub,
        "notification_options": NOTIFICATION_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "currency_options": CURRENCY_OPTIONS,
        "current_user": current_user,
    })


@router.post("/subscriptions/{subscription_id}/edit")
def edit_submit(
    subscription_id: int,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    notification_emails: str = Form(...),
    notification_days: int = Form(...),
    status: str = Form("active"),
    cost: str | None = Form(None),
    currency: str = Form("TWD"),
    notes: str | None = Form(None),
    uc=Depends(get_update_uc),
    current_user=Depends(require_update),
):
    uc.execute(
        subscription_id=subscription_id,
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
        notification_emails=notification_emails,
        notification_days=NotificationDays(notification_days),
        status=SubscriptionStatus(status),
        cost=Decimal(cost) if cost and cost.strip() else None,
        currency=currency,
        notes=notes or None,
    )
    return RedirectResponse("/", status_code=303)


@router.post("/subscriptions/{subscription_id}/delete")
def delete(
    subscription_id: int,
    uc=Depends(get_delete_uc),
    current_user=Depends(require_delete),
):
    uc.execute(subscription_id)
    return RedirectResponse("/", status_code=303)
```

- [ ] **Step 11: Update `src/interfaces/web/templates/create.html`**

Replace the full file:

```html
{% extends "base.html" %}
{% block content %}
<h4 class="mb-3">新增訂閱</h4>
<form method="POST" action="/subscriptions/create" style="max-width:560px">
  <div class="mb-3">
    <label class="form-label">服務名稱</label>
    <input type="text" name="service_name" class="form-control" required>
  </div>
  <div class="mb-3">
    <label class="form-label">登入帳號</label>
    <input type="text" name="login_account" class="form-control" required>
  </div>
  <div class="mb-3">
    <label class="form-label">到期日</label>
    <input type="date" name="expiry_date" class="form-control" required>
  </div>
  <div class="mb-3">
    <label class="form-label">狀態</label>
    <select name="status" class="form-select" required>
      {% for value, label in status_options %}
      <option value="{{ value }}">{{ label }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label class="form-label">費用（選填）</label>
    <div class="input-group">
      <input type="number" name="cost" step="0.01" min="0" class="form-control"
             placeholder="例如 1200">
      <select name="currency" class="form-select" style="max-width:100px">
        {% for c in currency_options %}
        <option value="{{ c }}">{{ c }}</option>
        {% endfor %}
      </select>
    </div>
  </div>
  <div class="mb-3">
    <label class="form-label">通知收件人 Email</label>
    <input type="text" name="notification_emails" class="form-control" required
           placeholder="可填多人，以逗號分隔：alice@co.com,bob@co.com">
    <div class="form-text">多個收件人請用逗號分隔</div>
  </div>
  <div class="mb-3">
    <label class="form-label">提前通知天數</label>
    <select name="notification_days" class="form-select" required>
      {% for value, label in notification_options %}
      <option value="{{ value }}">{{ label }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label class="form-label">備註</label>
    <textarea name="notes" class="form-control" rows="3"
              placeholder="合約編號、購買廠商、授權數量等（選填）"></textarea>
  </div>
  <button type="submit" class="btn btn-primary">儲存</button>
  <a href="/" class="btn btn-secondary ms-2">取消</a>
</form>
{% endblock %}
```

- [ ] **Step 12: Update `src/interfaces/web/templates/edit.html`**

Replace the full file:

```html
{% extends "base.html" %}
{% block content %}
<h4 class="mb-3">編輯訂閱</h4>
<form method="POST" action="/subscriptions/{{ sub.id }}/edit" style="max-width:560px">
  <div class="mb-3">
    <label class="form-label">服務名稱</label>
    <input type="text" name="service_name" class="form-control"
           value="{{ sub.service_name }}" required>
  </div>
  <div class="mb-3">
    <label class="form-label">登入帳號</label>
    <input type="text" name="login_account" class="form-control"
           value="{{ sub.login_account }}" required>
  </div>
  <div class="mb-3">
    <label class="form-label">到期日</label>
    <input type="date" name="expiry_date" class="form-control"
           value="{{ sub.expiry_date }}" required>
  </div>
  <div class="mb-3">
    <label class="form-label">狀態</label>
    <select name="status" class="form-select" required>
      {% for value, label in status_options %}
      <option value="{{ value }}" {% if value == sub.status.value %}selected{% endif %}>{{ label }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label class="form-label">費用（選填）</label>
    <div class="input-group">
      <input type="number" name="cost" step="0.01" min="0" class="form-control"
             value="{{ sub.cost if sub.cost else '' }}" placeholder="例如 1200">
      <select name="currency" class="form-select" style="max-width:100px">
        {% for c in currency_options %}
        <option value="{{ c }}" {% if c == sub.currency %}selected{% endif %}>{{ c }}</option>
        {% endfor %}
      </select>
    </div>
  </div>
  <div class="mb-3">
    <label class="form-label">通知收件人 Email</label>
    <input type="text" name="notification_emails" class="form-control"
           value="{{ sub.notification_emails }}" required>
    <div class="form-text">多個收件人請用逗號分隔</div>
  </div>
  <div class="mb-3">
    <label class="form-label">提前通知天數</label>
    <select name="notification_days" class="form-select" required>
      {% for value, label in notification_options %}
      <option value="{{ value }}" {% if value == sub.notification_days.value %}selected{% endif %}>
        {{ label }}
      </option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label class="form-label">備註</label>
    <textarea name="notes" class="form-control" rows="3"
              placeholder="合約編號、購買廠商、授權數量等（選填）">{{ sub.notes or '' }}</textarea>
  </div>
  <button type="submit" class="btn btn-primary">更新</button>
  <a href="/" class="btn btn-secondary ms-2">取消</a>
</form>
{% endblock %}
```

- [ ] **Step 13: Run full test suite**

```
python -m pytest tests/ -q
```
Expected: 30 passed (all existing + the 2 new entity tests).

- [ ] **Step 14: Commit**

```bash
cd /c/Users/Gillion-ADM-015/Desktop/Claude/saas-tracker
git add src/domain/entities/subscription.py \
        src/infrastructure/database/models.py \
        src/infrastructure/database/sql_subscription_repository.py \
        src/application/use_cases/create_subscription.py \
        src/application/use_cases/update_subscription.py \
        src/interfaces/web/routes/subscriptions.py \
        src/interfaces/web/templates/create.html \
        src/interfaces/web/templates/edit.html \
        tests/unit/test_subscription_entity.py
git commit -m "feat: add subscription status tags and cost tracking (A1, A2)"
```

Note: `index.html` is NOT committed yet — it will be updated in Task 2 along with the other frontend changes.

---

## Task 2: A3 + A4 + E2 + E3 — Frontend Enhancements (Search / Sort / Delete Modal / Pagination)

**Files:**
- Modify: `src/interfaces/web/templates/base.html` — add Bootstrap JS bundle
- Modify: `src/interfaces/web/templates/index.html` — full rewrite with all JS features

No backend changes. No new tests (pure HTML/JS).

---

- [ ] **Step 1: Add Bootstrap JS to `src/interfaces/web/templates/base.html`**

In `base.html`, find the closing `</body>` tag and insert the script tag before it:

```html
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
```

- [ ] **Step 2: Replace `src/interfaces/web/templates/index.html`**

```html
{% extends "base.html" %}
{% block content %}

{# ── Status badge lookup ───────────────────────────────────────────── #}
{% set STATUS = {
  'active':    ('bg-success',           '使用中'),
  'renewed':   ('bg-primary',           '已續約'),
  'cancelled': ('bg-secondary',         '已取消'),
  'suspended': ('bg-warning text-dark', '暫停')
} %}

{# ── Toolbar: search + filter + page size ─────────────────────────── #}
<div class="d-flex justify-content-between align-items-center mb-2">
  <h4 class="mb-0">訂閱清單</h4>
</div>
<div class="row g-2 mb-3 align-items-end">
  <div class="col-sm-5">
    <input type="text" id="searchInput" class="form-control form-control-sm"
           placeholder="搜尋服務名稱…">
  </div>
  <div class="col-sm-3">
    <select id="statusFilter" class="form-select form-select-sm">
      <option value="">全部狀態</option>
      <option value="active">使用中</option>
      <option value="renewed">已續約</option>
      <option value="cancelled">已取消</option>
      <option value="suspended">暫停</option>
    </select>
  </div>
  <div class="col-sm-2">
    <select id="pageSizeSelect" class="form-select form-select-sm">
      <option value="10">每頁 10 筆</option>
      <option value="25">每頁 25 筆</option>
      <option value="50">每頁 50 筆</option>
      <option value="999">全部</option>
    </select>
  </div>
</div>

{% if not subscriptions %}
  <p class="text-muted">目前沒有訂閱資料。</p>
{% else %}

<div class="table-responsive">
<table class="table table-bordered table-hover align-middle">
  <thead class="table-header">
    <tr>
      <th class="sortable" data-col="service">服務名稱 <span class="sort-icon">↕</span></th>
      <th>登入帳號</th>
      <th class="sortable" data-col="expiry">到期日 <span class="sort-icon">↕</span></th>
      <th class="sortable" data-col="status">狀態 <span class="sort-icon">↕</span></th>
      <th class="sortable" data-col="cost">費用 <span class="sort-icon">↕</span></th>
      <th>提前通知</th>
      <th>通知收件人</th>
      <th>備註</th>
      <th>操作</th>
    </tr>
  </thead>
  <tbody id="subTable">
    {% for sub in subscriptions %}
    {% set days_left = (sub.expiry_date - today).days %}
    {% set badge_cls, badge_txt = STATUS.get(sub.status.value, ('bg-secondary', sub.status.value)) %}
    <tr class="{% if days_left <= 7 %}table-danger{% elif days_left <= 30 %}table-warning{% endif %}"
        data-service="{{ sub.service_name | lower }}"
        data-expiry="{{ sub.expiry_date }}"
        data-status="{{ sub.status.value }}"
        data-cost="{{ sub.cost | float if sub.cost else 0 }}">
      <td>{{ sub.service_name }}</td>
      <td>{{ sub.login_account }}</td>
      <td>
        {{ sub.expiry_date }}
        <small class="text-muted">({{ days_left }} 天後)</small>
      </td>
      <td><span class="badge {{ badge_cls }}">{{ badge_txt }}</span></td>
      <td>
        {% if sub.cost %}
          {{ "%.2f" % sub.cost }} {{ sub.currency }}
        {% else %}
          <span class="text-muted">—</span>
        {% endif %}
      </td>
      <td>{{ sub.notification_days.value }} 天前</td>
      <td><small>{{ sub.notification_emails }}</small></td>
      <td><small class="text-muted">{{ sub.notes or '' }}</small></td>
      <td class="text-nowrap">
        {% if current_user.role == 'admin' or current_user.can_update %}
        <a href="/subscriptions/{{ sub.id }}/edit"
           class="btn btn-sm btn-outline-primary">編輯</a>
        {% endif %}
        {% if current_user.role == 'admin' or current_user.can_delete %}
        <button type="button" class="btn btn-sm btn-outline-danger delete-btn"
                data-id="{{ sub.id }}"
                data-name="{{ sub.service_name }}">刪除</button>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
</div>

{# ── Pagination controls ───────────────────────────────────────────── #}
<div class="d-flex justify-content-between align-items-center mt-2">
  <small id="pageInfo" class="text-muted"></small>
  <div>
    <button id="prevBtn" class="btn btn-sm btn-outline-secondary me-1">‹ 上一頁</button>
    <button id="nextBtn" class="btn btn-sm btn-outline-secondary">下一頁 ›</button>
  </div>
</div>

{% endif %}

{# ── Delete confirm modal ─────────────────────────────────────────── #}
<div class="modal fade" id="deleteModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-sm">
    <div class="modal-content">
      <div class="modal-header py-2">
        <h6 class="modal-title">確認刪除</h6>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body py-2">
        確認刪除「<strong id="deleteTargetName"></strong>」？<br>
        <small class="text-muted">此操作無法復原。</small>
      </div>
      <div class="modal-footer py-2">
        <button type="button" class="btn btn-sm btn-secondary"
                data-bs-dismiss="modal">取消</button>
        <form id="deleteForm" method="POST" class="d-inline">
          <button type="submit" class="btn btn-sm btn-danger">確認刪除</button>
        </form>
      </div>
    </div>
  </div>
</div>

<script>
// ── Delete modal ──────────────────────────────────────────────────────────
document.querySelectorAll('.delete-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.getElementById('deleteTargetName').textContent = btn.dataset.name;
    document.getElementById('deleteForm').action =
      '/subscriptions/' + btn.dataset.id + '/delete';
    new bootstrap.Modal(document.getElementById('deleteModal')).show();
  });
});

// ── Table filter / sort / pagination ─────────────────────────────────────
const tbody   = document.getElementById('subTable');
if (tbody) {
  const allRows    = Array.from(tbody.querySelectorAll('tr'));
  let   sortCol    = null;
  let   sortAsc    = true;
  let   currentPage = 1;

  function pageSize() {
    return parseInt(document.getElementById('pageSizeSelect').value);
  }

  function filtered() {
    const q  = document.getElementById('searchInput').value.toLowerCase();
    const st = document.getElementById('statusFilter').value;
    return allRows.filter(r =>
      r.dataset.service.includes(q) &&
      (!st || r.dataset.status === st)
    );
  }

  function sorted(rows) {
    if (!sortCol) return rows;
    return [...rows].sort((a, b) => {
      let av = a.dataset[sortCol] || '';
      let bv = b.dataset[sortCol] || '';
      // numeric sort for cost
      if (sortCol === 'cost') {
        return sortAsc ? parseFloat(av) - parseFloat(bv)
                       : parseFloat(bv) - parseFloat(av);
      }
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
  }

  function render() {
    const rows  = sorted(filtered());
    const total = rows.length;
    const ps    = pageSize();
    const pages = Math.max(1, Math.ceil(total / ps));
    if (currentPage > pages) currentPage = pages;

    allRows.forEach(r => r.style.display = 'none');
    const start = (currentPage - 1) * ps;
    rows.slice(start, start + ps).forEach(r => r.style.display = '');

    const end = Math.min(start + ps, total);
    document.getElementById('pageInfo').textContent =
      total === 0 ? '無符合資料' :
      `顯示 ${start + 1}–${end} / 共 ${total} 筆`;
    document.getElementById('prevBtn').disabled = currentPage <= 1;
    document.getElementById('nextBtn').disabled = currentPage >= pages;
  }

  document.getElementById('searchInput')
    .addEventListener('input',  () => { currentPage = 1; render(); });
  document.getElementById('statusFilter')
    .addEventListener('change', () => { currentPage = 1; render(); });
  document.getElementById('pageSizeSelect')
    .addEventListener('change', () => { currentPage = 1; render(); });
  document.getElementById('prevBtn')
    .addEventListener('click',  () => { currentPage--; render(); });
  document.getElementById('nextBtn')
    .addEventListener('click',  () => { currentPage++; render(); });

  document.querySelectorAll('th.sortable').forEach(th => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (sortCol === col) { sortAsc = !sortAsc; }
      else { sortCol = col; sortAsc = true; }
      document.querySelectorAll('.sort-icon').forEach(s => s.textContent = '↕');
      th.querySelector('.sort-icon').textContent = sortAsc ? '↑' : '↓';
      currentPage = 1;
      render();
    });
  });

  render();
}
</script>
{% endblock %}
```

- [ ] **Step 3: Verify visually**

Start the app: `python main.py`
Open `http://localhost:8000`. Verify:
1. Subscription table has Status and 費用 columns ✓
2. Search input filters rows as you type ✓
3. Status dropdown filters by status ✓
4. Clicking 到期日 header sorts asc/desc ✓
5. Clicking 費用 header sorts numerically ✓
6. Pagination prev/next work ✓
7. Clicking 刪除 opens a Bootstrap modal (not a browser confirm dialog) ✓

- [ ] **Step 4: Commit**

```bash
git add src/interfaces/web/templates/base.html \
        src/interfaces/web/templates/index.html
git commit -m "feat: search/filter/sort/pagination/delete-modal (A3, A4, E2, E3)"
```

---

## Task 3: D1 — Change Password

**Files:**
- Create: `src/application/use_cases/auth/change_password.py`
- Create: `tests/unit/auth/test_change_password.py`
- Modify: `src/interfaces/web/dependencies.py`
- Modify: `src/interfaces/web/routes/auth.py`
- Create: `src/interfaces/web/templates/account/change_password.html`
- Modify: `src/interfaces/web/templates/base.html`

---

- [ ] **Step 1: Write failing tests**

Create `tests/unit/auth/test_change_password.py`:

```python
import pytest
from unittest.mock import MagicMock
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.domain.entities.user import User
from src.infrastructure.auth.hash_utils import hash_password


@pytest.fixture
def repo():
    return MagicMock()


def _make_user(hashed_pw: str) -> User:
    return User(
        id=1,
        email="alice@gilliontec.com.tw",
        display_name="Alice",
        hashed_password=hashed_pw,
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
    )


def test_change_password_success(repo):
    pw = hash_password("OldPass1!")
    repo.get_by_id.return_value = _make_user(pw)
    repo.update.side_effect = lambda u: u
    ChangePasswordUseCase(repo).execute(
        user_id=1,
        current_password="OldPass1!",
        new_password="NewPass2@",
    )
    repo.update.assert_called_once()
    saved_user = repo.update.call_args[0][0]
    # new hash should NOT equal old hash
    assert saved_user.hashed_password != pw


def test_change_password_wrong_current(repo):
    pw = hash_password("OldPass1!")
    repo.get_by_id.return_value = _make_user(pw)
    with pytest.raises(ValueError, match="Current password"):
        ChangePasswordUseCase(repo).execute(
            user_id=1,
            current_password="WrongPass!",
            new_password="NewPass2@",
        )


def test_change_password_user_not_found(repo):
    repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="not found"):
        ChangePasswordUseCase(repo).execute(
            user_id=99,
            current_password="any",
            new_password="any2",
        )
```

- [ ] **Step 2: Run to confirm they fail**

```
python -m pytest tests/unit/auth/test_change_password.py -v
```
Expected: `ERROR ... ModuleNotFoundError: No module named 'src.application.use_cases.auth.change_password'`

- [ ] **Step 3: Create `src/application/use_cases/auth/change_password.py`**

```python
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.auth.hash_utils import hash_password, verify_password


class ChangePasswordUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(self, user_id: int, current_password: str, new_password: str) -> None:
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        self._repo.update(user)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
python -m pytest tests/unit/auth/test_change_password.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Add dependency to `src/interfaces/web/dependencies.py`**

At the end of the imports section, add:
```python
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
```

After the existing `get_list_users_uc` function, add:
```python
def get_change_password_uc(repo=Depends(get_user_repo)) -> ChangePasswordUseCase:
    return ChangePasswordUseCase(repo)
```

- [ ] **Step 6: Add routes to `src/interfaces/web/routes/auth.py`**

At the top, add to existing imports:
```python
from src.interfaces.web.dependencies import get_login_uc, get_change_password_uc, get_current_user
```

Append at the bottom of the file:
```python
@router.get("/account/password")
def change_password_form(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse("account/change_password.html", {
        "request": request,
        "current_user": current_user,
        "error": None,
        "success": False,
    })


@router.post("/account/password")
def change_password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    current_user=Depends(get_current_user),
    uc=Depends(get_change_password_uc),
):
    if new_password != new_password_confirm:
        return templates.TemplateResponse("account/change_password.html", {
            "request": request,
            "current_user": current_user,
            "error": "新密碼兩次輸入不一致。",
            "success": False,
        })
    try:
        uc.execute(
            user_id=current_user.id,
            current_password=current_password,
            new_password=new_password,
        )
    except ValueError as e:
        return templates.TemplateResponse("account/change_password.html", {
            "request": request,
            "current_user": current_user,
            "error": str(e),
            "success": False,
        })
    return templates.TemplateResponse("account/change_password.html", {
        "request": request,
        "current_user": current_user,
        "error": None,
        "success": True,
    })
```

- [ ] **Step 7: Create `src/interfaces/web/templates/account/change_password.html`**

First create the directory, then the file:

```html
{% extends "base.html" %}
{% block content %}
<div style="max-width:440px">
  <h4 class="mb-3">🔑 修改密碼</h4>

  {% if success %}
  <div class="alert alert-success">密碼已成功更新。</div>
  {% endif %}

  {% if error %}
  <div class="alert alert-danger">{{ error }}</div>
  {% endif %}

  <form method="POST" action="/account/password">
    <div class="mb-3">
      <label class="form-label">目前密碼</label>
      <input type="password" name="current_password" class="form-control" required autofocus>
    </div>
    <div class="mb-3">
      <label class="form-label">新密碼</label>
      <input type="password" name="new_password" class="form-control" required>
    </div>
    <div class="mb-4">
      <label class="form-label">確認新密碼</label>
      <input type="password" name="new_password_confirm" class="form-control" required>
    </div>
    <button type="submit" class="btn btn-primary">更新密碼</button>
    <a href="/" class="btn btn-secondary ms-2">取消</a>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 8: Add 修改密碼 link to navbar in `src/interfaces/web/templates/base.html`**

Find this block in the navbar:
```html
        <form method="POST" action="/logout" class="d-inline m-0">
          <button type="submit" class="btn btn-sm"
                  style="background:#e53935;color:#fff;border:none;">登出</button>
        </form>
```

Replace it with (adds 修改密碼 before 登出):
```html
        <a href="/account/password" class="btn btn-sm"
           style="background:#546e7a;color:#fff;border:none;">🔑 修改密碼</a>
        <form method="POST" action="/logout" class="d-inline m-0">
          <button type="submit" class="btn btn-sm"
                  style="background:#e53935;color:#fff;border:none;">登出</button>
        </form>
```

- [ ] **Step 9: Run full test suite**

```
python -m pytest tests/ -q
```
Expected: 33 passed.

- [ ] **Step 10: Commit**

```bash
git add src/application/use_cases/auth/change_password.py \
        src/interfaces/web/dependencies.py \
        src/interfaces/web/routes/auth.py \
        src/interfaces/web/templates/account/change_password.html \
        src/interfaces/web/templates/base.html \
        tests/unit/auth/test_change_password.py
git commit -m "feat: add change-password page (D1)"
```

---

## Task 4: D2 — Audit Log

**Files:**
- Create: `src/domain/entities/audit_entry.py`
- Create: `src/domain/repositories/audit_log_repository.py`
- Create: `src/infrastructure/database/sql_audit_log_repository.py`
- Modify: `src/interfaces/web/dependencies.py`
- Modify: `src/interfaces/web/routes/subscriptions.py`
- Modify: `src/interfaces/web/routes/admin.py`
- Create: `src/interfaces/web/templates/admin/audit_log.html`
- SQL: CREATE TABLE (manual)

---

- [ ] **Step 1: Create `src/domain/entities/audit_entry.py`**

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AuditEntry:
    user_id: int
    user_email: str
    action: str        # "create" | "update" | "delete"
    target_type: str   # "subscription"
    target_id: int
    target_name: str
    id: int | None = None
    created_at: datetime | None = None
```

- [ ] **Step 2: Create `src/domain/repositories/audit_log_repository.py`**

```python
from abc import ABC, abstractmethod
from src.domain.entities.audit_entry import AuditEntry


class AuditLogRepository(ABC):

    @abstractmethod
    def add(self, entry: AuditEntry) -> AuditEntry: ...

    @abstractmethod
    def get_recent(self, limit: int = 100) -> list[AuditEntry]: ...
```

- [ ] **Step 3: Create audit_log table in SSMS**

Connect to SQL Server and run:

```sql
USE subscription_tracker;
GO
CREATE TABLE audit_log (
    id          INT           IDENTITY(1,1) PRIMARY KEY,
    user_id     INT           NOT NULL,
    user_email  NVARCHAR(200) NOT NULL,
    action      NVARCHAR(20)  NOT NULL,
    target_type NVARCHAR(50)  NOT NULL,
    target_id   INT           NOT NULL,
    target_name NVARCHAR(200) NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT GETDATE()
);
GO
```
Expected: `Commands completed successfully.`

- [ ] **Step 4: Create `src/infrastructure/database/sql_audit_log_repository.py`**

```python
from sqlalchemy.orm import Session
from src.domain.entities.audit_entry import AuditEntry
from src.domain.repositories.audit_log_repository import AuditLogRepository
from src.infrastructure.database.models import AuditLogModel


class SqlAuditLogRepository(AuditLogRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, model: AuditLogModel) -> AuditEntry:
        return AuditEntry(
            id=model.id,
            user_id=model.user_id,
            user_email=model.user_email,
            action=model.action,
            target_type=model.target_type,
            target_id=model.target_id,
            target_name=model.target_name,
            created_at=model.created_at,
        )

    def add(self, entry: AuditEntry) -> AuditEntry:
        model = AuditLogModel(
            user_id=entry.user_id,
            user_email=entry.user_email,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            target_name=entry.target_name,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def get_recent(self, limit: int = 100) -> list[AuditEntry]:
        models = (
            self._session.query(AuditLogModel)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(m) for m in models]
```

- [ ] **Step 5: Add audit log dependency to `src/interfaces/web/dependencies.py`**

Add import near the top with the other infrastructure imports:
```python
from src.infrastructure.database.sql_audit_log_repository import SqlAuditLogRepository
```

Add this function after `get_user_repo`:
```python
def get_audit_log_repo(session: Session = Depends(get_db_session)) -> SqlAuditLogRepository:
    return SqlAuditLogRepository(session)
```

- [ ] **Step 6: Wire audit logging into `src/interfaces/web/routes/subscriptions.py`**

Add to imports:
```python
from src.interfaces.web.dependencies import (
    get_create_uc, get_delete_uc, get_list_uc, get_single_uc, get_update_uc,
    get_current_user, require_create, require_update, require_delete,
    get_audit_log_repo,
)
from src.domain.entities.audit_entry import AuditEntry
```

Update `create_submit` signature — add `audit_repo=Depends(get_audit_log_repo)` and call it:
```python
@router.post("/subscriptions/create")
def create_submit(
    request: Request,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    notification_emails: str = Form(...),
    notification_days: int = Form(...),
    status: str = Form("active"),
    cost: str | None = Form(None),
    currency: str = Form("TWD"),
    notes: str | None = Form(None),
    uc=Depends(get_create_uc),
    current_user=Depends(require_create),
    audit_repo=Depends(get_audit_log_repo),
):
    sub = uc.execute(
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
        notification_emails=notification_emails,
        notification_days=NotificationDays(notification_days),
        status=SubscriptionStatus(status),
        cost=Decimal(cost) if cost and cost.strip() else None,
        currency=currency,
        notes=notes or None,
    )
    audit_repo.add(AuditEntry(
        user_id=current_user.id,
        user_email=current_user.email,
        action="create",
        target_type="subscription",
        target_id=sub.id,
        target_name=sub.service_name,
    ))
    return RedirectResponse("/", status_code=303)
```

Update `edit_submit` similarly — add `audit_repo=Depends(get_audit_log_repo)` and log after update:
```python
@router.post("/subscriptions/{subscription_id}/edit")
def edit_submit(
    subscription_id: int,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    notification_emails: str = Form(...),
    notification_days: int = Form(...),
    status: str = Form("active"),
    cost: str | None = Form(None),
    currency: str = Form("TWD"),
    notes: str | None = Form(None),
    uc=Depends(get_update_uc),
    current_user=Depends(require_update),
    audit_repo=Depends(get_audit_log_repo),
):
    sub = uc.execute(
        subscription_id=subscription_id,
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
        notification_emails=notification_emails,
        notification_days=NotificationDays(notification_days),
        status=SubscriptionStatus(status),
        cost=Decimal(cost) if cost and cost.strip() else None,
        currency=currency,
        notes=notes or None,
    )
    audit_repo.add(AuditEntry(
        user_id=current_user.id,
        user_email=current_user.email,
        action="update",
        target_type="subscription",
        target_id=sub.id,
        target_name=sub.service_name,
    ))
    return RedirectResponse("/", status_code=303)
```

Update `delete` — add `single_uc=Depends(get_single_uc)` and `audit_repo=Depends(get_audit_log_repo)` to look up the name before deletion:
```python
@router.post("/subscriptions/{subscription_id}/delete")
def delete(
    subscription_id: int,
    uc=Depends(get_delete_uc),
    single_uc=Depends(get_single_uc),
    current_user=Depends(require_delete),
    audit_repo=Depends(get_audit_log_repo),
):
    sub = single_uc.execute(subscription_id)
    service_name = sub.service_name if sub else str(subscription_id)
    uc.execute(subscription_id)
    audit_repo.add(AuditEntry(
        user_id=current_user.id,
        user_email=current_user.email,
        action="delete",
        target_type="subscription",
        target_id=subscription_id,
        target_name=service_name,
    ))
    return RedirectResponse("/", status_code=303)
```

- [ ] **Step 7: Add audit log route to `src/interfaces/web/routes/admin.py`**

Add import at top:
```python
from src.interfaces.web.dependencies import (
    get_user_repo, get_register_uc, get_update_permissions_uc,
    get_list_users_uc, require_admin, get_audit_log_repo,
)
```

Append at the bottom of the file:
```python
@router.get("/audit-log")
def audit_log(
    request: Request,
    audit_repo=Depends(get_audit_log_repo),
    current_user=Depends(require_admin),
):
    entries = audit_repo.get_recent(limit=200)
    return templates.TemplateResponse("admin/audit_log.html", {
        "request": request,
        "entries": entries,
        "current_user": current_user,
    })
```

- [ ] **Step 8: Create `src/interfaces/web/templates/admin/audit_log.html`**

```html
{% extends "base.html" %}
{% block content %}
<h4 class="mb-3">🕵️ 操作紀錄（最近 200 筆）</h4>

{% if not entries %}
<p class="text-muted">尚無操作紀錄。</p>
{% else %}
<div class="table-responsive">
<table class="table table-bordered table-hover align-middle table-sm">
  <thead class="table-header">
    <tr>
      <th>時間</th>
      <th>操作者</th>
      <th>動作</th>
      <th>對象</th>
    </tr>
  </thead>
  <tbody>
    {% for e in entries %}
    {% if e.action == 'create' %}
      {% set action_badge = 'bg-success' %}
      {% set action_text  = '新增' %}
    {% elif e.action == 'update' %}
      {% set action_badge = 'bg-primary' %}
      {% set action_text  = '修改' %}
    {% else %}
      {% set action_badge = 'bg-danger' %}
      {% set action_text  = '刪除' %}
    {% endif %}
    <tr>
      <td><small>{{ e.created_at.strftime('%Y-%m-%d %H:%M:%S') if e.created_at else '—' }}</small></td>
      <td><small>{{ e.user_email }}</small></td>
      <td><span class="badge {{ action_badge }}">{{ action_text }}</span></td>
      <td>{{ e.target_name }} <small class="text-muted">(#{{ e.target_id }})</small></td>
    </tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 9: Add 操作紀錄 link to admin navbar in `src/interfaces/web/templates/base.html`**

Find:
```html
        {% if current_user.role == 'admin' %}
        <a href="/admin/users" class="btn btn-sm"
           style="background:#1976d2;color:#fff;border:none;">👥 使用者管理</a>
        {% endif %}
```

Replace with:
```html
        {% if current_user.role == 'admin' %}
        <a href="/admin/users" class="btn btn-sm"
           style="background:#1976d2;color:#fff;border:none;">👥 使用者管理</a>
        <a href="/admin/audit-log" class="btn btn-sm"
           style="background:#00695c;color:#fff;border:none;">🕵️ 操作紀錄</a>
        {% endif %}
```

- [ ] **Step 10: Run full test suite**

```
python -m pytest tests/ -q
```
Expected: 33 passed (no new tests — audit log repo requires DB; logic is trivial pass-through).

- [ ] **Step 11: Commit**

```bash
git add src/domain/entities/audit_entry.py \
        src/domain/repositories/audit_log_repository.py \
        src/infrastructure/database/sql_audit_log_repository.py \
        src/interfaces/web/dependencies.py \
        src/interfaces/web/routes/subscriptions.py \
        src/interfaces/web/routes/admin.py \
        src/interfaces/web/templates/admin/audit_log.html \
        src/interfaces/web/templates/base.html
git commit -m "feat: add audit log — records create/update/delete by whom (D2)"
```

---

## Self-Review

**Spec coverage:**
- ✅ A1 — `SubscriptionStatus` enum + status badge in index table; status select in create/edit forms
- ✅ A2 — `cost` (Decimal) + `currency` fields; cost column in index; cost/currency fields in create/edit
- ✅ A3 — Search by service name (client-side JS)
- ✅ A4 — Sortable columns: 服務名稱, 到期日, 狀態, 費用 (client-side JS)
- ✅ D1 — `/account/password` route + `ChangePasswordUseCase`; 3 unit tests
- ✅ D2 — `AuditEntry` entity + `audit_log` DB table + `SqlAuditLogRepository`; wired into create/update/delete routes; `/admin/audit-log` viewer
- ✅ E2 — Bootstrap modal replaces browser `confirm()` on delete button
- ✅ E3 — Client-side pagination with page-size selector

**Placeholder scan:** No TBD or TODO items. All code blocks are complete.

**Type consistency:**
- `SubscriptionStatus` defined in Task 1 entity; used as `sub.status.value` in templates and `SubscriptionStatus(status)` in routes — consistent throughout.
- `AuditEntry` fields (`user_id`, `user_email`, `action`, `target_type`, `target_id`, `target_name`) defined in entity and used identically in repository and route — consistent.
- `ChangePasswordUseCase.execute(user_id, current_password, new_password)` defined in Task 3 and called with same signature in route — consistent.
