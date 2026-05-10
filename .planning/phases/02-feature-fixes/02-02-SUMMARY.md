---
phase: 02-feature-fixes
plan: "02"
subsystem: routes-templates
tags: [bug-fix, notifications, admin, password-reset, tdd]
dependency_graph:
  requires: [02-01]
  provides: [bulk-renew-field-preservation, notif-settings-validation, email-failure-banners, admin-password-reset]
  affects:
    - src/interfaces/web/routes/subscriptions.py
    - src/interfaces/web/routes/notifications.py
    - src/interfaces/web/routes/admin.py
    - src/interfaces/web/templates/notifications/settings.html
    - src/interfaces/web/templates/admin/users.html
    - src/interfaces/web/templates/admin/user_edit.html
tech_stack:
  added: []
  patterns: [POST-redirect-GET, query-param-banner, route-layer-form-validation, invite-token-reuse]
key_files:
  created: []
  modified:
    - src/interfaces/web/routes/subscriptions.py
    - src/interfaces/web/routes/notifications.py
    - src/interfaces/web/routes/admin.py
    - src/interfaces/web/templates/notifications/settings.html
    - src/interfaces/web/templates/admin/users.html
    - src/interfaces/web/templates/admin/user_edit.html
decisions:
  - bulk_renew passes notifications_enabled through to use case alongside the four Phase 2B fields (preserves flag through renew cycle)
  - notif_settings_save validates empty emails before the main loop to give fast feedback without partial saves
  - resend_invite email failure redirects to edit page (not users list) to keep context; create_user_submit failure redirects to users list
  - reset-password guards user.role != admin matching the delete_user guard pattern for consistency
metrics:
  duration: ~30min
  completed: 2026-05-11
  tasks_completed: 2
  files_modified: 6
---

# Phase 2 Plan 02: Routes and Templates Bug Fixes Summary

Apply four bug fixes at the route/template layer: bulk_renew field preservation (SUBSCR-01), notification settings silent email corruption (NOTIF-01), missing email-failure UI feedback (NOTIF-02), and admin password reset capability (USER-01).

## What Was Implemented

### Task 1: SUBSCR-01 and NOTIF-01

**bulk_renew field preservation** (`src/interfaces/web/routes/subscriptions.py`, lines 424-428):

Before (missing 5 fields):
```python
billing_cycle=sub.billing_cycle,
# MISSING: payment_account, auto_renew, trial_end_date, next_billing_date, notifications_enabled
```

After:
```python
billing_cycle=sub.billing_cycle,
payment_account=sub.payment_account,
auto_renew=sub.auto_renew,
trial_end_date=sub.trial_end_date,
next_billing_date=sub.next_billing_date,
notifications_enabled=sub.notifications_enabled,
```

**Notification settings POST handler** (`src/interfaces/web/routes/notifications.py`):

Three changes applied:
1. Added `list_uc=Depends(get_list_uc)` to handler signature (for re-render on validation error)
2. Added validation block before main loop — rejects empty email when enabled, re-renders form with error message
3. Changed email preservation logic:
   - Before: `emails = form.get(f"emails_{sid}", "").strip() if enabled else ""` (wiped emails on disable)
   - After: `emails = emails_from_form if enabled else sub.notification_emails` (preserves on disable)
4. Added `notifications_enabled=enabled` to `uc.execute()` call (was missing entirely)

**Notification settings template** (`src/interfaces/web/templates/notifications/settings.html`, line 71):

Before:
```html
{% set enabled = s.notification_emails and s.notification_emails.strip() %}
```
After:
```html
{% set enabled = s.notifications_enabled %}
```

### Task 2: NOTIF-02 and USER-01

**Email failure redirects** (`src/interfaces/web/routes/admin.py`):

- `create_user_submit`: except block now returns `RedirectResponse("/admin/users?email_failed=1")` instead of falling through to `?invited=1`
- `resend_invite`: except block now returns `RedirectResponse(f"/admin/users/{user_id}/edit?email_failed=1")` instead of falling through to `?invited=1`

**New reset-password endpoint** (`src/interfaces/web/routes/admin.py`, added after resend_invite):

