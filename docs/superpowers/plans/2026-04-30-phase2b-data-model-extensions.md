# Phase 2B — Data Model Extensions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add six new fields to the Subscription entity — `payment_account` (付款帳戶), extended `billing_cycle` options (季付/半年付/兩年付), `auto_renew` flag (自動續約), `trial_end_date` (試用到期日), `next_billing_date` (下次計費日), and `icon_emoji` (圖示表情) — propagating each through DB → ORM → repository → use cases → routes → templates.

**Architecture:** Standard clean-architecture propagation: entity fields first → DB ALTER TABLE (manual SQL in SSMS) → ORM model → repository mapping → use case params → form routes → create/edit templates → list and dashboard display. Plan 2A must be implemented first (or in parallel) because Task 7 updates the card view introduced by Plan 2A. If Plan 2A is not yet done, skip the card-view section of Task 7.

**Tech Stack:** FastAPI, Jinja2, SQLAlchemy 2, SQL Server (pyodbc), Bootstrap 5.3

---

## File Map

| Action | File | What changes |
|--------|------|--------------|
| Modify | `src/domain/entities/subscription.py` | Add 5 fields: `payment_account`, `auto_renew`, `trial_end_date`, `next_billing_date`, `icon_emoji` |
| Modify | `src/infrastructure/database/models.py` | Add 5 columns to `SubscriptionModel` |
| Modify | `src/infrastructure/database/sql_subscription_repository.py` | Map new fields in `_to_entity`, `add`, `update` |
| Modify | `src/application/use_cases/create_subscription.py` | Add 5 new params |
| Modify | `src/application/use_cases/update_subscription.py` | Add 5 new params |
| Modify | `src/interfaces/web/routes/subscriptions.py` | Extend `BILLING_CYCLE_OPTIONS`; update `annual_cost()` in dashboard; add form params to create/edit submit; pass new options to forms |
| Modify | `src/interfaces/web/templates/create.html` | Add 5 new form fields |
| Modify | `src/interfaces/web/templates/edit.html` | Add 5 new form fields (pre-filled) |
| Modify | `src/interfaces/web/templates/index.html` | Show `icon_emoji` on service name; `auto_renew` badge; `trial_end_date` countdown; `next_billing_date` in billing column; `payment_account` column |
| Modify | `src/interfaces/web/templates/dashboard.html` | Add "試用即將到期" stat card; update renewal timeline billing cycle display |
| Modify | `src/interfaces/web/routes/subscriptions.py` | Add `trial_expiring_count` to dashboard context |
| Test | `tests/unit/test_subscription_entity.py` | New field tests |
| Test | `tests/unit/test_create_subscription.py` | New param tests |
| Test | `tests/unit/test_update_subscription.py` | New param tests |

---

## Task 1: Subscription Entity — New Fields + Tests

**Files:**
- Modify: `src/domain/entities/subscription.py`
- Test: `tests/unit/test_subscription_entity.py`

- [ ] **Step 1: Write the failing tests**

Open `tests/unit/test_subscription_entity.py` and add at the bottom:

```python
def test_subscription_has_phase2b_fields():
    sub = Subscription(
        service_name="Linear",
        login_account="team@co.com",
        expiry_date=date(2027, 1, 1),
        notification_emails="a@co.com",
        notification_days=NotificationDays.THIRTY,
        payment_account="公司美金卡末4碼1234",
        auto_renew=True,
        trial_end_date=date(2026, 6, 1),
        next_billing_date=date(2026, 5, 15),
        icon_emoji="💻",
    )
    assert sub.payment_account == "公司美金卡末4碼1234"
    assert sub.auto_renew is True
    assert sub.trial_end_date == date(2026, 6, 1)
    assert sub.next_billing_date == date(2026, 5, 15)
    assert sub.icon_emoji == "💻"


def test_subscription_phase2b_fields_default_values():
    sub = Subscription(
        service_name="Slack",
        login_account="it@co.com",
        expiry_date=date(2027, 6, 1),
        notification_emails="b@co.com",
        notification_days=NotificationDays.SEVEN,
    )
    assert sub.payment_account is None
    assert sub.auto_renew is False
    assert sub.trial_end_date is None
    assert sub.next_billing_date is None
    assert sub.icon_emoji is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/unit/test_subscription_entity.py::test_subscription_has_phase2b_fields -v
```

