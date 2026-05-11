# SubTrack — Project State

## Current Status
Phase: 3 — plans ready, ready to execute
Last updated: 2026-05-11

## Project Reference
See: `.planning/PROJECT.md`

**Core value**: 到期日前就知道，不在服務中斷後才發現
**Current focus**: Phase 3 — Reports & Subscription Filtering

## Phase Progress

| Phase | Name | Status | Requirements |
|-------|------|--------|--------------|
| 1 | Foundation & Security | Complete | SEC-01, SEC-02, DEBT-01 |
| 2 | Feature Fixes | Complete | SUBSCR-01, NOTIF-01, NOTIF-02, USER-01 |
| 3 | Reports & Subscription Filtering | Ready to execute | REPORT-01, REPORT-02, REPORT-03, SUBSCR-02 |
| 4 | UI Redesign | Not Started | UI-01 |
| 5 | Deployment & Documentation | Not Started | DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04 |

## Resume From
Phase 3 planned (2 plans, 2 waves). Run `/gsd-execute-phase 3` to begin execution.

## Decisions
- Used os.getenv("SECRET_KEY", "") in lifespan so RuntimeError message is clear rather than raw KeyError
- session.py uses os.getenv("SECRET_KEY", "") at module level so import succeeds; lifespan's RuntimeError gives the clear error message
- Middleware placed after include_router calls per FastAPI middleware ordering semantics
- Removed passlib[bcrypt]==1.7.4; pinned bcrypt==5.0.0 directly to eliminate compatibility issues with bcrypt>=4.0
- Shared Jinja2Templates placed in dependencies.py (same file as engine/SessionLocal singletons) for consistency
- annual_cost() placed on Subscription entity as domain method — pure logic from entity fields, not route handler
- ORM defaults use lambda: datetime.now(timezone.utc) not bare datetime.now (bare callable produces naive datetimes)
- notifications_enabled defaults to True in both entity field and UpdateSubscriptionUseCase parameter — preserves all existing callers with no change
- bool() wraps SQL Server BIT→int coercion in _to_entity() for notifications_enabled (same pattern as auto_renew)
- bulk_renew passes notifications_enabled through to use case to prevent silent reset of the flag on renew
- notif_settings_save email validation runs before the main save loop to give fast feedback without partial saves
- reset-password guards user.role != admin matching the delete_user guard pattern for consistency
- resend_invite email failure redirects to edit page (keeps context); create_user_submit failure redirects to users list

## Session Log
- 2026-05-07: Phase 1 context gathered → `.planning/phases/01-foundation-security/01-CONTEXT.md`
- 2026-05-07: Phase 1 planned → 2 plans (01-01 SEC, 01-02 DEBT), verification passed
- 2026-05-07: Plan 01-01 complete — SEC-01 + SEC-02 implemented (commits 845c98f, 1c4d3ec)
- 2026-05-07: Plan 01-02 complete — DEBT-01 all 6 items resolved (commits fa359cd, 46f04ac, 6490601)
- 2026-05-07: Phase 1 code review + verification passed — 3 post-review fixes applied (commit c77cdfb); Phase 1 complete
- 2026-05-07: Phase 2 context gathered → `.planning/phases/02-feature-fixes/02-CONTEXT.md`
- 2026-05-10: Phase 2 planned → 2 plans (02-01 domain stack, 02-02 routes/templates), coverage verified
- 2026-05-10: Plan 02-01 complete — notifications_enabled wired through domain stack (commits eb8a5eb, 677d979, 75641b0, 5e65d27); 47 tests pass
- 2026-05-11: Plan 02-02 complete — routes/templates bug fixes (commits 4fa93cc, 9451ff5); 47 tests pass; Phase 2 complete
