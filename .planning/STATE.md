# SubTrack — Project State

## Current Status
Phase: 1 — complete (both plans done)
Last updated: 2026-05-07

## Project Reference
See: `.planning/PROJECT.md`

**Core value**: 到期日前就知道，不在服務中斷後才發現
**Current focus**: Phase 1 — Foundation & Security

## Phase Progress

| Phase | Name | Status | Requirements |
|-------|------|--------|--------------|
| 1 | Foundation & Security | Complete | SEC-01, SEC-02, DEBT-01 |
| 2 | Feature Fixes | Not Started | SUBSCR-01, NOTIF-01, NOTIF-02, USER-01 |
| 3 | Reports & Subscription Filtering | Not Started | REPORT-01, REPORT-02, REPORT-03, SUBSCR-02 |
| 4 | UI Redesign | Not Started | UI-01 |
| 5 | Deployment & Documentation | Not Started | DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04 |

## Resume From
Run `/gsd-discuss-phase 2` to begin Phase 2 (Feature Fixes).

## Decisions
- Used os.getenv("SECRET_KEY", "") in lifespan so RuntimeError message is clear rather than raw KeyError
- session.py uses os.getenv("SECRET_KEY", "") at module level so import succeeds; lifespan's RuntimeError gives the clear error message
- Middleware placed after include_router calls per FastAPI middleware ordering semantics
- Removed passlib[bcrypt]==1.7.4; pinned bcrypt==5.0.0 directly to eliminate compatibility issues with bcrypt>=4.0
- Shared Jinja2Templates placed in dependencies.py (same file as engine/SessionLocal singletons) for consistency
- annual_cost() placed on Subscription entity as domain method — pure logic from entity fields, not route handler
- ORM defaults use lambda: datetime.now(timezone.utc) not bare datetime.now (bare callable produces naive datetimes)

## Session Log
- 2026-05-07: Phase 1 context gathered → `.planning/phases/01-foundation-security/01-CONTEXT.md`
- 2026-05-07: Phase 1 planned → 2 plans (01-01 SEC, 01-02 DEBT), verification passed
- 2026-05-07: Plan 01-01 complete — SEC-01 + SEC-02 implemented (commits 845c98f, 1c4d3ec)
- 2026-05-07: Plan 01-02 complete — DEBT-01 all 6 items resolved (commits fa359cd, 46f04ac, 6490601)
- 2026-05-07: Phase 1 code review + verification passed — 3 post-review fixes applied (commit c77cdfb); Phase 1 complete