Expected: `FAILED` — `TypeError: __init__() got an unexpected keyword argument 'payment_account'`

- [ ] **Step 3: Add the five new fields to the entity**

In `src/domain/entities/subscription.py`, replace the `@dataclass` block with:

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
    billing_cycle: str | None = None
    payment_account: str | None = None    # N1 — 付款帳戶
    auto_renew: bool = False              # N5 — 自動續約
    trial_end_date: date | None = None   # N6 — 試用到期日
    next_billing_date: date | None = None # N7 — 下次計費日
    icon_emoji: str | None = None        # N8 — 服務圖示
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def should_notify_today(self, today: date) -> bool:
        trigger = self.expiry_date - timedelta(days=self.notification_days.value)
        return today == trigger
```

- [ ] **Step 4: Run all entity tests to confirm they pass**

```
python -m pytest tests/unit/test_subscription_entity.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```
git add src/domain/entities/subscription.py tests/unit/test_subscription_entity.py
git commit -m "feat: add payment_account/auto_renew/trial_end_date/next_billing_date/icon_emoji to Subscription entity"
```

---

## Task 2: Extended Billing Cycle Options

**Files:**
- Modify: `src/interfaces/web/routes/subscriptions.py`

- [ ] **Step 1: Replace `BILLING_CYCLE_OPTIONS`**

In `src/interfaces/web/routes/subscriptions.py`, replace:

```python
BILLING_CYCLE_OPTIONS = [
    ("monthly", "月付"),
    ("annual",  "年付"),
]
```

with:

```python
BILLING_CYCLE_OPTIONS = [
    ("monthly",     "月付"),
    ("quarterly",   "季付"),
    ("semi_annual", "半年付"),
    ("annual",      "年付"),
    ("biennial",    "兩年付"),
]
```

- [ ] **Step 2: Update `annual_cost()` inside the `dashboard()` route**

The `annual_cost()` helper currently only handles `"monthly"` and treats everything else as annual. Replace it with:

```python
def annual_cost(s):
    if s.cost is None:
        return 0.0
    multipliers = {
        "monthly":     12,
        "quarterly":   4,
        "semi_annual": 2,
        "annual":      1,
        "biennial":    0.5,
    }
    return float(s.cost) * multipliers.get(s.billing_cycle or "annual", 1)
```

- [ ] **Step 3: Run tests**

```
python -m pytest tests/ -q
```

Expected: All PASS.

- [ ] **Step 4: Commit**

```
git add src/interfaces/web/routes/subscriptions.py
git commit -m "feat: extend billing cycle options (季付/半年付/兩年付) and update annual_cost multipliers"
```

---

## Task 3: DB Schema + ORM Model

**Files:**
- Modify: `src/infrastructure/database/models.py`
- SQL: manual ALTER TABLE in SSMS

- [ ] **Step 1: Run this SQL in SSMS**

Connect to SQL Server, select the `subscription_tracker` database, and execute:

```sql
USE subscription_tracker;
GO
ALTER TABLE saas_subscriptions
  ADD payment_account   NVARCHAR(100) NULL,
      auto_renew        BIT           NOT NULL DEFAULT 0,
      trial_end_date    DATE          NULL,
      next_billing_date DATE          NULL,
      icon_emoji        NVARCHAR(10)  NULL;
GO
```

Expected: `Commands completed successfully.`

- [ ] **Step 2: Add the five new columns to `SubscriptionModel`**

In `src/infrastructure/database/models.py`, add after the `billing_cycle` column line:

```python
    billing_cycle       = Column(String(20),  nullable=True)
    payment_account     = Column(String(100), nullable=True)
    auto_renew          = Column(Boolean,     nullable=False, default=False)
    trial_end_date      = Column(Date,        nullable=True)
    next_billing_date   = Column(Date,        nullable=True)
    icon_emoji          = Column(String(10),  nullable=True)
    created_at          = Column(DateTime,    nullable=False, default=datetime.now)
    updated_at          = Column(DateTime,    nullable=True,  onupdate=datetime.now)
```

- [ ] **Step 3: Run tests (no DB needed for unit tests)**

```
python -m pytest tests/ -q
```

