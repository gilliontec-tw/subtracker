# Phase 1: Foundation & Security - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate startup risk and fix all six technical debt items so every subsequent phase builds on a stable, safe codebase. No new user-facing features are delivered in this phase.

**In scope:**
- SEC-01: Raise a startup error if `SECRET_KEY` is missing or equals the dev default
- SEC-02: Add stdlib JSON structured logging to the web layer (all requests + errors); fix silent `except: pass` swallowing
- DEBT-01 (6 items): remove passlib, delete stale `session.py` schema comment, extract `annual_cost()` to domain entity, deduplicate `NOTIFICATION_OPTIONS`, consolidate `Jinja2Templates`, fix `datetime.now()` timezone-naive calls

**Out of scope:**
- Cookie `secure` flag — deferred to Phase 5 (needs nginx + HTTPS first)
- `UserRole` / `BillingCycle` enums (LOW severity, not in DEBT-01)
- Log rotation for notifications.log — Phase 5 deployment concern
- Any new user-facing functionality

</domain>

<decisions>
## Implementation Decisions

### SEC-02: Structured Logging

- **D-01:** Use **stdlib `logging`** — zero new dependencies, consistent with existing `run_notifications.py` setup.
- **D-02:** Output format: **JSON** (fields: timestamp, level, method, path, status, duration). Configure with a custom `JsonFormatter`.
- **D-03:** Scope: **all HTTP requests + errors** — one log line per request (method, path, status, duration); full traceback on unhandled exceptions.
- **D-04:** Initialize in **`app.py` lifespan event** — same location as SECRET_KEY check. Single startup configuration block.
- **D-05:** Fix the two silent `except Exception: pass` blocks in `src/interfaces/web/routes/admin.py` (lines 79–81 and 113–115) by replacing with `log.exception(...)`. This is part of SEC-02 ("errors not silently swallowed").

### Log Destination

- **D-06:** Web layer logs → **stdout only**. systemd journald captures stdout automatically; `journalctl -u subtrack` is sufficient for the successor. No file-based log for the web app.
- **D-07:** `scripts/run_notifications.py` → **keep file-based** (`logs/notifications.log`). It runs as a detached timer job; file logging is appropriate. Do NOT change it in Phase 1.

### SEC-01: SECRET_KEY Validation

- **D-08:** Check runs in **`app.py` lifespan event** (same block as logging init). Raise `RuntimeError` with a clear message if `SECRET_KEY` is not set or equals `"dev-secret-key-change-in-production"`. App refuses to start.

### DEBT-01: annual_cost() Extraction

- **D-09:** Extract `annual_cost()` as a **method on `Subscription` entity** (`src/domain/entities/subscription.py`). Billing cycle cost logic is domain behaviour — it belongs in the domain layer. Both route handlers import/call `subscription.annual_cost()` after the fix.
- **D-10:** This is done in **Phase 1** (not deferred to Phase 3). REPORT-02 in Phase 3 only needs to import the already-existing method.

### DEBT-01: Other Items

- **D-11:** Remove `passlib[bcrypt]` from `requirements.txt`; keep `bcrypt` pinned directly. No code changes needed in `hash_utils.py` (it already imports `bcrypt` directly).
- **D-12:** Delete the stale CREATE TABLE comment block at the top of `src/infrastructure/database/session.py` (lines 1–18). Replace with a one-line pointer: `# Schema defined in src/infrastructure/database/models.py`.
- **D-13:** Extract `NOTIFICATION_OPTIONS` to `src/interfaces/web/constants.py`; import in both `subscriptions.py` and `notifications.py`.
- **D-14:** Create a shared `Jinja2Templates` instance in `src/interfaces/web/dependencies.py`; remove the four per-router `templates = Jinja2Templates(...)` instantiations.
- **D-15:** Replace all `datetime.now()` with `datetime.now(timezone.utc)` (Python 3.12 compatible, preferred over deprecated `utcnow()`). Affected files: `src/infrastructure/database/sql_subscription_repository.py` (line 97), `src/infrastructure/database/models.py` (lines 35–36).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Docs
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria (6 items), requirements list
- `.planning/REQUIREMENTS.md` — SEC-01, SEC-02, DEBT-01 detailed specs