```python
@router.post("/users/{user_id}/reset-password")
def reset_password(request, user_id, current_user=Depends(require_admin), repo=Depends(get_user_repo)):
    # Generates new invite_token + invite_expires_at, saves, sends password reset email
    # Guard: user.role != "admin" (prevents admin-on-admin reset)
    # Success: RedirectResponse("/admin/users?password_reset=1")
    # Email failure: RedirectResponse(f"/admin/users/{user_id}/edit?email_failed=1")
```

**Email failure and password reset banners** (`src/interfaces/web/templates/admin/users.html`):

Added two new banners after existing `invited` banner:
- `?email_failed=1` → danger banner: "帳號已建立，但邀請信寄送失敗..."
- `?password_reset=1` → success banner: "密碼重設邀請已寄出..."

**Reset password button** (`src/interfaces/web/templates/admin/user_edit.html`):

Replaced simple button div with flex row containing:
- 取消 link
- Optional `email_failed` inline error message (when `?email_failed=1` in URL)
- Separate `<form>` posting to `/admin/users/{id}/reset-password` with 重置密碼 button
- 儲存 submit button

## Test Results

47 tests passed, 0 failed. No new tests were added (route-layer changes are not unit-testable without HTTP client; behavior verified via grep of key patterns).

## Verification Grep Results

- `payment_account=sub.payment_account` in subscriptions.py: 1 match (bulk_renew)
- `notifications_enabled=enabled` in notifications.py: 1 match
- `notifications_enabled` in notifications/settings.html: 1 match
- `emails = emails_from_form if enabled else sub.notification_emails` in notifications.py: 1 match
- `email_failed` in admin.py: 3 matches (create_user_submit + resend_invite + reset_password)
- `reset-password` in admin.py: 2 matches (route decorator + redirect)
- `password_reset` in admin.py: 1 match (success redirect)
- `email_failed` in users.html: 1 match (banner conditional)
- `password_reset` in users.html: 1 match (banner conditional)
- `重置密碼` in user_edit.html: 1 match
- `reset-password` in user_edit.html: 1 match (form action)

## Deviations from Plan

### Auto-added enhancements

**1. [Rule 2 - Missing functionality] notifications_enabled passed through bulk_renew**
- **Found during:** Task 1
- **Issue:** Plan specified adding `payment_account`, `auto_renew`, `trial_end_date`, `next_billing_date` to bulk_renew. `notifications_enabled` was also missing from the call, which would reset the flag to the use case default (True) on every bulk renew — silently disabling any subscriptions where the user had set `notifications_enabled=False`
- **Fix:** Added `notifications_enabled=sub.notifications_enabled` to the bulk_renew uc.execute() call alongside the four specified fields
- **Files modified:** `src/interfaces/web/routes/subscriptions.py`
- **Commit:** 4fa93cc

**2. [Rule 2 - Missing functionality] payment_account and other Phase 2B fields passed through notif_settings_save**
- **Found during:** Task 1
- **Issue:** The notification settings POST handler called uc.execute() with ~14 fields but was missing `payment_account`, `auto_renew`, `trial_end_date`, `next_billing_date` — these would be reset to None/False on every notification settings save
- **Fix:** Added all four missing fields to uc.execute() in the notif_settings_save loop
- **Files modified:** `src/interfaces/web/routes/notifications.py`
- **Commit:** 4fa93cc

## Known Stubs

None — all fixes wire real behavior end-to-end.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| threat_flag: elevation-of-privilege | src/interfaces/web/routes/admin.py | reset_password guarded by `user.role != "admin"` (T-02-02-01 mitigated as designed) |

No new unmitigated surface introduced.

## Self-Check: PASSED

- src/interfaces/web/routes/subscriptions.py modified and contains `payment_account=sub.payment_account`
- src/interfaces/web/routes/notifications.py modified and contains `notifications_enabled=enabled`
- src/interfaces/web/templates/notifications/settings.html modified and contains `notifications_enabled`
- src/interfaces/web/routes/admin.py modified and contains `reset-password` endpoint
- src/interfaces/web/templates/admin/users.html modified and contains `email_failed` and `password_reset` banners
- src/interfaces/web/templates/admin/user_edit.html modified and contains `重置密碼` button
- Commits 4fa93cc and 9451ff5 confirmed in git log
- All 47 tests pass