Expected: All PASS.

- [ ] **Step 4: Commit**

```
git add src/infrastructure/database/models.py
git commit -m "feat: add 5 new columns to SubscriptionModel ORM"
```

---

## Task 4: Repository Mapping

**Files:**
- Modify: `src/infrastructure/database/sql_subscription_repository.py`

- [ ] **Step 1: Update `_to_entity` — add the five new field mappings**

In `_to_entity`, add after `billing_cycle=model.billing_cycle,`:

```python
        billing_cycle=model.billing_cycle,
        payment_account=model.payment_account,
        auto_renew=bool(model.auto_renew),
        trial_end_date=model.trial_end_date,
        next_billing_date=model.next_billing_date,
        icon_emoji=model.icon_emoji,
```

- [ ] **Step 2: Update `add` — add the five new field mappings**

In the `SubscriptionModel(...)` constructor inside `add`, add after `billing_cycle=subscription.billing_cycle,`:

```python
            billing_cycle=subscription.billing_cycle,
            payment_account=subscription.payment_account,
            auto_renew=subscription.auto_renew,
            trial_end_date=subscription.trial_end_date,
            next_billing_date=subscription.next_billing_date,
            icon_emoji=subscription.icon_emoji,
```

- [ ] **Step 3: Update `update` — add the five new assignment lines**

In `update`, add after `model.billing_cycle = subscription.billing_cycle`:

```python
        model.billing_cycle      = subscription.billing_cycle
        model.payment_account    = subscription.payment_account
        model.auto_renew         = subscription.auto_renew
        model.trial_end_date     = subscription.trial_end_date
        model.next_billing_date  = subscription.next_billing_date
        model.icon_emoji         = subscription.icon_emoji
        model.updated_at         = datetime.now()
```

- [ ] **Step 4: Run tests**

```
python -m pytest tests/ -q
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```
git add src/infrastructure/database/sql_subscription_repository.py
git commit -m "feat: map payment_account/auto_renew/trial_end_date/next_billing_date/icon_emoji in subscription repository"
```

---

## Task 5: Use Cases + Tests

**Files:**
- Modify: `src/application/use_cases/create_subscription.py`
- Modify: `src/application/use_cases/update_subscription.py`
- Test: `tests/unit/test_create_subscription.py`
- Test: `tests/unit/test_update_subscription.py`

- [ ] **Step 1: Write failing test for CreateSubscriptionUseCase**

Open `tests/unit/test_create_subscription.py` and add at the bottom:

```python
def test_create_subscription_with_phase2b_fields(mock_repo):
    mock_repo.add.return_value = Subscription(
        id=20,
        service_name="Linear",
        login_account="team@co.com",
        expiry_date=date(2027, 1, 1),
        notification_emails="a@co.com",
        notification_days=NotificationDays.THIRTY,
        payment_account="公司美金卡末4碼1234",
        auto_renew=True,
        trial_end_date=date(2026, 6, 1),
        next_billing_date=date(2026, 5, 15),
        icon_emoji="💻",
        billing_cycle="quarterly",
    )
    uc = CreateSubscriptionUseCase(mock_repo)
    uc.execute(
        service_name="Linear",
        login_account="team@co.com",
        expiry_date=date(2027, 1, 1),
        notification_emails="a@co.com",
        notification_days=NotificationDays.THIRTY,
        payment_account="公司美金卡末4碼1234",
        auto_renew=True,
        trial_end_date=date(2026, 6, 1),
        next_billing_date=date(2026, 5, 15),
        icon_emoji="💻",
        billing_cycle="quarterly",
    )
    saved = mock_repo.add.call_args[0][0]
    assert saved.payment_account == "公司美金卡末4碼1234"
    assert saved.auto_renew is True
    assert saved.trial_end_date == date(2026, 6, 1)
    assert saved.next_billing_date == date(2026, 5, 15)
    assert saved.icon_emoji == "💻"
    assert saved.billing_cycle == "quarterly"
