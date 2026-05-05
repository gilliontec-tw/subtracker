# Phase 1 — Dashboard & Core Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Dashboard首頁（4 stat cards + renewal timeline）、到期倒數標記、負責人、分類、部門、計費週期六項功能。

**Architecture:** New fields are added to the `Subscription` domain entity and propagated through the full stack: ORM model → repository → use cases → routes → templates. The Dashboard is a new route `/dashboard` (redirected from `/`) that aggregates data from the existing subscription list without a new use case. No migration tooling exists — schema changes are raw `ALTER TABLE` SQL for SQL Server.

**Tech Stack:** FastAPI + Jinja2 (server-rendered), SQLAlchemy 2 ORM, SQL Server Express (pyodbc), Bootstrap 5.3, vanilla JS.

---

## File Map

| Action | File | What changes |
|--------|------|--------------|
| Modify | `src/domain/entities/subscription.py` | Add `owner_name`, `category`, `department`, `billing_cycle` fields |
| Modify | `src/infrastructure/database/models.py` | Add 4 new columns to `SubscriptionModel` |
| Modify | `src/infrastructure/database/sql_subscription_repository.py` | Map new fields in `_to_entity`, `add`, `update` |
| Modify | `src/application/use_cases/create_subscription.py` | Accept 4 new params |
| Modify | `src/application/use_cases/update_subscription.py` | Accept 4 new params |
| Modify | `src/interfaces/web/routes/subscriptions.py` | New option lists, new Form params, dashboard route |
| Modify | `src/interfaces/web/templates/base.html` | Add Dashboard nav link |
| Modify | `src/interfaces/web/templates/index.html` | New columns (days-badge, owner, category, dept, billing_cycle), new filter dropdowns |
| Modify | `src/interfaces/web/templates/create.html` | 4 new form fields |
| Modify | `src/interfaces/web/templates/edit.html` | 4 new form fields (pre-filled) |
| Create | `src/interfaces/web/templates/dashboard.html` | Stat cards + renewal timeline |
| Modify | `tests/unit/test_subscription_entity.py` | Test new fields |
| Modify | `tests/unit/test_create_subscription.py` | Test new params |
| Modify | `tests/unit/test_update_subscription.py` | Test new params |

---

## Task 1: Add New Fields to Subscription Entity

**Files:**
- Modify: `src/domain/entities/subscription.py`
- Test: `tests/unit/test_subscription_entity.py`

- [ ] **Step 1: Write the failing test**

Open `tests/unit/test_subscription_entity.py`. Add at the bottom:

```python
def test_subscription_has_new_phase1_fields():
    sub = Subscription(
        service_name="Slack",
        login_account="admin@co.com",
        expiry_date=date(2026, 6, 1),
        notification_emails="a@co.com",
        notification_days=NotificationDays.THIRTY,
        owner_name="陳小明",
        category="生產力工具",
        department="全公司",
        billing_cycle="annual",
    )
    assert sub.owner_name == "陳小明"
    assert sub.category == "生產力工具"
    assert sub.department == "全公司"
    assert sub.billing_cycle == "annual"


def test_subscription_new_fields_default_to_none():
    sub = Subscription(
        service_name="GitHub",
        login_account="dev@co.com",
        expiry_date=date(2026, 8, 1),
        notification_emails="b@co.com",
        notification_days=NotificationDays.FOURTEEN,
    )
    assert sub.owner_name is None
    assert sub.category is None
    assert sub.department is None
    assert sub.billing_cycle is None
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest tests/unit/test_subscription_entity.py::test_subscription_has_new_phase1_fields -v
```

Expected: `FAILED` — `TypeError: __init__() got an unexpected keyword argument 'owner_name'`

- [ ] **Step 3: Add new fields to entity**

In `src/domain/entities/subscription.py`, add four fields after the `notes` field:

```python
@dataclass
class Subscription:
    service_name: str
    login_account: str
    expiry_date: date
    notification_emails: str
    notification_days: NotificationDays
    id: int | None = None
    is_active: bool = True
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    cost: Decimal | None = None
    currency: str = "TWD"
    notes: str | None = None
    owner_name: str | None = None
    category: str | None = None
    department: str | None = None
    billing_cycle: str | None = None  # "monthly" | "annual" | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest tests/unit/test_subscription_entity.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```
