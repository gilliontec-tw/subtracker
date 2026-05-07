# Phase 2: Feature Fixes - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix four known bugs where existing features either silently corrupt data, produce no user feedback on failure, or are missing entirely. No new capabilities are added in this phase.

**In scope:**
- SUBSCR-01: Bulk Renew silently drops `payment_account`, `auto_renew`, `trial_end_date`, `next_billing_date` — pass missing fields through to the use case
- NOTIF-01: Notification settings page — add `notifications_enabled` flag so disabling preserves the email list; validate empty emails at route layer
- NOTIF-02: Invite email send failures now logged (Phase 1) — add visible UI feedback for admin via query-param banner
- USER-01: Admin can reset any user's password without deleting the account — re-trigger the invite flow (new token + email)

**Out of scope:**
- Extracting `BulkRenewSubscriptionUseCase` (architecture refactor — future phase)
- Notification job failure surfacing in admin UI (headless job, logs are sufficient)
- Flash/toast system (no new infrastructure needed — query params are sufficient for Phase 2)
- CSRF protection, password complexity enforcement, health-check endpoint (deferred per Phase 1)

</domain>

<decisions>
## Implementation Decisions

### NOTIF-01: Notification Enable/Disable

- **D-01:** Add a `notifications_enabled` boolean field to the `Subscription` entity (`src/domain/entities/subscription.py`) and the `SubscriptionModel` ORM (`src/infrastructure/database/models.py`). DB column: `notifications_enabled BIT NOT NULL DEFAULT 1`.
- **D-02:** Migration default strategy: set `notifications_enabled = True` for subscriptions with non-empty `notification_emails`; `False` for subscriptions with empty or NULL `notification_emails`. This preserves intent without requiring manual admin fix-up.
- **D-03:** Route-layer validation in `src/interfaces/web/routes/notifications.py`: if `enabled=True` and `emails` is empty/whitespace, re-render the form with an error message. Do NOT call the use case. Consistent with existing form validation pattern in this codebase.
- **D-04:** When `enabled=False` on form submit, save `notifications_enabled = False` but preserve the existing `notification_emails` value unchanged in the DB.
- **D-05:** `CheckAndNotifyUseCase` must respect the new flag: skip subscriptions where `notifications_enabled = False` regardless of email content.

### NOTIF-02: Email Failure Feedback

- **D-06:** On invite email send failure in `create_user_submit` and `resend_invite` handlers in `src/interfaces/web/routes/admin.py`: redirect with `?email_failed=1` query param. The admin users template renders a visible warning banner when this param is present.
- **D-07:** Notification job failures (`scripts/run_notifications.py`) — logs only. The job runs headlessly; no UI banner needed.

### USER-01: Admin Password Reset

- **D-08:** Password reset re-triggers the invite flow: generate a new `invite_token` (via `secrets.token_urlsafe(32)`), set `invite_expires_at = datetime.now(timezone.utc) + timedelta(hours=72)`, save, and send an invite email. The user visits the invite link and sets their own new password — exactly the same as first-time account setup.
- **D-09:** New endpoint: `POST /admin/users/{user_id}/reset-password`. Separate from `POST /admin/users/{user_id}/resend-invite` to keep intent clear (activate vs reset).
- **D-10:** Button location: on the existing `GET /admin/users/{user_id}/edit` page. A "重置密碼" (Reset Password) button inside the edit form, alongside existing actions.
- **D-11:** Success/failure feedback follows the same `?password_reset=1` / `?email_failed=1` query-param pattern as NOTIF-02.

### SUBSCR-01: Bulk Renew Field Fix

- **D-12:** Fix scope: pass missing fields through in the existing route handler. Do NOT extract `BulkRenewSubscriptionUseCase`.
- **D-13:** Implementation approach: read the existing subscription from the repo before calling `UpdateSubscriptionUseCase.execute()`, then pass `payment_account`, `auto_renew`, `trial_end_date`, `next_billing_date` from the fetched entity. Let the planner/executor verify which fields the use case already accepts; add them if missing.

### Claude's Discretion

- Whether `UpdateSubscriptionUseCase.execute()` already accepts all four bulk-renew fields or needs them added — executor should read the current signature and fix accordingly.
- Exact wording of the email-failure banner in the admin template (Chinese UI).
- Whether to show the "重置密碼" button for users who haven't yet accepted their invite (likely yes — same flow).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Docs
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria (5 items), requirements list
- `.planning/REQUIREMENTS.md` — SUBSCR-01, NOTIF-01, NOTIF-02, USER-01 detailed specs