```

- [ ] **Step 2: Run test to confirm it fails**

```
python -m pytest tests/unit/test_create_subscription.py::test_create_subscription_with_phase2b_fields -v
```

Expected: `FAILED` — `TypeError: execute() got an unexpected keyword argument 'payment_account'`

- [ ] **Step 3: Replace `src/application/use_cases/create_subscription.py`**

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
        payment_account: str | None = None,
        auto_renew: bool = False,
        trial_end_date: date | None = None,
        next_billing_date: date | None = None,
        icon_emoji: str | None = None,
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
            payment_account=payment_account,
            auto_renew=auto_renew,
            trial_end_date=trial_end_date,
            next_billing_date=next_billing_date,
            icon_emoji=icon_emoji,
        )
        return self._repo.add(entity)
```

- [ ] **Step 4: Write failing test for UpdateSubscriptionUseCase**

Open `tests/unit/test_update_subscription.py` and add at the bottom:

```python
def test_update_subscription_with_phase2b_fields(mock_repo):
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
        payment_account="台幣帳戶5678",
        auto_renew=False,
        trial_end_date=date(2026, 5, 31),
        next_billing_date=date(2026, 5, 20),
        icon_emoji="📝",
        billing_cycle="semi_annual",
    )
    saved = mock_repo.update.call_args[0][0]
    assert saved.payment_account == "台幣帳戶5678"
    assert saved.auto_renew is False
    assert saved.trial_end_date == date(2026, 5, 31)
    assert saved.next_billing_date == date(2026, 5, 20)
    assert saved.icon_emoji == "📝"
    assert saved.billing_cycle == "semi_annual"
```

- [ ] **Step 5: Replace `src/application/use_cases/update_subscription.py`**

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
        payment_account: str | None = None,
        auto_renew: bool = False,
        trial_end_date: date | None = None,
        next_billing_date: date | None = None,
        icon_emoji: str | None = None,
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
        entity.payment_account     = payment_account
        entity.auto_renew          = auto_renew
        entity.trial_end_date      = trial_end_date
        entity.next_billing_date   = next_billing_date
        entity.icon_emoji          = icon_emoji
        return self._repo.update(entity)
```

- [ ] **Step 6: Run all tests**

```
python -m pytest tests/ -q
```

Expected: All PASS (2 new tests added).

- [ ] **Step 7: Commit**

```
git add src/application/use_cases/create_subscription.py \
        src/application/use_cases/update_subscription.py \
        tests/unit/test_create_subscription.py \
        tests/unit/test_update_subscription.py
git commit -m "feat: add 5 new params to create/update use cases"
```

---

## Task 6: Routes + Form Templates

**Files:**
- Modify: `src/interfaces/web/routes/subscriptions.py`
- Modify: `src/interfaces/web/templates/create.html`
- Modify: `src/interfaces/web/templates/edit.html`

- [ ] **Step 1: Add new Form params to `create_submit`**

In `create_submit`, add these five parameters after `billing_cycle: str | None = Form(None),`:

```python
    billing_cycle: str | None = Form(None),
    payment_account: str | None = Form(None),
    auto_renew: bool = Form(False),
    trial_end_date: str | None = Form(None),
    next_billing_date: str | None = Form(None),
    icon_emoji: str | None = Form(None),
```

In the `uc.execute(...)` call inside `create_submit`, add after `billing_cycle=billing_cycle or None,`:

```python
        billing_cycle=billing_cycle or None,
        payment_account=payment_account or None,
        auto_renew=bool(auto_renew),
        trial_end_date=datetime.strptime(trial_end_date, "%Y-%m-%d").date() if trial_end_date else None,
        next_billing_date=datetime.strptime(next_billing_date, "%Y-%m-%d").date() if next_billing_date else None,
        icon_emoji=icon_emoji or None,