git add src/domain/entities/subscription.py tests/unit/test_subscription_entity.py
git commit -m "feat: add owner_name, category, department, billing_cycle to Subscription entity"
```

---

## Task 2: DB Schema — ALTER TABLE + ORM Model

**Files:**
- Modify: `src/infrastructure/database/models.py`

> **No migration tooling exists.** Run the SQL manually in SSMS before starting the app.

- [ ] **Step 1: Run this SQL in SSMS (SQL Server Express)**

```sql
ALTER TABLE saas_subscriptions
  ADD owner_name   NVARCHAR(100)  NULL,
      category     NVARCHAR(100)  NULL,
      department   NVARCHAR(100)  NULL,
      billing_cycle NVARCHAR(20)  NULL;
```

- [ ] **Step 2: Add columns to ORM model**

In `src/infrastructure/database/models.py`, add after the `notes` column:

```python
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
    currency            = Column(String(10), nullable=False, default="TWD")
    notes               = Column(String(1000), nullable=True)
    owner_name          = Column(String(100), nullable=True)
    category            = Column(String(100), nullable=True)
    department          = Column(String(100), nullable=True)
    billing_cycle       = Column(String(20), nullable=True)
    created_at          = Column(DateTime, nullable=False, default=datetime.now)
    updated_at          = Column(DateTime, nullable=True, onupdate=datetime.now)
```

- [ ] **Step 3: Commit**

```
git add src/infrastructure/database/models.py
git commit -m "feat: add owner_name/category/department/billing_cycle columns to SubscriptionModel"
```

---

## Task 3: Update Repository

**Files:**
- Modify: `src/infrastructure/database/sql_subscription_repository.py`

- [ ] **Step 1: Update `_to_entity` to map new fields**

Replace the `_to_entity` method:

```python
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
        owner_name=model.owner_name,
        category=model.category,
        department=model.department,
        billing_cycle=model.billing_cycle,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
```

- [ ] **Step 2: Update `add` to persist new fields**

Replace the `add` method:

```python
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
        owner_name=subscription.owner_name,
        category=subscription.category,
        department=subscription.department,
        billing_cycle=subscription.billing_cycle,
    )
    self._session.add(model)
    self._session.commit()
    self._session.refresh(model)
    return self._to_entity(model)
```

- [ ] **Step 3: Update `update` to persist new fields**

In the `update` method, add four lines after `model.notes = subscription.notes`:

```python
model.notes         = subscription.notes
model.owner_name    = subscription.owner_name
model.category      = subscription.category
model.department    = subscription.department
model.billing_cycle = subscription.billing_cycle
model.updated_at    = datetime.now()
```

- [ ] **Step 4: Run existing tests to confirm nothing broke**

```
python -m pytest tests/ -q
```

Expected: All PASS (36 tests).

- [ ] **Step 5: Commit**

```
git add src/infrastructure/database/sql_subscription_repository.py
git commit -m "feat: propagate new fields through subscription repository"
```

---

## Task 4: Update Use Cases

**Files:**
- Modify: `src/application/use_cases/create_subscription.py`
- Modify: `src/application/use_cases/update_subscription.py`
- Test: `tests/unit/test_create_subscription.py`
- Test: `tests/unit/test_update_subscription.py`

- [ ] **Step 1: Write failing test for CreateSubscriptionUseCase**

Open `tests/unit/test_create_subscription.py`. Add at the bottom:

```python
def test_create_subscription_with_new_fields(mock_repo):
    mock_repo.add.return_value = Subscription(
        id=10,
        service_name="Figma",
        login_account="design@co.com",
        expiry_date=date(2027, 1, 1),
        notification_emails="a@co.com",
        notification_days=NotificationDays.THIRTY,
        owner_name="李設計",
        category="設計工具",
        department="設計",
        billing_cycle="annual",
    )
    uc = CreateSubscriptionUseCase(mock_repo)
    result = uc.execute(
        service_name="Figma",
        login_account="design@co.com",
        expiry_date=date(2027, 1, 1),
        notification_emails="a@co.com",
        notification_days=NotificationDays.THIRTY,
        owner_name="李設計",
        category="設計工具",
        department="設計",
        billing_cycle="annual",
    )
    saved = mock_repo.add.call_args[0][0]
    assert saved.owner_name == "李設計"
    assert saved.category == "設計工具"
    assert saved.department == "設計"
    assert saved.billing_cycle == "annual"
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest tests/unit/test_create_subscription.py::test_create_subscription_with_new_fields -v
```

Expected: `FAILED` — `TypeError: execute() got an unexpected keyword argument 'owner_name'`

- [ ] **Step 3: Update CreateSubscriptionUseCase**

Replace `src/application/use_cases/create_subscription.py`:

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
        owner_name: str | None = None,
        category: str | None = None,
        department: str | None = None,
        billing_cycle: str | None = None,
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
            owner_name=owner_name,
            category=category,
            department=department,
            billing_cycle=billing_cycle,
        )
        return self._repo.add(entity)
```