### Affected Routes
- `src/interfaces/web/routes/subscriptions.py` — `bulk_renew` POST handler (lines 429–467); missing fields call site
- `src/interfaces/web/routes/notifications.py` — notification settings form handler; toggle + email save logic (lines 65–67)
- `src/interfaces/web/routes/admin.py` — `create_user_submit` (invite email, lines ~65–81), `resend_invite` (lines ~89–115); add `reset-password` endpoint here

### Affected Use Cases & Domain
- `src/application/use_cases/update_subscription.py` — check which fields `execute()` accepts; add missing ones if needed
- `src/application/use_cases/check_and_notify.py` — must respect new `notifications_enabled` flag (line 25: `should_notify_today` check)
- `src/domain/entities/subscription.py` — add `notifications_enabled: bool = True` field here
- `src/domain/entities/user.py` — review `invite_token` + `invite_expires_at` fields for reset-password reuse
- `src/domain/repositories/user_repository.py` — check if `update()` method is available for saving reset token

### Affected Infrastructure
- `src/infrastructure/database/models.py` — add `notifications_enabled` column to `SubscriptionModel`
- `src/infrastructure/database/sql_subscription_repository.py` — map `notifications_enabled` in `_to_entity()`, `add()`, `update()`

### Affected Templates
- `src/interfaces/web/templates/admin/users.html` — add email-failure banner conditional on `?email_failed=1`
- `src/interfaces/web/templates/admin/user_edit.html` — add "重置密碼" button
- `src/interfaces/web/templates/notifications/settings.html` — add empty-email validation error display

### Prior Phase Context
- `.planning/phases/01-foundation-security/01-CONTEXT.md` — D-05: logging in admin.py is already wired; D-08: `log.exception` in both except blocks already done in Phase 1

### Codebase Maps
- `.planning/codebase/ARCHITECTURE.md` — Clean Architecture layers, DI patterns, anti-patterns (bulk_renew and SmtpEmailSender direct instantiation)
- `.planning/codebase/CONCERNS.md` — Full concern audit with exact file/line refs for NOTIF-01 (line 65–67), NOTIF-02 (lines 79–81, 113–115), USER-01 (missing), SUBSCR-01 (lines 443–458)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `resend_invite` handler in `admin.py` — already implements token generation + email send; `reset-password` endpoint reuses the same logic with a different route and feedback message
- `invite_token` + `invite_expires_at` fields on `User` entity — already exist; no new entity fields needed for USER-01
- `?invited=1` query-param pattern in `admin.py` — template already checks this for success banner; extend same pattern for `?email_failed=1` and `?password_reset=1`

### Established Patterns
- **Route-layer form validation** — existing routes re-render templates with an `error=` context variable on validation failure; NOTIF-01 should follow this pattern
- **Repository fetch before use case** — SUBSCR-01 fix: `repo.get_by_id(subscription_id)` to read existing entity, then pass preserved fields to `execute()`
- **POST-redirect-GET** — all mutating routes redirect after success; no form re-renders on success

### Integration Points
- `src/interfaces/web/dependencies.py` — `get_subscription_repo()` and `get_update_subscription_uc()` providers used in `subscriptions.py`; `get_user_repo()` in `admin.py`
- `src/application/use_cases/check_and_notify.py` line 25 — `should_notify_today()` filter; add `and sub.notifications_enabled` check here
- `src/infrastructure/database/sql_subscription_repository.py` `_to_entity()` — add `notifications_enabled` mapping here and in `add()` / `update()`

</code_context>

<specifics>
## Specific Ideas

- The `notifications_enabled` DB column should be `BIT NOT NULL DEFAULT 1` — keeps existing behavior (notifications on by default) without requiring NULL handling.
- For the migration default (D-02): since there's no Alembic, the migration is a one-time SQL script. The planner should produce the exact `ALTER TABLE` + `UPDATE` statement for the instructions doc.
- "重置密碼" is the button label (Traditional Chinese, consistent with rest of admin UI).
- The `reset-password` endpoint should check that the user exists before generating a new token; return 404 or redirect to user list if not found.

</specifics>

<deferred>
## Deferred Ideas

- **`BulkRenewSubscriptionUseCase` extraction** — ARCHITECTURE.md anti-pattern; defer to a future debt cleanup phase (Phase 3 or a separate debt phase).
- **`SmtpEmailSender` DI via `Depends()`** — another ARCHITECTURE.md anti-pattern in `admin.py`; defer to same future debt phase.
- **Flash/toast system** — query params are sufficient for Phase 2; a proper flash system could be added in Phase 4 (UI redesign).
- **Notification job error surfacing in UI** — would require DB-stored job state; v2 feature.

</deferred>

---

*Phase: 2-Feature Fixes*
*Context gathered: 2026-05-07*
