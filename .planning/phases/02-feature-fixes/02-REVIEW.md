---
phase: 02-feature-fixes
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/domain/entities/subscription.py
  - src/infrastructure/database/models.py
  - src/infrastructure/database/sql_subscription_repository.py
  - src/application/use_cases/update_subscription.py
  - src/application/use_cases/check_and_notify.py
  - src/interfaces/web/routes/subscriptions.py
  - src/interfaces/web/routes/notifications.py
  - src/interfaces/web/routes/admin.py
  - src/interfaces/web/templates/notifications/settings.html
  - src/interfaces/web/templates/admin/users.html
  - src/interfaces/web/templates/admin/user_edit.html
  - tests/unit/test_check_and_notify.py
  - tests/unit/test_update_subscription.py
  - tests/unit/test_subscription_entity.py
  - tests/unit/test_create_subscription.py
findings:
  critical: 5
  warning: 5
  info: 2
  total: 12
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Reviewed 15 source files across the domain entity layer, infrastructure repository, two use cases, three route modules, three templates, and four test modules. The code follows clean architecture conventions consistently and the test suite has good coverage of the happy path.

Five blockers were found: two correctness bugs in the notification use case (one causing silent data loss on partial failures, one allowing zero-byte emails to be sent), two silent-success flows in admin routes that return success responses for no-op operations, and a template XSS vector via an unquoted display name injected into JavaScript. Five warnings cover unhandled exceptions that produce 500 responses, a broken bulk-renew billing-cycle calculation, an enum parsing crash on legacy DB data, and a misleading `notification_emails` preservation when disabling notifications.

---

## Critical Issues

### CR-01: Notification use case loses IDs when any single send fails

**File:** `src/application/use_cases/check_and_notify.py:55-63`

**Issue:** `success` is a single boolean flag covering the entire loop of recipients. If the first recipient's `send()` raises but the second succeeds, `success` ends up `False` and the method returns `[]` — losing the IDs of subscriptions whose notifications *did* reach at least one person. Callers that use the return value to update state (e.g., to avoid re-notifying) will re-send to already-notified recipients the next run, or never record them at all. The current test `test_email_failure_returns_empty_notified` asserts `[]` on failure, which validates the broken behaviour.

Additionally: because all recipients across all due subscriptions are pooled into one list and sent the same body, one bad address in *any* subscription's `notification_emails` poisons notification for the entire batch.

**Fix:**
```python
notified_ids: list[int] = []
for recipient in recipients:
    try:
        self._email_sender.send(to=recipient, subject=subject, body=body)
    except Exception as exc:
        print(f"[ERROR] Failed to send email to {recipient}: {exc}")

# Return IDs regardless of partial send failures; callers decide on retry policy.
return [sub.id for sub in due_subs]
```
If per-subscription tracking is needed, send one email per subscription instead of pooling recipients.

---

### CR-02: XSS / JS injection via unescaped `display_name` in JavaScript

**File:** `src/interfaces/web/templates/admin/users.html:81`

**Issue:** The user's `display_name` is interpolated directly into a JavaScript string literal without escaping:

```html
onclick="confirmDeleteUser({{ user.id }}, '{{ user.display_name }}')"
```

A display name containing a single quote (e.g., `O'Brien`) breaks the JS string and causes a syntax error. A name containing `'); alert(document.cookie);//` constitutes stored XSS, executable by any admin who views the users list page. Since admins create users, this is an admin-to-admin XSS, but stored XSS on an admin page is still a security defect.

**Fix:**
Pass the name via a `data-*` attribute and read it in the JS handler, avoiding interpolation into script context entirely:

```html
<!-- Template -->
<button class="btn btn-ghost btn-sm" style="color:var(--danger-text);"
        data-user-id="{{ user.id }}"
        data-user-name="{{ user.display_name | e }}"
        onclick="confirmDeleteUser(this)">移除</button>

<!-- Script -->
function confirmDeleteUser(btn) {
  const id   = btn.dataset.userId;
  const name = btn.dataset.userName;
  document.getElementById('deleteUserMsg').textContent = '確定要移除「' + name + '」？此操作無法復原。';
  document.getElementById('deleteUserForm').action = '/admin/users/' + id + '/delete';
  document.getElementById('deleteUserModal').classList.add('show');
}
```