- [ ] **Step 4: Write failing test for UpdateSubscriptionUseCase**

Open `tests/unit/test_update_subscription.py`. Add at the bottom:

```python
def test_update_subscription_with_new_fields(mock_repo):
    existing = Subscription(
        id=5,
        service_name="Notion",
        login_account="team@co.com",
        expiry_date=date(2026, 9, 1),
        notification_emails="c@co.com",
        notification_days=NotificationDays.THIRTY,
        status=SubscriptionStatus.ACTIVE,
    )
    mock_repo.get_by_id.return_value = existing
    mock_repo.update.return_value = existing
    uc = UpdateSubscriptionUseCase(mock_repo)
    uc.execute(
        subscription_id=5,
        service_name="Notion",
        login_account="team@co.com",
        expiry_date=date(2026, 9, 1),
        notification_emails="c@co.com",
        notification_days=NotificationDays.THIRTY,
        status=SubscriptionStatus.ACTIVE,
        owner_name="林行政",
        category="生產力工具",
        department="全公司",
        billing_cycle="annual",
    )
    saved = mock_repo.update.call_args[0][0]
    assert saved.owner_name == "林行政"
    assert saved.category == "生產力工具"
    assert saved.department == "全公司"
    assert saved.billing_cycle == "annual"
```

- [ ] **Step 5: Update UpdateSubscriptionUseCase**

Replace `src/application/use_cases/update_subscription.py`:

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
        status: SubscriptionStatus,
        cost: Decimal | None = None,
        currency: str = "TWD",
        notes: str | None = None,
        owner_name: str | None = None,
        category: str | None = None,
        department: str | None = None,
        billing_cycle: str | None = None,
    ):
        entity = self._repo.get_by_id(subscription_id)
        if entity is None:
            raise ValueError(f"Subscription {subscription_id} not found")
        entity.service_name        = service_name
        entity.login_account       = login_account
        entity.expiry_date         = expiry_date
        entity.notification_emails = notification_emails
        entity.notification_days   = notification_days
        entity.status              = status
        entity.cost                = cost
        entity.currency            = currency
        entity.notes               = notes
        entity.owner_name          = owner_name
        entity.category            = category
        entity.department          = department
        entity.billing_cycle       = billing_cycle
        return self._repo.update(entity)
```

- [ ] **Step 6: Run all tests**

```
python -m pytest tests/ -q
```

Expected: All PASS (38 tests).

- [ ] **Step 7: Commit**

```
git add src/application/use_cases/create_subscription.py src/application/use_cases/update_subscription.py tests/unit/test_create_subscription.py tests/unit/test_update_subscription.py
git commit -m "feat: add owner_name/category/department/billing_cycle to create and update use cases"
```

---

## Task 5: Update Web Routes

**Files:**
- Modify: `src/interfaces/web/routes/subscriptions.py`

- [ ] **Step 1: Add new option constants and update imports**

At the top of `src/interfaces/web/routes/subscriptions.py`, after `CURRENCY_OPTIONS`, add:

```python
CATEGORY_OPTIONS = [
    "生產力工具", "開發工具", "資安合規", "設計工具",
    "行銷廣告", "雲端基礎", "財務會計", "HR人資", "其他",
]

