---
phase: 01-foundation-security
plan: 01
subsystem: infra
tags: [fastapi, logging, json-logging, security, secret-key, lifespan]

# Dependency graph
requires: []
provides:
  - Startup fails fast with RuntimeError if SECRET_KEY missing or equals dev default
  - All HTTP requests emit a structured JSON log line to stdout (method, path, status_code, duration_ms)
  - Email send failures in admin invite flow are logged with full traceback instead of silently dropped
affects: [all-phases, phase-2, phase-3, phase-4, phase-5]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JsonFormatter: stdlib logging.Formatter subclass emitting JSON to stdout"
    - "FastAPI lifespan: asynccontextmanager for startup validation before serving traffic"
    - "HTTP middleware: @app.middleware('http') for cross-cutting request logging"

key-files:
  created: []
  modified:
    - src/interfaces/web/app.py
    - src/interfaces/web/session.py
    - src/interfaces/web/routes/admin.py

key-decisions:
  - "Used os.getenv(SECRET_KEY, '') in lifespan (not os.environ) to allow graceful RuntimeError message rather than raw KeyError"
  - "Used os.environ[SECRET_KEY] in session.py as secondary safety net — KeyError if module imported before lifespan fires"
  - "Middleware placed after include_router calls per FastAPI middleware ordering semantics"
  - "JsonFormatter includes exc field only when exc_info is set, avoiding null exc in normal request logs"

patterns-established:
  - "Fail-fast startup: validate required env vars in lifespan, raise RuntimeError with clear message"
  - "Structured logging: JsonFormatter on root logger, all app loggers inherit JSON format"
  - "Exception logging: log.exception() in except blocks to capture traceback without re-raising"

requirements-completed: [SEC-01, SEC-02]

# Metrics
duration: 5min
completed: 2026-05-07
---

# Phase 1 Plan 01: Foundation & Security Summary

**Startup fails with RuntimeError on missing/insecure SECRET_KEY, and all HTTP requests emit structured JSON logs to stdout via lifespan + JsonFormatter + middleware**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-07T01:22:28Z
- **Completed:** 2026-05-07T01:27:33Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- SEC-01: App now refuses to start if SECRET_KEY is absent or equals the dev default, via RuntimeError in FastAPI lifespan
- SEC-02: Every HTTP request produces a JSON log line on stdout with method, path, status_code, duration_ms via @app.middleware("http") and JsonFormatter
- SEC-02 D-05: Both silent `except: pass` blocks in admin.py invite email handlers replaced with `log.exception(...)` capturing full tracebacks

## Task Commits

Each task was committed atomically:

1. **Task 1: Add lifespan event with SECRET_KEY validation and JSON logging init to app.py** - `845c98f` (feat)
2. **Task 2: Harden session.py SECRET_KEY read + fix admin.py silent except blocks** - `1c4d3ec` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/interfaces/web/app.py` - Added JsonFormatter class, lifespan function with SEC-01 check + logging init, @app.middleware("http") for request logging
- `src/interfaces/web/session.py` - Changed line 5 from os.getenv with fallback to os.environ["SECRET_KEY"] (no insecure default)
- `src/interfaces/web/routes/admin.py` - Added module-level logger; replaced 2 silent except blocks with log.exception calls

## Decisions Made
- Used `os.getenv("SECRET_KEY", "")` in lifespan (not `os.environ`) so the RuntimeError message is clear and actionable rather than a raw KeyError from the environment
- Used `os.environ["SECRET_KEY"]` in session.py as a secondary safety net — if session.py is imported before lifespan runs, it raises KeyError immediately
- Middleware is placed after all `app.include_router(...)` calls per FastAPI's middleware registration order (middleware wraps all routes registered before it)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Pre-existing test failures (4 tests, out of scope):** Tests in `test_create_subscription.py`, `test_subscription_entity.py`, and `test_update_subscription.py` fail because they test an `icon_emoji` field on the `Subscription` entity. Per CLAUDE.md, `icon_emoji` is "intentionally excluded from the entity — exists as DB column only for legacy data." These failures pre-existed before this plan's execution (verified by checking baseline on commit before 845c98f) and are not caused by our changes. No test files were modified in this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Foundation security hardening complete — app will refuse insecure startup
- JSON structured logging in place for all HTTP traffic; operators can pipe to journald/log aggregators
- Ready for Plan 01-02 (DEBT-01: code debt cleanup)
- Pre-existing icon_emoji test failures should be tracked for Phase 2b data model work

---
*Phase: 01-foundation-security*
*Completed: 2026-05-07*