### Security (SEC-01, SEC-02)
- `src/interfaces/web/session.py` — SECRET_KEY at line 5 (hardcoded fallback); cookie settings at lines 13–17
- `src/interfaces/web/app.py` — FastAPI app entry point; lifespan event is where both SECRET_KEY check and logging init go; existing global exception handlers for NotAuthenticatedException/ForbiddenException
- `src/interfaces/web/routes/admin.py` — silent `except Exception: pass` at lines 79–81 and 113–115 (SEC-02 must fix these)

### Technical Debt (DEBT-01)
- `src/infrastructure/database/session.py` — stale schema comment lines 1–18 (delete entirely, add pointer to models.py)
- `src/infrastructure/auth/hash_utils.py` — already imports `bcrypt` directly (line 1); no code change needed
- `requirements.txt` — `passlib[bcrypt]==1.7.4` at line 11 (remove this line)
- `src/interfaces/web/routes/subscriptions.py` — `annual_cost()` at lines 55–65 and 371–381 (both to be replaced by `subscription.annual_cost()`); `NOTIFICATION_OPTIONS` at lines 22–29 (move to constants.py)
- `src/interfaces/web/routes/notifications.py` — `NOTIFICATION_OPTIONS` at lines 14–21 (second copy; import from constants.py)
- `src/domain/entities/subscription.py` — add `annual_cost()` instance method here
- `src/infrastructure/database/sql_subscription_repository.py` — `datetime.now()` at line 97 (fix to `datetime.now(timezone.utc)`)
- `src/infrastructure/database/models.py` — `datetime.now` defaults at lines 35–36 (fix to `datetime.now(timezone.utc)`)

### Codebase Maps (for broader context)
- `.planning/codebase/ARCHITECTURE.md` — Clean Architecture layers, DI patterns, anti-patterns to avoid
- `.planning/codebase/CONCERNS.md` — Full security and debt audit with exact file/line references

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/run_notifications.py` logging setup (lines 24–33): working example of Python stdlib `logging` with `FileHandler` and formatter — reference it for the `JsonFormatter` implementation pattern
- `src/interfaces/web/app.py`: already has a `@app.exception_handler` pattern for `NotAuthenticatedException` and `ForbiddenException` — the new logging middleware fits next to these handlers

### Established Patterns
- **FastAPI `Depends()`** is the DI container — `Jinja2Templates` shared instance should be exposed via `dependencies.py`, consistent with how repositories and use cases are wired
- **`src/interfaces/web/constants.py` does not exist yet** — create it fresh; this is the right home for `NOTIFICATION_OPTIONS`
- **`Subscription` entity** already has `should_notify_today()` as a domain method — `annual_cost()` follows the exact same pattern

### Integration Points
- `app.py` lifespan: add `logging.basicConfig(...)` + SECRET_KEY check here (runs at startup before any request)
- All 4 router files (`subscriptions.py`, `auth.py`, `admin.py`, `notifications.py`): remove `templates = Jinja2Templates(...)` and import shared instance from `dependencies.py`
- `subscriptions.py` lines 55–65 and 371–381: replace inline `annual_cost()` with `sub.annual_cost()` call after method is added to entity

</code_context>

<specifics>
## Specific Ideas

- JSON log format should include at minimum: `timestamp`, `level`, `method`, `path`, `status_code`, `duration_ms`. Keep it compact — successor maintainer will read these with `journalctl`.
- The SECRET_KEY error message should be specific: show what value was found (or that it was missing) and direct the user to set `SECRET_KEY` in `.env`.

</specifics>

<deferred>
## Deferred Ideas

- **Cookie `secure` flag** — Phase 5. Needs nginx + HTTPS configured first. Enabling in Phase 1 would break local HTTP dev.
- **`UserRole` enum / `BillingCycle` enum** — LOW severity items from CONCERNS.md, not in DEBT-01 scope. Could be picked up in a future debt cleanup pass.
- **Log rotation for `notifications.log`** — Phase 5. Addressed when setting up the systemd timer and deployment environment.
- **Health check endpoint (`/health`)** — v2 requirement, not in Phase 1 scope.

</deferred>

---

*Phase: 1-Foundation & Security*
*Context gathered: 2026-05-07*