DEPARTMENT_OPTIONS = [
    "全公司", "工程", "設計", "行銷", "業務", "財務", "HR", "IT", "其他",
]

BILLING_CYCLE_OPTIONS = [
    ("monthly", "月付"),
    ("annual",  "年付"),
]
```

- [ ] **Step 2: Update `create_form` to pass new options**

Replace the `create_form` route:

```python
@router.get("/subscriptions/create")
def create_form(request: Request, current_user=Depends(require_create)):
    return templates.TemplateResponse("create.html", {
        "request": request,
        "notification_options": NOTIFICATION_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "currency_options": CURRENCY_OPTIONS,
        "category_options": CATEGORY_OPTIONS,
        "department_options": DEPARTMENT_OPTIONS,
        "billing_cycle_options": BILLING_CYCLE_OPTIONS,
        "current_user": current_user,
    })
```

- [ ] **Step 3: Update `create_submit` to accept and pass new Form params**

Replace the `create_submit` route:

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
    owner_name: str | None = Form(None),
    category: str | None = Form(None),
    department: str | None = Form(None),
    billing_cycle: str | None = Form(None),
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
        owner_name=owner_name or None,
        category=category or None,
        department=department or None,
        billing_cycle=billing_cycle or None,
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

- [ ] **Step 4: Update `edit_form` to pass new options + prefill values**

Replace the `edit_form` route:

```python
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
        "category_options": CATEGORY_OPTIONS,
        "department_options": DEPARTMENT_OPTIONS,
        "billing_cycle_options": BILLING_CYCLE_OPTIONS,
        "current_user": current_user,
    })
```

- [ ] **Step 5: Update `edit_submit` to accept and pass new Form params**

Replace the `edit_submit` route:

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
    owner_name: str | None = Form(None),
    category: str | None = Form(None),
    department: str | None = Form(None),
    billing_cycle: str | None = Form(None),
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
        owner_name=owner_name or None,
        category=category or None,
        department=department or None,
        billing_cycle=billing_cycle or None,
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

- [ ] **Step 6: Add the dashboard route**

Add this route at the top of the `router` declarations (before `GET /`), and also add the necessary import at the top:

At the top imports, `from datetime import date, datetime, timedelta` (add `timedelta`).

Then add the dashboard route before `@router.get("/")`:

```python
@router.get("/dashboard")
def dashboard(request: Request, uc=Depends(get_list_uc), current_user=Depends(get_current_user)):
    subscriptions = uc.execute()
    today = date.today()

    active_subs = [s for s in subscriptions if s.status.value in ("active", "renewed")]
    total_annual_cost = sum(
        (s.cost * 12 if s.billing_cycle == "monthly" else s.cost)
        for s in active_subs if s.cost is not None
    )
    upcoming_30 = [s for s in active_subs if 0 <= (s.expiry_date - today).days <= 30]
    upcoming_90 = sorted(
        [s for s in active_subs if 0 <= (s.expiry_date - today).days <= 90],
        key=lambda s: s.expiry_date,
    )
    no_owner = [s for s in active_subs if not s.owner_name]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "today": today,
        "total_subscriptions": len(subscriptions),
        "active_count": len(active_subs),
        "total_annual_cost": total_annual_cost,
        "upcoming_30_count": len(upcoming_30),
        "no_owner_count": len(no_owner),
        "upcoming_90": upcoming_90,
    })