```

- [ ] **Step 2: Add new Form params to `edit_submit`**

Apply the identical changes to `edit_submit` (same five new parameters and same five new arguments to `uc.execute(...)`).

- [ ] **Step 3: Pass new options to `create_form` and `edit_form` template contexts**

In `create_form`, the context already passes `billing_cycle_options` which is now extended — no change needed. Verify `BILLING_CYCLE_OPTIONS` is referenced correctly (it is, from Task 2).

- [ ] **Step 4: Add five new fields to `create.html`**

Read `src/interfaces/web/templates/create.html`. Before the `<button type="submit">` line, insert:

```html
  <div class="mb-3">
    <label class="form-label">服務圖示（選填）</label>
    <input type="text" name="icon_emoji" class="form-control" maxlength="4"
           placeholder="貼上 Emoji，例如 💻 🔒 📊">
    <div class="form-text">輸入任一 Emoji 作為訂閱的視覺識別</div>
  </div>
  <div class="mb-3">
    <label class="form-label">付款帳戶（選填）</label>
    <input type="text" name="payment_account" class="form-control"
           placeholder="例如：公司美金卡末4碼1234">
  </div>
  <div class="mb-3">
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="auto_renew"
             id="autoRenewCreate" value="true">
      <label class="form-check-label" for="autoRenewCreate">
        自動續約（到期前會自動扣款）
      </label>
    </div>
  </div>
  <div class="row g-2 mb-3">
    <div class="col-sm-6">
      <label class="form-label">試用到期日（選填）</label>
      <input type="date" name="trial_end_date" class="form-control">
      <div class="form-text">免費試用結束日，到期前會顯示警示</div>
    </div>
    <div class="col-sm-6">
      <label class="form-label">下次計費日（選填）</label>
      <input type="date" name="next_billing_date" class="form-control">
      <div class="form-text">月付訂閱的下次扣款日</div>
    </div>
  </div>
```

- [ ] **Step 5: Add five new fields to `edit.html` (with pre-filled values)**

Read `src/interfaces/web/templates/edit.html`. Before the `<button type="submit">` line, insert:

```html
  <div class="mb-3">
    <label class="form-label">服務圖示（選填）</label>
    <input type="text" name="icon_emoji" class="form-control" maxlength="4"
           value="{{ sub.icon_emoji or '' }}"
           placeholder="貼上 Emoji，例如 💻 🔒 📊">
    <div class="form-text">輸入任一 Emoji 作為訂閱的視覺識別</div>
  </div>
  <div class="mb-3">
    <label class="form-label">付款帳戶（選填）</label>
    <input type="text" name="payment_account" class="form-control"
           value="{{ sub.payment_account or '' }}"
           placeholder="例如：公司美金卡末4碼1234">
  </div>
  <div class="mb-3">
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="auto_renew"
             id="autoRenewEdit" value="true"
             {% if sub.auto_renew %}checked{% endif %}>
      <label class="form-check-label" for="autoRenewEdit">
        自動續約（到期前會自動扣款）
      </label>
    </div>
  </div>
  <div class="row g-2 mb-3">
    <div class="col-sm-6">
      <label class="form-label">試用到期日（選填）</label>
      <input type="date" name="trial_end_date" class="form-control"
             value="{{ sub.trial_end_date or '' }}">
      <div class="form-text">免費試用結束日，到期前會顯示警示</div>
    </div>
    <div class="col-sm-6">
      <label class="form-label">下次計費日（選填）</label>
      <input type="date" name="next_billing_date" class="form-control"
             value="{{ sub.next_billing_date or '' }}">
      <div class="form-text">月付訂閱的下次扣款日</div>
    </div>
  </div>
```

- [ ] **Step 6: Run all tests**

```
python -m pytest tests/ -q
```

Expected: All PASS.

- [ ] **Step 7: Smoke test the forms**

```
python main.py
```

Open http://localhost:8000/subscriptions/create. Verify:
1. "服務圖示" emoji input field appears
2. "付款帳戶" text input appears
3. "自動續約" checkbox appears
4. "試用到期日" and "下次計費日" date pickers appear
5. "計費週期" dropdown now includes 季付, 半年付, 兩年付

Open any existing subscription's edit page — verify all five fields are pre-filled from saved data.

- [ ] **Step 8: Commit**

```
git add src/interfaces/web/routes/subscriptions.py \
        src/interfaces/web/templates/create.html \
        src/interfaces/web/templates/edit.html
git commit -m "feat: add new form fields to create/edit routes and templates"
```

---

## Task 7: Template Display — List Page + Dashboard

**Files:**
- Modify: `src/interfaces/web/templates/index.html`
- Modify: `src/interfaces/web/routes/subscriptions.py`
- Modify: `src/interfaces/web/templates/dashboard.html`

### Part A: Update index.html

- [ ] **Step 1: Show `icon_emoji` as prefix in the service name cell (table view)**

In the table row `<td>{{ sub.service_name }}</td>`, replace with:

```html
      <td>
        {% if sub.icon_emoji %}
          <span class="me-1">{{ sub.icon_emoji }}</span>
        {% endif %}
        {{ sub.service_name }}
        {% if sub.auto_renew %}
          <span class="badge bg-info text-dark ms-1" title="自動續約">↻</span>
        {% endif %}
      </td>
