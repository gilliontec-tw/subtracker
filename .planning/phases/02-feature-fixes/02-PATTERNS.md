# Phase 2: Feature Fixes - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 11 (new/modified)
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/domain/entities/subscription.py` | model/entity | CRUD | `src/domain/entities/user.py` | role-match (same layer, same dataclass pattern) |
| `src/infrastructure/database/models.py` | model/ORM | CRUD | existing `SubscriptionModel` in same file | exact (add column, same pattern as `auto_renew`) |
| `src/infrastructure/database/sql_subscription_repository.py` | repository | CRUD | same file — `_to_entity()`, `add()`, `update()` | exact (extend existing mapping) |
| `src/application/use_cases/update_subscription.py` | use-case | request-response | same file — verify existing signature | exact (signature already accepts all four fields) |
| `src/application/use_cases/check_and_notify.py` | use-case | event-driven | same file — `due_subs` filter at line 16 | exact (add flag to filter expression) |
| `src/interfaces/web/routes/subscriptions.py` | route/controller | request-response | same file — `bulk_renew` handler lines 395-433 | exact (pass missing fields in same call) |
| `src/interfaces/web/routes/notifications.py` | route/controller | request-response | same file — `notif_settings_save` lines 39-81 | exact (add validation before use-case call) |
| `src/interfaces/web/routes/admin.py` | route/controller | request-response | same file — `resend_invite` lines 87-118 | exact (new endpoint reuses token-gen + email pattern) |
| `src/interfaces/web/templates/admin/users.html` | template | request-response | same file — `invited` banner lines 19-23 | exact (duplicate banner for `email_failed`) |
| `src/interfaces/web/templates/admin/user_edit.html` | template | request-response | same file — form actions block lines 43-47 | exact (add button alongside existing buttons) |
| `src/interfaces/web/templates/notifications/settings.html` | template | request-response | same file — `error` block lines 31-36 (already exists) | exact (wire existing `error` variable; template already renders it) |

---

## Pattern Assignments

### `src/domain/entities/subscription.py` (entity, CRUD)

**Analog:** `src/domain/entities/user.py` + existing `Subscription` dataclass

**Existing field declaration pattern** (`subscription.py` lines 30-43):
```python
# Optional boolean field with default — copy this pattern
auto_renew: bool = False
trial_end_date: date | None = None
next_billing_date: date | None = None
```

**Add after `next_billing_date`:**
```python
notifications_enabled: bool = True
```

No other changes needed — `should_notify_today()` remains unchanged; the flag is checked in the use case layer, not the entity.

---

### `src/infrastructure/database/models.py` (ORM model, CRUD)

**Analog:** existing `SubscriptionModel` — same file

**Boolean column pattern** (`models.py` lines 30-31):
```python
auto_renew          = Column(Boolean,     nullable=False, default=False)
trial_end_date      = Column(Date,        nullable=True)
```

**Add after `next_billing_date` column (line 32):**
```python
notifications_enabled = Column(Boolean, nullable=False, default=True)
```

**DB migration SQL** (no Alembic — manual script):
```sql
ALTER TABLE saas_subscriptions
  ADD notifications_enabled BIT NOT NULL DEFAULT 1;

