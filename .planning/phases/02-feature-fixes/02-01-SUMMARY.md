---
phase: 02-feature-fixes
plan: "01"
subsystem: domain-infrastructure
tags: [notifications, domain-model, tdd]
dependency_graph:
  requires: []
  provides: [notifications_enabled-field, check-and-notify-filter]
  affects: [src/domain/entities/subscription.py, src/infrastructure/database/models.py, src/infrastructure/database/sql_subscription_repository.py, src/application/use_cases/update_subscription.py, src/application/use_cases/check_and_notify.py]
tech_stack:
  added: []
  patterns: [TDD RED-GREEN, dataclass-field-default, BIT-column-bool-coercion]
key_files:
  created: []
  modified:
    - src/domain/entities/subscription.py
    - src/infrastructure/database/models.py
    - src/infrastructure/database/sql_subscription_repository.py
    - src/application/use_cases/update_subscription.py
    - src/application/use_cases/check_and_notify.py
    - tests/unit/test_check_and_notify.py
    - tests/unit/test_update_subscription.py
    - tests/unit/test_subscription_entity.py
    - tests/unit/test_create_subscription.py
decisions:
  - notifications_enabled defaults to True in both entity and use case parameter to preserve existing behavior for all callers
  - bool() wrapping in _to_entity() prevents SQL Server BIT integer coercion issue (T-02-01-01 mitigated)
  - Filter in check_and_notify places notifications_enabled check before should_notify_today() for short-circuit efficiency
metrics:
  duration: ~25min
  completed: 2026-05-10
  tasks_completed: 2
  files_modified: 9
---

# Phase 2 Plan 01: notifications_enabled Domain Stack Summary

Wire `notifications_enabled` boolean flag from Subscription entity through ORM, repository, use cases — with `bool()` BIT coercion safety and `CheckAndNotifyUseCase` filter that skips disabled subscriptions without touching the email list.

## What Was Implemented

### Task 1: Entity, ORM, Repository

**Entity field** (`src/domain/entities/subscription.py`):
```python
notifications_enabled: bool = True   # added after next_billing_date, before created_at
```

**ORM column** (`src/infrastructure/database/models.py`):
```python
notifications_enabled = Column(Boolean, nullable=False, default=True)
```
Placed after `next_billing_date`, before `icon_emoji`.

**Repository mappings** (`src/infrastructure/database/sql_subscription_repository.py`):
- `_to_entity()`: `notifications_enabled=bool(model.notifications_enabled)` — bool() wraps SQL Server BIT→int coercion (T-02-01-01)
- `add()`: `notifications_enabled=subscription.notifications_enabled`
- `update()`: `model.notifications_enabled = subscription.notifications_enabled`

### Task 2: Use Cases

**UpdateSubscriptionUseCase** (`src/application/use_cases/update_subscription.py`):
- Parameter added: `notifications_enabled: bool = True` (after `next_billing_date`)
- Assignment added: `entity.notifications_enabled = notifications_enabled`

**CheckAndNotifyUseCase** (`src/application/use_cases/check_and_notify.py`):
```python
due_subs = [
    s for s in subscriptions
    if s.notifications_enabled and s.should_notify_today(today)
]
```

## Migration SQL

**Run in SSMS before deploying this change:**

```sql
ALTER TABLE saas_subscriptions
  ADD notifications_enabled BIT NOT NULL DEFAULT 1;

-- Backfill: disable for subscriptions with no emails configured
UPDATE saas_subscriptions
SET notifications_enabled = 0
WHERE notification_emails IS NULL
   OR LTRIM(RTRIM(notification_emails)) = '';
```

This must be executed BEFORE restarting the application, otherwise the ORM will fail to read/write the column.

## Test Results

47 tests passed, 0 failed.

New tests added:
- `test_disabled_subscription_is_skipped` — notifications_enabled=False → no email even on due date
- `test_enabled_subscription_is_notified` — notifications_enabled=True → email sent (existing behavior preserved)
- `test_update_notifications_enabled_defaults_to_true` — execute() without param defaults to True
- `test_update_notifications_enabled_false_is_saved` — execute(notifications_enabled=False) persists False

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed icon_emoji references from pre-existing tests**
- **Found during:** Task 1 (pre-existing failure before any changes)
- **Issue:** `test_create_subscription_with_phase2b_fields`, `test_update_subscription_with_phase2b_fields`, `test_subscription_has_phase2b_fields`, and `test_subscription_phase2b_fields_default_values` all referenced `icon_emoji` kwarg/attribute on `Subscription`, but CLAUDE.md states `login_password` and `icon_emoji` are intentionally excluded from the entity
- **Fix:** Removed `icon_emoji="..."` kwargs from test constructors and `assert saved.icon_emoji == ...` assertions. In `test_subscription_phase2b_fields_default_values`, replaced `assert sub.icon_emoji is None` with `assert sub.notifications_enabled is True` (adds value for this plan's scope)
- **Files modified:** `tests/unit/test_create_subscription.py`, `tests/unit/test_update_subscription.py`, `tests/unit/test_subscription_entity.py`
- **Commits:** 677d979 (create/update), 5e65d27 (entity)
- **Plan acknowledgment:** The plan for Task 2 explicitly noted this fix was needed — "If pytest fails on that test with AttributeError, update the test to remove the icon_emoji kwarg"

## Known Stubs

None — this plan wires real logic end-to-end. The feature is complete at the domain/infrastructure layer pending the route/template changes in Plan 02-02.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundary crossings introduced. All changes are internal domain and infrastructure layer only.

## Self-Check: PASSED

- src/domain/entities/subscription.py exists and contains `notifications_enabled: bool = True`
- src/infrastructure/database/models.py exists and contains `notifications_enabled` column
- src/infrastructure/database/sql_subscription_repository.py has 3 occurrences of `notifications_enabled`
- src/application/use_cases/update_subscription.py has 2 occurrences of `notifications_enabled`
- src/application/use_cases/check_and_notify.py has 1 occurrence of `notifications_enabled`
- All 47 tests pass
- Commits eb8a5eb, 677d979, 75641b0, 5e65d27 confirmed in git log