```

- [ ] **Step 2: Show `trial_end_date` countdown in the expiry date cell**

Replace `<td>{{ sub.expiry_date }}</td>` with:

```html
      <td>
        {{ sub.expiry_date }}
        {% if sub.trial_end_date %}
        {% set trial_days = (sub.trial_end_date - today).days %}
        <br><small>
          {% if trial_days >= 0 %}
            <span class="text-warning">🧪 試用剩 {{ trial_days }} 天</span>
          {% else %}
            <span class="text-muted">🧪 試用已結束</span>
          {% endif %}
        </small>
        {% endif %}
      </td>
```

- [ ] **Step 3: Update the billing cycle cell to also show `next_billing_date`**

Replace the billing cycle `<td>` block:

```html
      <td>
        {% if sub.billing_cycle == "monthly" %}月付
        {% elif sub.billing_cycle == "quarterly" %}季付
        {% elif sub.billing_cycle == "semi_annual" %}半年付
        {% elif sub.billing_cycle == "annual" %}年付
        {% elif sub.billing_cycle == "biennial" %}兩年付
        {% else %}<span class="text-muted">—</span>{% endif %}
        {% if sub.next_billing_date %}
          <br><small class="text-muted">下次 {{ sub.next_billing_date }}</small>
        {% endif %}
      </td>
```

- [ ] **Step 4: Add `payment_account` column to table header**

In `<thead>`, add after the `<th>備註</th>` line:

```html
      <th>付款帳戶</th>
```

- [ ] **Step 5: Add `payment_account` cell to table rows**

In the table row, add after `<td><small class="text-muted">{{ sub.notes or '' }}</small></td>`:

```html
      <td><small class="text-muted">{{ sub.payment_account or '—' }}</small></td>
```

- [ ] **Step 6: Update card view to use `icon_emoji` when available (requires Plan 2A done)**

In the card grid, replace the category-emoji line:

```html
            <span class="fs-4 lh-1">{{ CAT_EMOJI.get(sub.category, '📦') }}</span>
```

with:

```html
            <span class="fs-4 lh-1">{{ sub.icon_emoji or CAT_EMOJI.get(sub.category, '📦') }}</span>
```

Also add auto_renew indicator below the status badge inside the card body:

```html
          {% if sub.auto_renew %}
          <div class="text-info small mt-1">↻ 自動續約</div>
          {% endif %}
          {% if sub.trial_end_date %}
          {% set trial_days = (sub.trial_end_date - today).days %}
          <div class="small mt-1">
            {% if trial_days >= 0 %}
              <span class="text-warning">🧪 試用剩 {{ trial_days }} 天</span>
            {% else %}
              <span class="text-muted">🧪 試用已結束</span>
            {% endif %}
          </div>
          {% endif %}
```

### Part B: Update Dashboard

- [ ] **Step 7: Add `trial_expiring_count` to the `dashboard()` route**

In `src/interfaces/web/routes/subscriptions.py`, inside `dashboard()`, add after the `no_owner` line:

```python
    no_owner = [s for s in active_subs if not s.owner_name]
    trial_expiring = [
        s for s in active_subs
        if s.trial_end_date and 0 <= (s.trial_end_date - today).days <= 14
    ]
```

Add `"trial_expiring_count": len(trial_expiring)` to the `templates.TemplateResponse` context dict.

- [ ] **Step 8: Add "試用即將到期" stat card to `dashboard.html`**

In `dashboard.html`, replace the four-column stat grid with a five-column layout. Add a fifth card after the "尚未指定負責人" card:

```html
  <div class="col-sm-6 col-md-3">
    <div class="card h-100 border-0 shadow-sm {% if trial_expiring_count > 0 %}border-warning{% endif %}">
      <div class="card-body">
        <div class="text-muted small mb-1">試用 14 天內到期</div>
        <div class="fs-3 fw-bold {% if trial_expiring_count > 0 %}text-warning{% endif %}">
          {{ trial_expiring_count }}
        </div>
        <div class="text-muted small">記得取消或升級</div>
      </div>
    </div>
  </div>