---

### CR-03: `resend_invite` silently returns success when token is absent

**File:** `src/interfaces/web/routes/admin.py:98-120`

**Issue:** The guard `if user and user.invite_token:` silently skips both the token refresh and the email send when `invite_token` is `None` (i.e., the user already set their password and the token was cleared). The function falls through to `return RedirectResponse("/admin/users?invited=1", status_code=303)` — which is the *success* URL — so the admin is shown "邀請信已寄出" even though nothing happened.

**Fix:**
```python
user = repo.get_by_id(user_id)
if not user:
    raise HTTPException(status_code=404)
if not user.invite_token:
    # User already accepted invite; redirect with an informative param instead.
    return RedirectResponse("/admin/users?already_active=1", status_code=303)
# ... regenerate token and send email ...
```

---

### CR-04: `reset_password` silently returns success for non-existent user

**File:** `src/interfaces/web/routes/admin.py:132-156`

**Issue:** The condition `if user and user.role != "admin":` means that when `user is None` (non-existent `user_id`), the entire body is skipped and the handler redirects to `?password_reset=1` — a success message — with no action taken and no error surfaced.

**Fix:**
```python
user = repo.get_by_id(user_id)
if not user:
    raise HTTPException(status_code=404)
if user.role == "admin":
    raise HTTPException(status_code=403)
# ... regenerate token and send email ...
```

---

### CR-05: `_add_billing_period` only handles monthly and annual; other cycles produce wrong expiry in bulk-renew

**File:** `src/interfaces/web/routes/subscriptions.py:163-173`

**Issue:** The `try/except ValueError` block falls through to `d.replace(year=d.year + 1)` for all billing cycles other than `monthly`. This means `quarterly` (3 months), `semi_annual` (6 months), and `biennial` (2 years) all produce an incorrectly computed new expiry date — a full year ahead instead of the correct period. This silently produces incorrect data in the database when bulk-renew is used.

**Fix:**
```python
def _add_billing_period(d: date, billing_cycle: str | None) -> date:
    bc = (billing_cycle or "annual").lower()
    if bc == "monthly":
        m, y = d.month + 1, d.year
        if m > 12:
            m, y = 1, y + 1
        return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
    if bc == "quarterly":
        months = d.month - 1 + 3
        y = d.year + months // 12
        m = months % 12 + 1
        return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
    if bc == "semi_annual":
        months = d.month - 1 + 6
        y = d.year + months // 12
        m = months % 12 + 1
        return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
    if bc == "biennial":
        try:
            return d.replace(year=d.year + 2)
        except ValueError:
            return date(d.year + 2, 2, 28)
    # annual (default)
    try:
        return d.replace(year=d.year + 1)
    except ValueError:
        return date(d.year + 1, 2, 28)
```

---

## Warnings

### WR-01: Unhandled `ValueError` on malformed date input produces HTTP 500

**File:** `src/interfaces/web/routes/subscriptions.py:227, 304`

**Issue:** `datetime.strptime(expiry_date, "%Y-%m-%d")` is called without a try/except. If the form submits an invalid date string (e.g., via a direct POST), FastAPI propagates the `ValueError` as a 500 Internal Server Error rather than a 400 with a user-facing message. Same applies to `trial_end_date` and `next_billing_date` parsing on lines 240-241 and 317-318.

**Fix:**
```python
try:
    parsed_expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
except ValueError:
    # Re-render form with error message
    return templates.TemplateResponse("create.html", {
        "request": request, "error": "到期日格式不正確", ...
    }, status_code=422)
```

---

### WR-02: Malformed `sub_ids` or `ids` form field raises unhandled `ValueError` → HTTP 500

**File:** `src/interfaces/web/routes/subscriptions.py:403`, `src/interfaces/web/routes/notifications.py:49`

