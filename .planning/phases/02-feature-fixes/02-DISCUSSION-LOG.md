# Phase 2: Feature Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 2-Feature Fixes
**Areas discussed:** NOTIF-01 (disabled notifications), NOTIF-02 (email failure feedback), USER-01 (password reset mechanism), SUBSCR-01 (bulk renew fix scope)

---

## NOTIF-01: Disabled Notifications Behavior

### Q1: When notifications are disabled, should the email list be preserved or cleared?

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve emails, add enabled flag | Add `notifications_enabled` boolean to entity + DB; disabling toggles flag without touching email list | ✓ |
| Preserve emails, no new field | Skip saving email when toggle is off; empty emails = disabled implicitly | |
| Clear emails on disable | Current (broken) behavior — wipes list permanently | |

**User's choice:** Preserve emails, add `notifications_enabled` flag (recommended)

---

### Q2: What should `notifications_enabled` default to for existing DB rows on migration?

| Option | Description | Selected |
|--------|-------------|----------|
| True if emails non-empty, False if empty | Smart default — existing active subscriptions stay on | ✓ |
| True for all | Blanket enable; risks SMTP errors for empty-email rows | |
| False for all | Blanket disable; requires admin to re-enable each one | |

**User's choice:** True if emails non-empty, False if empty (recommended)

---

### Q3: Where should empty-email validation live?

| Option | Description | Selected |
|--------|-------------|----------|
| Route layer — form validation before use case | Check in notifications.py; re-render form with error if enabled+empty | ✓ |
| Use case layer — raise ValueError | More testable but requires extracting a new use case | |

**User's choice:** Route layer (recommended)

---

## NOTIF-02: Email Failure Feedback

### Q1: How should the admin be informed when an invite email fails to send?

| Option | Description | Selected |
|--------|-------------|----------|
| Query-param banner on redirect | `?email_failed=1`; template shows warning banner; consistent with `?invited=1` pattern | ✓ |
| Flash message system | Generic flash/toast; reusable but requires new infrastructure | |
| Form re-render with inline error | Breaks POST-redirect-GET pattern | |

**User's choice:** Query-param banner (recommended)

---

### Q2: Should the same pattern apply to notification job failures?

| Option | Description | Selected |
|--------|-------------|----------|
| No — notifications job runs headlessly | Failures logged; no UI banner needed | ✓ |
| Yes — surface job failures in admin panel | Requires DB-stored job state; much larger scope | |

**User's choice:** No (recommended) — NOTIF-02 scope is invite emails only

---

## USER-01: Password Reset Mechanism

### Q1: What should admin password reset actually do?

| Option | Description | Selected |
|--------|-------------|----------|
| Re-trigger invite flow | New token + email; user sets own password; reuses existing infrastructure | ✓ |
| Admin types temp password | Requires `must_change_password` flag on User entity | |
| System generates random password shown once | No email dependency; admin shares verbally | |

**User's choice:** Re-trigger invite flow (recommended)

---

### Q2: Where in the admin UI should the "Reset Password" button appear?

| Option | Description | Selected |
|--------|-------------|----------|
| User edit page | On /admin/users/{id}/edit alongside other actions | ✓ |
| User list page inline | In table row; more crowded | |

**User's choice:** User edit page (recommended)

---

### Q3: Separate endpoint or reuse resend-invite?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate POST endpoint | POST /admin/users/{id}/reset-password — clearer intent, easier to audit | ✓ |
| Reuse resend-invite endpoint | Simpler but conflates two different operations | |

**User's choice:** Separate POST endpoint (recommended)

---

## SUBSCR-01: Bulk Renew Fix Scope

### Q1: How far should the fix go?

| Option | Description | Selected |
|--------|-------------|----------|
| Fix missing fields only | Read existing subscription, pass four missing fields through to execute() | ✓ |
| Fix fields + extract BulkRenewUseCase | Cleaner architecture but significantly more work for a one-line data fix | |

**User's choice:** Fix missing fields only (recommended)

---

### Q2: Does UpdateSubscriptionUseCase already accept all four fields?

| Option | Description | Selected |
|--------|-------------|----------|
| You decide — check use case and fix accordingly | Let planner/executor read the signature and add if missing | ✓ |
| They're already in the use case | Pure route fix | |
| They may need to be added | Entity + use case change too | |

**User's choice:** You decide (Claude's discretion)

---

## Claude's Discretion

- Whether `UpdateSubscriptionUseCase.execute()` already accepts all four bulk-renew fields — executor reads current signature and adds if missing
- Exact wording of the email-failure banner (Chinese UI)
- Whether "重置密碼" button appears for users who haven't yet accepted invite

## Deferred Ideas

- `BulkRenewSubscriptionUseCase` extraction — future debt cleanup phase
- `SmtpEmailSender` DI via `Depends()` — same future debt phase
- Flash/toast system — Phase 4 UI redesign
- Notification job error surfacing in admin UI — v2 feature