```

Also update the renewal timeline billing cycle display to include the new cycles:

In the `{% for sub in upcoming_90 %}` loop, replace the billing cycle `<td>`:

```html
          <td>
            {% if sub.billing_cycle == "monthly" %}月付
            {% elif sub.billing_cycle == "quarterly" %}季付
            {% elif sub.billing_cycle == "semi_annual" %}半年付
            {% elif sub.billing_cycle == "annual" %}年付
            {% elif sub.billing_cycle == "biennial" %}兩年付
            {% else %}<span class="text-muted">—</span>{% endif %}
          </td>
```

- [ ] **Step 9: Change stat grid from 4 to 5 columns**

In `dashboard.html`, update the stat grid row — change `col-md-3` to `col-md` on all five stat cards so they auto-distribute across one row. (Bootstrap `col-md` with 5 cards auto-sizes to ~20% each.)

- [ ] **Step 10: Run all tests**

```
python -m pytest tests/ -q
```

Expected: All PASS.

- [ ] **Step 11: Full smoke test**

```
python main.py
```

Verify:
1. Subscription list table shows `icon_emoji` prefix + auto-renew `↻` badge on service name
2. Expiry date cell shows "🧪 試用剩 N 天" for subscriptions with `trial_end_date` set
3. Billing cycle cell shows correct Chinese label for 季付/半年付/兩年付 and "下次 YYYY-MM-DD" on next line if set
4. "付款帳戶" column appears at the end
5. Card view shows `icon_emoji` (or category fallback emoji), auto_renew indicator, trial days remaining
6. Dashboard shows 5 stat cards with "試用 14 天內到期" as the fifth card
7. Edit an existing subscription → all five new fields appear pre-filled

- [ ] **Step 12: Commit**

```
git add src/interfaces/web/routes/subscriptions.py \
        src/interfaces/web/templates/index.html \
        src/interfaces/web/templates/dashboard.html
git commit -m "feat: display icon_emoji/auto_renew/trial_end_date/next_billing_date/payment_account in list and dashboard"
```

---

## Self-Review

**Spec coverage:**
- ✅ N1 — `payment_account` field end-to-end: entity → DB → repo → use case → form → list column
- ✅ N2 — Extended `BILLING_CYCLE_OPTIONS`: 季付/半年付/兩年付; `annual_cost()` uses multiplier map; all templates show correct labels
- ✅ N5 — `auto_renew` boolean: entity default `False` → DB `BIT DEFAULT 0` → checkbox in forms → `↻` badge in list + card
- ✅ N6 — `trial_end_date`: entity `date|None` → DB `DATE NULL` → date picker in forms → countdown in list cell + card → dashboard "試用 14 天內到期" stat card
- ✅ N7 — `next_billing_date`: entity `date|None` → DB `DATE NULL` → date picker in forms → small text below billing cycle in list
- ✅ N8 — `icon_emoji`: entity `str|None` → DB `NVARCHAR(10) NULL` → emoji text input in forms → prefix in list service name cell → override for card view icon

**Placeholder scan:** No TBD or TODO items. All code blocks are complete.

**Type consistency:**
- `payment_account`, `auto_renew`, `trial_end_date`, `next_billing_date`, `icon_emoji` defined in Task 1 entity; used with identical names in Task 3 (ORM), Task 4 (repo), Task 5 (use cases), Task 6 (routes/forms), Task 7 (templates) — consistent throughout
- `auto_renew` is `bool` in entity; `BIT` in SQL Server; `Boolean` in SQLAlchemy; `bool(model.auto_renew)` cast in `_to_entity`; `Form(False)` in route; `value="true"` checkbox — consistent conversion path
- New billing cycle values (`"quarterly"`, `"semi_annual"`, `"biennial"`) defined in `BILLING_CYCLE_OPTIONS` (Task 2) and displayed in all three templates (Task 7) with consistent Chinese labels (季付/半年付/兩年付)
- `trial_expiring_count` defined in `dashboard()` route (Task 7 Part B Step 7) and consumed in `dashboard.html` (Task 7 Part B Step 8) — consistent