**Issue:** Both routes parse IDs with `int(x.strip())` in a list comprehension with no exception handling. A crafted POST with a non-integer in the comma-separated list (e.g., `ids=1,2,abc`) raises `ValueError` and returns a 500.

**Fix:**
```python
# subscriptions.py bulk_renew
id_list = []
for x in ids.split(","):
    x = x.strip()
    if x.isdigit():
        id_list.append(int(x))

# notifications.py notif_settings_save
ids = [int(i) for i in sub_ids_raw.split(",") if i.strip().isdigit()]
```

---

### WR-03: `NotificationDays` enum construction crashes on legacy DB values

**File:** `src/infrastructure/database/sql_subscription_repository.py:20`

**Issue:** `NotificationDays(model.notification_days)` raises `ValueError` if the database contains an integer not present in the enum (e.g., a legacy value of `60`, or `1`). This causes `get_all_active()` to raise during the list comprehension on line 76, which crashes the dashboard and the notification job for all users — not just the offending row.

**Fix:**
```python
try:
    nd = NotificationDays(model.notification_days)
except ValueError:
    nd = NotificationDays.THIRTY  # safe fallback; log a warning
```

---

### WR-04: Notification settings POST makes N+1 DB calls per subscription in the validation loop

**File:** `src/interfaces/web/routes/notifications.py:53-73`

**Issue:** For each enabled subscription with an empty email, `single_uc.execute(sid)` and `list_uc.execute()` are both called inside the validation loop. `list_uc.execute()` fetches all active subscriptions from the database on every iteration. If 10 subscriptions are being saved and 3 have empty emails, this makes 3 full-table-scans during validation before returning the error page. While performance is noted as out-of-v1-scope, the correctness concern here is that the first failing subscription short-circuits validation and returns — other invalid subscriptions are not shown. The re-fetched `subscriptions` list may also differ from the page state (if another user edited something concurrently), producing a confusing error page.

**Fix:**
Run the full validation pass first (collecting all errors), then process saves. Reuse the already-loaded subscription list from before form parsing rather than re-querying inside the loop.

---

### WR-05: `resend_invite` regenerates token without checking whether user already activated

**File:** `src/interfaces/web/routes/admin.py:98-101`

**Issue:** (Related to CR-03, separate concern.) When `user.invite_token` is present and is regenerated, there is no check that `user.is_active` is `False`. If a user who set their password somehow retained a stale token in the DB, the admin resending the invite would create a new valid token — potentially allowing the account to be "re-invited" and have its password reset by anyone who receives the email link, without the user's awareness.

**Fix:**
Only regenerate and send the invite if `not user.is_active` or if the prior token is genuinely pending (i.e., the user hasn't logged in yet). Consider checking `user.last_login_at is None` as a proxy for "never logged in."

---

## Info

### IN-01: `type` parameter shadows Python built-in

**File:** `src/interfaces/web/routes/admin.py:229`

**Issue:** The form parameter `type: str = Form(...)` shadows the Python built-in `type`. While harmless here, it is a poor naming choice that will confuse readers and linters.

**Fix:** Rename to `option_type: str = Form(...)` and update the two uses on lines 235-236.

---

### IN-02: `notifications_enabled` comment in `notifications.py` is misleading

**File:** `src/interfaces/web/routes/notifications.py:82`

**Issue:** The comment `# preserve on disable (per D-04)` describes preserving `notification_emails` when a subscription is disabled. However, the info-box in `notifications/settings.html` tells users "清空收件人欄位即關閉該訂閱的通知" (clearing the email field disables notifications). This creates a discrepancy: the UI implies that clearing emails disables notifications, but the backend explicitly preserves emails when the toggle is turned off. A user who disables via toggle and then expects the email field to be cleared will be surprised if they later re-enable and find old addresses restored. This is not a bug per se, but the two UX models conflict and should be documented or reconciled.

**Fix:** Either align the UI help text with the actual behaviour (D-04: toggling disables without clearing emails) or, if clearing emails should disable notifications, enforce that at the backend and remove the `if enabled else sub.notification_emails` branch.

---

_Reviewed: 2026-05-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