-- Backfill: disable for subscriptions with no emails
UPDATE saas_subscriptions
SET notifications_enabled = 0
WHERE notification_emails IS NULL OR LTRIM(RTRIM(notification_emails)) = '';
```

---

### `src/infrastructure/database/sql_subscription_repository.py` (repository, CRUD)

**Analog:** existing methods in same file

**`_to_entity()` mapping pattern** (lines 13-36 — add one line):
```python
def _to_entity(self, model: SubscriptionModel) -> Subscription:
    return Subscription(
        # ... existing fields ...
        next_billing_date=model.next_billing_date,
        notifications_enabled=bool(model.notifications_enabled),  # ADD
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
```

**`add()` pattern** (lines 38-61 — add one line in `SubscriptionModel(...)` constructor):
```python
model = SubscriptionModel(
    # ... existing fields ...
    next_billing_date=subscription.next_billing_date,
    notifications_enabled=subscription.notifications_enabled,  # ADD
)
```

**`update()` pattern** (lines 76-100 — add one assignment before `updated_at`):
```python
model.next_billing_date   = subscription.next_billing_date
model.notifications_enabled = subscription.notifications_enabled  # ADD
model.updated_at          = datetime.now(timezone.utc)
```

---

### `src/application/use_cases/update_subscription.py` (use-case, request-response)

**Analog:** same file

**Current `execute()` signature** (lines 11-31) — already accepts all four bulk-renew fields:
```python
def execute(
    self,
    subscription_id: int,
    # ...
    payment_account: str | None = None,
    auto_renew: bool = False,
    trial_end_date: date | None = None,
    next_billing_date: date | None = None,
):
```

**Action required:** Add `notifications_enabled: bool = True` parameter and assignment. Pattern matches existing optional parameters:
```python
# In signature:
notifications_enabled: bool = True,
# In body (after next_billing_date assignment, line 51):
entity.notifications_enabled = notifications_enabled
```

**No callers currently pass `notifications_enabled` — the default of `True` is safe for all existing call sites.**

---

### `src/application/use_cases/check_and_notify.py` (use-case, event-driven)

**Analog:** same file — filter expression at line 16

**Existing filter pattern** (line 16):
```python
due_subs = [s for s in subscriptions if s.should_notify_today(today)]
```

**Change to** (add `notifications_enabled` guard):
```python
due_subs = [
    s for s in subscriptions
    if s.notifications_enabled and s.should_notify_today(today)
]
```

This is the only change needed. The email-sending loop below is unchanged.

---

### `src/interfaces/web/routes/subscriptions.py` (route/controller, request-response)

**Analog:** `bulk_renew` handler in same file (lines 395-433)

**Current broken call** (lines 409-424 — missing four fields):
```python
uc.execute(
    subscription_id=sub_id,
    service_name=sub.service_name,
    login_account=sub.login_account,
    expiry_date=new_expiry,
    notification_emails=sub.notification_emails,
    notification_days=sub.notification_days,
    status=sub.status,
    cost=sub.cost,
    currency=sub.currency,
    notes=sub.notes,
    owner_name=sub.owner_name,
    category=sub.category,
    department=sub.department,
    billing_cycle=sub.billing_cycle,
    # MISSING: payment_account, auto_renew, trial_end_date, next_billing_date
)
```

**Fixed call — add four lines:**
```python
uc.execute(
    subscription_id=sub_id,
    service_name=sub.service_name,
    login_account=sub.login_account,
    expiry_date=new_expiry,
    notification_emails=sub.notification_emails,
    notification_days=sub.notification_days,
    status=sub.status,
    cost=sub.cost,
    currency=sub.currency,
    notes=sub.notes,
    owner_name=sub.owner_name,
    category=sub.category,
    department=sub.department,
    billing_cycle=sub.billing_cycle,
    payment_account=sub.payment_account,        # ADD
    auto_renew=sub.auto_renew,                  # ADD
    trial_end_date=sub.trial_end_date,          # ADD
    next_billing_date=sub.next_billing_date,    # ADD
)
```

No new imports needed. `sub` is already fetched via `single_uc.execute(sub_id)`.

---

### `src/interfaces/web/routes/notifications.py` (route/controller, request-response)

**Analog:** same file — `notif_settings_save` handler (lines 39-81)

**Current logic** (lines 55-79): reads `enabled` from form checkbox, sets emails to `""` when disabled, then calls `uc.execute()` unconditionally.

**Required changes — two separate fixes:**

**Fix 1: Route-layer validation** — add before the `for` loop (after `ids` is built):
```python
# Validate: if any enabled subscription has empty email, re-render with error
errors = []
for sid in ids:
    enabled = f"notify_{sid}" in form
    if enabled:
        emails = form.get(f"emails_{sid}", "").strip()
        if not emails:
            sub = single_uc.execute(sid)
            name = sub.service_name if sub else str(sid)
            errors.append(f"「{name}」已啟用通知但收件人 Email 為空")
if errors:
    # Re-render form with error (matches existing route-layer validation pattern)
    subscriptions = list_uc.execute()
    ...
    return templates.TemplateResponse("notifications/settings.html", {
        "request": request,
        "current_user": current_user,
        "subscriptions": active,
        "today": today,
        "timedelta": timedelta,
        "notification_options": NOTIFICATION_OPTIONS,
        "saved": False,
        "error": errors[0],  # show first error
    })
```

**Fix 2: Preserve emails when disabling** — change the `emails` assignment (line 56):
```python
# Current (clears emails on disable):
emails = form.get(f"emails_{sid}", "").strip() if enabled else ""

# Fixed (preserve emails when disabling; pass notifications_enabled flag):
emails_from_form = form.get(f"emails_{sid}", "").strip()
emails = emails_from_form if enabled else sub.notification_emails  # preserve

# Also pass notifications_enabled to use case:
uc.execute(
    ...
    notification_emails=emails,
    notifications_enabled=enabled,   # ADD
    ...
)
```

**Import addition needed** — `get_list_uc` for re-render on error (already imported as `get_list_uc` in this file based on line 8). Also need to add `get_list_uc` to the POST handler's `Depends()` if validation re-render is needed.

**Re-render pattern reference:** `notif_settings` GET handler (lines 14-36) — copy its template context for the re-render.

---

### `src/interfaces/web/routes/admin.py` (route/controller, request-response)

**Analog:** `resend_invite` handler in same file (lines 87-118)

**`resend_invite` pattern to copy for `reset-password`** (lines 87-118):
```python
@router.post("/users/{user_id}/resend-invite")
def resend_invite(
    request: Request,
    user_id: int,
    current_user=Depends(require_admin),
    repo=Depends(get_user_repo),
):
    import secrets
    from datetime import datetime, timedelta, timezone
    user = repo.get_by_id(user_id)
    if user and user.invite_token:
        user.invite_token = secrets.token_urlsafe(32)
        user.invite_expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
        repo.update(user)
        try:
            ...
            SmtpEmailSender().send(...)
        except Exception:
            log.exception("Failed to resend invite email to user_id=%s", user_id)
    return RedirectResponse("/admin/users?invited=1", status_code=303)
```

**New `reset-password` endpoint — differences from `resend_invite`:**
1. Route: `POST /admin/users/{user_id}/reset-password`
2. Guard: `if user` (not `if user and user.invite_token`) — reset works for all non-admin users
3. Subject line: `"[SubTrack] 系統管理員已重設您的密碼，請重新設定"`
4. Body text: indicate this is a password reset, not first invite
5. Success redirect: `/admin/users?password_reset=1`
6. Email failure redirect: `/admin/users/{user_id}/edit?email_failed=1`

**NOTIF-02 fix — `create_user_submit` email failure** (line 82-84):
```python
# Current:
    except Exception:
        log.exception("Failed to send invite email to %s", email)
return RedirectResponse("/admin/users?invited=1", status_code=303)

# Fixed (redirect with email_failed param, keep the success redirect separate):
    except Exception:
        log.exception("Failed to send invite email to %s", email)
        return RedirectResponse("/admin/users?email_failed=1", status_code=303)
return RedirectResponse("/admin/users?invited=1", status_code=303)
```

**`resend_invite` email failure** (line 116-118):
```python
# Current:
        except Exception:
            log.exception("Failed to resend invite email to user_id=%s", user_id)
    return RedirectResponse("/admin/users?invited=1", status_code=303)

# Fixed:
        except Exception:
            log.exception("Failed to resend invite email to user_id=%s", user_id)
            return RedirectResponse(f"/admin/users/{user_id}/edit?email_failed=1", status_code=303)
    return RedirectResponse("/admin/users?invited=1", status_code=303)
```

---

### `src/interfaces/web/templates/admin/users.html` (template, request-response)

**Analog:** same file — existing `invited` banner (lines 19-23)

**Existing success banner pattern:**
```html
{% if request.query_params.get('invited') %}
<div class="alert alert-success mb-4" style="background:var(--success-bg);color:var(--success-text);border-radius:10px;padding:12px 16px;font-size:13px;margin-bottom:16px;">
  帳號已建立，邀請信已寄出。
</div>
{% endif %}
```

**Add immediately after that block — email_failed warning banner:**
```html
{% if request.query_params.get('email_failed') %}
<div class="alert alert-danger mb-4" style="border-radius:10px;padding:12px 16px;font-size:13px;margin-bottom:16px;">
  帳號已建立，但邀請信寄送失敗，請確認 SMTP 設定後手動重發邀請。
</div>
{% endif %}
{% if request.query_params.get('password_reset') %}
<div class="alert alert-success mb-4" style="background:var(--success-bg);color:var(--success-text);border-radius:10px;padding:12px 16px;font-size:13px;margin-bottom:16px;">
  密碼重設邀請已寄出。
</div>
{% endif %}
```

CSS classes `alert-danger` and `alert-success` are already used throughout the template set (see `notifications/settings.html` lines 24-36).

---

### `src/interfaces/web/templates/admin/user_edit.html` (template, request-response)

**Analog:** same file — form actions block (lines 43-47)

**Existing actions pattern:**
```html
<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px;">
  <a href="/admin/users" class="btn btn-outline">取消</a>
  <button type="submit" class="btn btn-primary">儲存</button>
</div>
```

**Add "重置密碼" button as a separate form (cannot share the edit form's POST action):**
```html
<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px;">
  <a href="/admin/users" class="btn btn-outline">取消</a>
  {% if request.query_params.get('email_failed') %}
  <span style="font-size:12px;color:var(--danger-text);align-self:center;">邀請信寄送失敗，請確認 SMTP 設定</span>
  {% endif %}
  <form method="POST" action="/admin/users/{{ user.id }}/reset-password" style="margin:0;">
    <button type="submit" class="btn btn-outline btn-sm">重置密碼</button>
  </form>
  <button type="submit" class="btn btn-primary">儲存</button>
</div>
```

The "重置密碼" button is a separate `<form>` with `POST` to the new endpoint, placed alongside the existing save button. This is consistent with the inline-form pattern used in `users.html` for the "重發邀請" button (line 65-67).

---

### `src/interfaces/web/templates/notifications/settings.html` (template, request-response)

**Analog:** same file — existing `error` block (lines 31-36)

**The template already renders `error`:**
```html
{% if error %}
<div class="alert alert-danger">
  <span>{{ error }}</span>
  <button class="alert-close" onclick="this.parentElement.style.display='none'">×</button>
</div>
{% endif %}
```

**No template changes needed.** The template already has the error display wired. The route handler must pass `error=<message>` in the context when re-rendering on validation failure (see route fix above).

**The `notifications_enabled` toggle visual state** — current JS in `toggleRow()` (lines 131-138) already handles the enabled/disabled UI. The checkbox `name="notify_{s.id}"` is already used to detect enabled state. When `notifications_enabled` is added to the entity, line 71 must also be updated:

```html
{# Current (line 71): #}
{% set enabled = s.notification_emails and s.notification_emails.strip() %}

{# Updated (use entity flag): #}
{% set enabled = s.notifications_enabled %}
```

---

## Shared Patterns

### POST-Redirect-GET
**Source:** `src/interfaces/web/routes/admin.py` — all POST handlers end with `RedirectResponse("/path", status_code=303)`
**Apply to:** All new POST handlers in admin.py, subscriptions.py, notifications.py
```python
return RedirectResponse("/admin/users?password_reset=1", status_code=303)
```

### Route-layer form re-render on validation error
**Source:** `src/interfaces/web/routes/admin.py` `create_user_submit` (lines 59-64)
**Apply to:** `notif_settings_save` in notifications.py when email validation fails
```python
except ValueError as e:
    return templates.TemplateResponse("admin/user_create.html", {
        "request": request,
        "current_user": current_user,
        "error": str(e),
    })
```

### Query-param feedback banners
**Source:** `src/interfaces/web/templates/admin/users.html` lines 19-23
**Apply to:** `users.html` (add `email_failed`, `password_reset`), `user_edit.html` (add `email_failed`)
```html
{% if request.query_params.get('invited') %}
<div class="alert alert-success ...">帳號已建立，邀請信已寄出。</div>
{% endif %}
```

### Token generation for invite/reset
**Source:** `src/interfaces/web/routes/admin.py` `resend_invite` (lines 94-100)
**Apply to:** New `reset-password` endpoint
```python
import secrets
from datetime import datetime, timedelta, timezone
user.invite_token = secrets.token_urlsafe(32)
user.invite_expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
repo.update(user)
```

### SQLAlchemy Boolean column mapping
**Source:** `src/infrastructure/database/sql_subscription_repository.py` line 31
**Apply to:** `notifications_enabled` field in `_to_entity()`, `add()`, `update()`
```python
auto_renew=bool(model.auto_renew),
# Pattern: wrap with bool() to handle SQL Server BIT → Python int coercion
```

---

## No Analog Found

All files have close analogs within the same codebase. No files require falling back to RESEARCH.md patterns.

---

## Key Findings for Planner

1. **`update_subscription.py` already accepts all four bulk-renew fields** (`payment_account`, `auto_renew`, `trial_end_date`, `next_billing_date`) — the bug is entirely in the route handler not passing them through. The use-case fix is only to add `notifications_enabled`.

2. **`notifications/settings.html` template already has `error` rendering** — no template change needed for the validation error display itself. Only the route handler needs to be fixed to pass the error.

3. **`resend_invite` is the exact template for `reset-password`** — copy the handler, change the guard condition (remove `user.invite_token` check), change the subject/body, and change the redirect targets.

4. **`notifications_enabled` must flow through the full stack**: entity field → ORM column → `_to_entity()` → `add()` → `update()` → `execute()` parameter → `check_and_notify.py` filter → template `{% set enabled %}` expression.

5. **`bool()` wrapping is required** when reading SQL Server `BIT` columns — the existing pattern at `sql_subscription_repository.py` line 31 (`auto_renew=bool(model.auto_renew)`) must be copied for `notifications_enabled`.

---

## Metadata

**Analog search scope:** `src/domain/`, `src/application/`, `src/infrastructure/`, `src/interfaces/web/`
**Files read:** 12 source files
**Pattern extraction date:** 2026-05-07