```

- [ ] **Step 7: Redirect `/` to `/dashboard`**

Replace the existing `@router.get("/")` route:

```python
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
```

Leave `/` as the subscription list and `/dashboard` as the new dashboard. The navbar will link to `/dashboard` as the home button.

- [ ] **Step 8: Run all tests**

```
python -m pytest tests/ -q
```

Expected: All PASS (38 tests).

- [ ] **Step 9: Commit**

```
git add src/interfaces/web/routes/subscriptions.py
git commit -m "feat: add dashboard route and new field options to subscription routes"
```

---

## Task 6: Update create.html and edit.html

**Files:**
- Modify: `src/interfaces/web/templates/create.html`
- Modify: `src/interfaces/web/templates/edit.html`

- [ ] **Step 1: Add four new fields to create.html**

In `src/interfaces/web/templates/create.html`, add before the `<button type="submit">` line:

```html
  <div class="mb-3">
    <label class="form-label">負責人（選填）</label>
    <input type="text" name="owner_name" class="form-control"
           placeholder="例如：陳小明">
  </div>
  <div class="row g-2 mb-3">
    <div class="col-sm-6">
      <label class="form-label">分類（選填）</label>
      <select name="category" class="form-select">
        <option value="">— 請選擇 —</option>
        {% for opt in category_options %}
        <option value="{{ opt }}">{{ opt }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-sm-6">
      <label class="form-label">部門（選填）</label>
      <select name="department" class="form-select">
        <option value="">— 請選擇 —</option>
        {% for opt in department_options %}
        <option value="{{ opt }}">{{ opt }}</option>
        {% endfor %}
      </select>
    </div>
  </div>
  <div class="mb-3">
    <label class="form-label">計費週期（選填）</label>
    <select name="billing_cycle" class="form-select">
      <option value="">— 請選擇 —</option>
      {% for value, label in billing_cycle_options %}
      <option value="{{ value }}">{{ label }}</option>
      {% endfor %}
    </select>
  </div>
```

- [ ] **Step 2: Read edit.html and add matching fields with pre-filled values**

Open `src/interfaces/web/templates/edit.html`. Add the same four fields before the submit button, using `sub` to pre-fill values:

```html
  <div class="mb-3">
    <label class="form-label">負責人（選填）</label>
    <input type="text" name="owner_name" class="form-control"
           value="{{ sub.owner_name or '' }}"
           placeholder="例如：陳小明">
  </div>
  <div class="row g-2 mb-3">
    <div class="col-sm-6">
      <label class="form-label">分類（選填）</label>
      <select name="category" class="form-select">
        <option value="">— 請選擇 —</option>
        {% for opt in category_options %}
        <option value="{{ opt }}"
                {% if sub.category == opt %}selected{% endif %}>{{ opt }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-sm-6">
      <label class="form-label">部門（選填）</label>
      <select name="department" class="form-select">
        <option value="">— 請選擇 —</option>
        {% for opt in department_options %}
        <option value="{{ opt }}"
                {% if sub.department == opt %}selected{% endif %}>{{ opt }}</option>
        {% endfor %}
      </select>
    </div>
  </div>
  <div class="mb-3">
    <label class="form-label">計費週期（選填）</label>
    <select name="billing_cycle" class="form-select">
      <option value="">— 請選擇 —</option>
      {% for value, label in billing_cycle_options %}
      <option value="{{ value }}"
              {% if sub.billing_cycle == value %}selected{% endif %}>{{ label }}</option>
      {% endfor %}
    </select>
  </div>
```

- [ ] **Step 3: Commit**

```
git add src/interfaces/web/templates/create.html src/interfaces/web/templates/edit.html
git commit -m "feat: add owner/category/department/billing_cycle fields to create and edit forms"
```

---

## Task 7: Update index.html (Subscription List)

**Files:**
- Modify: `src/interfaces/web/templates/index.html`

- [ ] **Step 1: Add category/department filter dropdowns to the toolbar**

Replace the toolbar section (the `<div class="row g-2 mb-3 ...">` block) with:

```html
<div class="row g-2 mb-3 align-items-end">
  <div class="col-sm-3">
    <input type="text" id="searchInput" class="form-control form-control-sm"
           placeholder="搜尋服務名稱…">
  </div>
  <div class="col-sm-2">
    <select id="statusFilter" class="form-select form-select-sm">
      <option value="">全部狀態</option>
      <option value="active">使用中</option>
      <option value="renewed">已續約</option>
      <option value="cancelled">已取消</option>
      <option value="suspended">暫停</option>
    </select>
  </div>
  <div class="col-sm-2">
    <select id="categoryFilter" class="form-select form-select-sm">
      <option value="">全部分類</option>
      {% set cats = subscriptions | map(attribute='category') | select | unique | sort %}
      {% for cat in cats %}
      <option value="{{ cat }}">{{ cat }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-sm-2">
    <select id="deptFilter" class="form-select form-select-sm">
      <option value="">全部部門</option>
      {% set depts = subscriptions | map(attribute='department') | select | unique | sort %}
      {% for dept in depts %}
      <option value="{{ dept }}">{{ dept }}</option>
      {% endfor %}
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
```

- [ ] **Step 2: Update the table header**

Replace the `<thead>` block:

```html
  <thead class="table-header">
    <tr>
      <th class="sortable" data-col="service">服務名稱 <span class="sort-icon">↕</span></th>
      <th>登入帳號</th>
      <th class="sortable" data-col="expiry">到期日 <span class="sort-icon">↕</span></th>
      <th class="sortable" data-col="days">倒數天數 <span class="sort-icon">↕</span></th>
      <th class="sortable" data-col="status">狀態 <span class="sort-icon">↕</span></th>
      <th class="sortable" data-col="cost">費用 <span class="sort-icon">↕</span></th>
      <th>計費週期</th>
      <th class="sortable" data-col="owner">負責人 <span class="sort-icon">↕</span></th>
      <th class="sortable" data-col="category">分類 <span class="sort-icon">↕</span></th>
      <th class="sortable" data-col="dept">部門 <span class="sort-icon">↕</span></th>
      <th>備註</th>
      <th>操作</th>
    </tr>
  </thead>
```

- [ ] **Step 3: Update the table rows with new data attributes and columns**

Replace the entire `{% for sub in subscriptions %}` block (the `<tr>` and its content):

```html
    {% for sub in subscriptions %}
    {% set days_left = (sub.expiry_date - today).days %}
    {% set badge_cls, badge_txt = STATUS.get(sub.status.value, ('bg-secondary', sub.status.value)) %}
    {% if days_left < 0 %}
      {% set days_color = "secondary" %}
    {% elif days_left <= 14 %}
      {% set days_color = "danger" %}
    {% elif days_left <= 30 %}
      {% set days_color = "warning" %}
    {% else %}
      {% set days_color = "success" %}
    {% endif %}
    <tr data-service="{{ sub.service_name | lower }}"
        data-expiry="{{ sub.expiry_date }}"
        data-days="{{ days_left }}"
        data-status="{{ sub.status.value }}"
        data-cost="{{ sub.cost | float if sub.cost else 0 }}"
        data-owner="{{ (sub.owner_name or '') | lower }}"
        data-category="{{ sub.category or '' }}"
        data-dept="{{ sub.department or '' }}">
      <td>{{ sub.service_name }}</td>
      <td>{{ sub.login_account }}</td>
      <td>{{ sub.expiry_date }}</td>
      <td>
        {% if days_left >= 0 %}
          <span class="badge bg-{{ days_color }}">{{ days_left }} 天</span>
        {% else %}
          <span class="badge bg-secondary">已過期</span>
        {% endif %}
      </td>
      <td><span class="badge {{ badge_cls }}">{{ badge_txt }}</span></td>
      <td>
        {% if sub.cost %}
          {{ "%.0f" % sub.cost }} {{ sub.currency }}
        {% else %}
          <span class="text-muted">—</span>
        {% endif %}
      </td>
      <td>
        {% if sub.billing_cycle == "monthly" %}月付
        {% elif sub.billing_cycle == "annual" %}年付
        {% else %}<span class="text-muted">—</span>{% endif %}
      </td>
      <td>{{ sub.owner_name or '<span class="text-muted">未指定</span>' | safe }}</td>
      <td>
        {% if sub.category %}
          <span class="badge badge-blue">{{ sub.category }}</span>
        {% else %}<span class="text-muted">—</span>{% endif %}
      </td>
      <td>
        {% if sub.department %}
          <small>{{ sub.department }}</small>
        {% else %}<span class="text-muted">—</span>{% endif %}
      </td>
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
```

- [ ] **Step 4: Update the JS filter function to include category and department**

Replace the `filtered()` function in the `<script>` block:

```javascript
function filtered() {
  const q    = document.getElementById('searchInput').value.toLowerCase();
  const st   = document.getElementById('statusFilter').value;
  const cat  = document.getElementById('categoryFilter').value;
  const dept = document.getElementById('deptFilter').value;
  return allRows.filter(r =>
    r.dataset.service.includes(q) &&
    (!st   || r.dataset.status   === st) &&
    (!cat  || r.dataset.category === cat) &&
    (!dept || r.dataset.dept     === dept)
  );
}
```

Also add event listeners for the two new filters (after the existing three listeners):

```javascript
document.getElementById('categoryFilter')
  .addEventListener('change', () => { currentPage = 1; render(); });
document.getElementById('deptFilter')
  .addEventListener('change', () => { currentPage = 1; render(); });
```

- [ ] **Step 5: Commit**

```
git add src/interfaces/web/templates/index.html
git commit -m "feat: add days-countdown badge, owner/category/dept columns and filters to subscription list"
```

---

## Task 8: Create Dashboard Template

**Files:**
- Create: `src/interfaces/web/templates/dashboard.html`

- [ ] **Step 1: Create the dashboard template**

Create `src/interfaces/web/templates/dashboard.html`:

```html
{% extends "base.html" %}
{% block content %}

{# ── Stat Cards ──────────────────────────────────────────────────── #}
<div class="row g-3 mb-4">
  <div class="col-sm-6 col-md-3">
    <div class="card h-100 border-0 shadow-sm">
      <div class="card-body">
        <div class="text-muted small mb-1">年度總支出</div>
        <div class="fs-3 fw-bold text-success">
          {{ "{:,.0f}".format(total_annual_cost) }} TWD
        </div>
        <div class="text-muted small">啟用中訂閱合計</div>
      </div>
    </div>
  </div>
  <div class="col-sm-6 col-md-3">
    <div class="card h-100 border-0 shadow-sm">
      <div class="card-body">
        <div class="text-muted small mb-1">訂閱總數</div>
        <div class="fs-3 fw-bold">{{ total_subscriptions }}</div>
        <div class="text-muted small">其中 {{ active_count }} 個啟用中</div>
      </div>
    </div>
  </div>
  <div class="col-sm-6 col-md-3">
    <div class="card h-100 border-0 shadow-sm {% if upcoming_30_count > 0 %}border-warning{% endif %}">
      <div class="card-body">
        <div class="text-muted small mb-1">30 天內到期</div>
        <div class="fs-3 fw-bold {% if upcoming_30_count > 0 %}text-warning{% endif %}">
          {{ upcoming_30_count }}
        </div>
        <div class="text-muted small">需確認是否續約</div>
      </div>
    </div>
  </div>
  <div class="col-sm-6 col-md-3">
    <div class="card h-100 border-0 shadow-sm {% if no_owner_count > 0 %}border-danger{% endif %}">
      <div class="card-body">
        <div class="text-muted small mb-1">尚未指定負責人</div>
        <div class="fs-3 fw-bold {% if no_owner_count > 0 %}text-danger{% endif %}">
          {{ no_owner_count }}
        </div>
        <div class="text-muted small">請盡速指定 Owner</div>
      </div>
    </div>
  </div>
</div>

{# ── Renewal Timeline ─────────────────────────────────────────────── #}
<div class="card border-0 shadow-sm">
  <div class="card-header bg-white border-bottom">
    <h6 class="mb-0 fw-semibold">📅 即將到期（90 天內）</h6>
  </div>
  <div class="card-body p-0">
    {% if upcoming_90 %}
    <table class="table table-hover mb-0 align-middle">
      <thead class="table-light">
        <tr>
          <th>服務名稱</th>
          <th>到期日</th>
          <th>倒數天數</th>
          <th>費用</th>
          <th>計費週期</th>
          <th>負責人</th>
          <th>分類</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {% for sub in upcoming_90 %}
        {% set days_left = (sub.expiry_date - today).days %}
        <tr>
          <td><strong>{{ sub.service_name }}</strong></td>
          <td>{{ sub.expiry_date }}</td>
          <td>
            {% if days_left <= 14 %}
              <span class="badge bg-danger">{{ days_left }} 天</span>
            {% elif days_left <= 30 %}
              <span class="badge bg-warning text-dark">{{ days_left }} 天</span>
            {% else %}
              <span class="badge bg-success">{{ days_left }} 天</span>
            {% endif %}
          </td>
          <td>
            {% if sub.cost %}{{ "%.0f" % sub.cost }} {{ sub.currency }}
            {% else %}<span class="text-muted">—</span>{% endif %}
          </td>
          <td>
            {% if sub.billing_cycle == "monthly" %}月付
            {% elif sub.billing_cycle == "annual" %}年付
            {% else %}<span class="text-muted">—</span>{% endif %}
          </td>
          <td>{{ sub.owner_name or '<span class="text-muted">未指定</span>' | safe }}</td>
          <td>
            {% if sub.category %}
              <span class="badge badge-blue">{{ sub.category }}</span>
            {% else %}<span class="text-muted">—</span>{% endif %}
          </td>
          <td>
            <a href="/subscriptions/{{ sub.id }}/edit" class="btn btn-sm btn-outline-primary">編輯</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="p-4 text-center text-muted">
      <p class="mb-0">🎉 90 天內沒有即將到期的訂閱</p>
    </div>
    {% endif %}
  </div>
</div>

{% endblock %}
```

- [ ] **Step 2: Commit**

```
git add src/interfaces/web/templates/dashboard.html
git commit -m "feat: create dashboard template with stat cards and renewal timeline"
```

---

## Task 9: Update Navbar

**Files:**
- Modify: `src/interfaces/web/templates/base.html`

- [ ] **Step 1: Update the navbar brand link and add Dashboard link**

In `src/interfaces/web/templates/base.html`, replace:

```html
    <a class="navbar-brand" href="/">📋 SaaS 訂閱追蹤</a>
```

with:

```html
    <a class="navbar-brand" href="/dashboard">📋 SaaS 訂閱追蹤</a>
```

Also add a Dashboard link in the nav. After the opening `<div class="d-flex align-items-center gap-3">`, add:

```html
      {% if current_user is defined and current_user %}
        <a href="/dashboard" class="btn btn-sm"
           style="background:#0d47a1;color:#fff;border:none;">🏠 Dashboard</a>
        <a href="/" class="btn btn-sm"
           style="background:#1565c0;color:#fff;border:none;">📦 訂閱清單</a>
```

(The existing `<span>` for display_name stays where it was — only add the two `<a>` links before it.)

- [ ] **Step 2: Run the app and smoke test**

```
python main.py
```

Open http://localhost:8000/dashboard — verify 4 stat cards appear.
Open http://localhost:8000/ — verify the subscription list now has倒數天數, 負責人, 分類, 部門, 計費週期 columns.
Open http://localhost:8000/subscriptions/create — verify 4 new fields appear.

- [ ] **Step 3: Run all tests**

```
python -m pytest tests/ -q
```

Expected: All PASS (38 tests).

- [ ] **Step 4: Commit**

```
git add src/interfaces/web/templates/base.html
git commit -m "feat: add Dashboard and 訂閱清單 nav links to navbar"
```

---

## Self-Review Checklist

- [x] **B1 Dashboard**: Covered in Task 5 (route) + Task 8 (template) — 4 stat cards + renewal timeline ✓
- [x] **B2 倒數天數標記**: Covered in Task 7 — `days_left` badge with red/amber/green ✓
- [x] **B3 負責人欄位**: Covered in Tasks 1–7 end-to-end ✓
- [x] **B4 分類標籤**: Covered in Tasks 1–7 end-to-end ✓
- [x] **B5 部門標籤**: Covered in Tasks 1–7 end-to-end ✓
- [x] **B6 計費週期**: Covered in Tasks 1–7 end-to-end; Dashboard uses it for cost annualization ✓
- [x] No TBD or placeholders found
- [x] Type consistency: `owner_name/category/department/billing_cycle` used consistently across all tasks
- [x] DB migration SQL included in Task 2 with exact SQL Server syntax
