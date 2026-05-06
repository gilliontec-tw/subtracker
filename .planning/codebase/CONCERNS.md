# Codebase Concerns

**Analysis Date:** 2026-05-06

---

## Security Considerations

**[HIGH] Session cookie missing `secure` flag:**
- Risk: Session cookies are set without `secure=True`, meaning they can be transmitted over plain HTTP. On an internal LAN this is low risk, but if the app is ever exposed over HTTP the cookie is visible in transit.
- Files: `src/interfaces/web/session.py` line 13–17
- Current mitigation: `httponly=True`, `samesite="lax"` are set; `secure` is absent.
- Recommendation: Add `secure=True` to `set_cookie()` and enforce HTTPS at the reverse-proxy level if the app is ever accessible outside the LAN.

**[HIGH] Hardcoded insecure default SECRET_KEY:**
- Risk: `_SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")` — if the `.env` file is missing or `SECRET_KEY` is not set, all session cookies are signed with a known public string. An attacker can forge arbitrary session tokens.
- Files: `src/interfaces/web/session.py` line 5
- Current mitigation: None. The default value is self-documenting but silently unsafe at runtime.
- Recommendation: Raise a startup error if `SECRET_KEY` is not set or matches the known dev string.

**[MEDIUM] No email address validation on `notification_emails`:**
- Risk: The `notification_emails` field is a free-form comma-separated string with no validation at form submission, use-case, or entity level. Malformed values silently fail during SMTP send.
- Files: `src/interfaces/web/routes/subscriptions.py` lines 228, 304; `src/application/use_cases/check_and_notify.py` line 25
- Recommendation: Validate each email segment against a basic RFC pattern in the use case or entity.

**[MEDIUM] Invite token exposed in redirect URL:**
- Risk: After user creation, the admin is redirected to `/admin/users?invited=1`. The invite token itself lives in the DB and is only sent by email, which is correct. However, the token is passed directly as a URL path segment (`/auth/invite/{token}`), meaning it appears in server access logs in plain text.
- Files: `src/interfaces/web/routes/admin.py` lines 65–66, 109
- Current mitigation: Token has a 72-hour TTL; cleared after first use.
- Recommendation: Acceptable for internal use; document that access logs should be protected.

**[LOW] `passlib[bcrypt]` declared but raw `bcrypt` imported:**
- Risk: `requirements.txt` pins `passlib[bcrypt]==1.7.4` but `src/infrastructure/auth/hash_utils.py` imports `bcrypt` directly, bypassing passlib's abstraction layer. `passlib` is unused. Passlib 1.7.4 has known deprecation warnings with bcrypt >= 4.0 and may generate `AttributeError: module 'bcrypt' has no attribute '__about__'` at runtime.
- Files: `src/infrastructure/auth/hash_utils.py` line 1; `requirements.txt` line 11
- Recommendation: Either remove `passlib` and pin `bcrypt` directly, or switch to `passlib.hash.bcrypt`.

**[LOW] No CSRF protection on state-mutating POST routes:**
- Risk: All forms use plain HTML `<form method="POST">` without CSRF tokens. On an internal LAN with session cookies, a malicious page opened by an authenticated user could trigger cross-site actions (delete subscription, change password, etc.).
- Files: All POST routes in `src/interfaces/web/routes/`
- Current mitigation: `samesite="lax"` on the cookie blocks cross-origin navigation-triggered POSTs in modern browsers; this is meaningful mitigation.
- Recommendation: Acceptable for an internal-only LAN tool. Document explicitly if exposure widens.

---

## Technical Debt

**[HIGH] Schema comment in `session.py` is stale and wrong:**
- The comment block at the top of `src/infrastructure/database/session.py` (lines 1–17) documents a CREATE TABLE script for `saas_subscriptions` that is severely out of date. It references `responsible_person_email` (old column name replaced by `notification_emails`) and is missing all columns added since Phase 1 (status, cost, currency, notes, owner_name, category, department, billing_cycle, payment_account, auto_renew, trial_end_date, next_billing_date, icon_emoji, login_password). The actual schema source of truth is `src/infrastructure/database/models.py`.
- Files: `src/infrastructure/database/session.py` lines 1–18
- Impact: A developer following this comment will create a broken schema. Very high confusion risk for new maintainers.
- Fix: Delete the comment block entirely or replace with a pointer to `models.py`.

**[MEDIUM] `annual_cost()` helper is duplicated across two routes:**
- The identical `annual_cost(s)` function is defined twice: once inside `dashboard()` and once inside `reports()` in `src/interfaces/web/routes/subscriptions.py` (lines 55–65 and lines 371–381).
- Files: `src/interfaces/web/routes/subscriptions.py`
- Impact: Any future change to billing cycle multipliers must be made in both places; easy to miss.
- Fix: Extract to a module-level helper or a utility function in `src/domain/entities/subscription.py`.

**[MEDIUM] `NOTIFICATION_OPTIONS` duplicated across two routers:**
- The list `NOTIFICATION_OPTIONS` is defined identically in both `src/interfaces/web/routes/subscriptions.py` (lines 22–29) and `src/interfaces/web/routes/notifications.py` (lines 14–21).
- Files: as above
- Fix: Define once in a shared constants module (e.g., `src/interfaces/web/constants.py`) and import.

**[MEDIUM] `Jinja2Templates` instantiated once per router module:**
- `templates = Jinja2Templates(directory="src/interfaces/web/templates")` appears in four router files (`subscriptions.py`, `auth.py`, `admin.py`, `notifications.py`). Jinja2 does lightweight caching internally, but this is boilerplate coupling the template directory path across multiple files.
- Files: all four router modules
- Fix: Create a shared `templates` instance in `src/interfaces/web/dependencies.py` or a separate `src/interfaces/web/templates_config.py` and import.

**[MEDIUM] `datetime.now()` used for timestamps (timezone-naive):**
- `src/infrastructure/database/sql_subscription_repository.py` line 97 and `src/infrastructure/database/models.py` lines 35–36 use `datetime.now()` (local time, timezone-naive). SQL Server stores `DATETIME2` without timezone info. If the server is ever moved or runs under a different timezone, historical timestamps will be silently wrong.
- Files: `src/infrastructure/database/sql_subscription_repository.py`; `src/infrastructure/database/models.py`
- Fix: Use `datetime.utcnow()` consistently or upgrade to `datetime.now(timezone.utc)`.

**[LOW] `role` field on `User` is a freeform string with no enum:**
- The `role` field in `src/domain/entities/user.py` is typed as `str` and compared with `== "admin"` in three guard functions. There is no `UserRole` enum to prevent typos.
- Files: `src/domain/entities/user.py` line 10; `src/interfaces/web/dependencies.py` lines 111, 117, 122, 128
- Fix: Add a `UserRole(str, Enum)` similar to `SubscriptionStatus`.

**[LOW] `billing_cycle` is a freeform string with no enum:**
- The `billing_cycle` field on `Subscription` is typed as `str | None` but valid values (`"monthly"`, `"quarterly"`, `"semi_annual"`, `"annual"`, `"biennial"`) are scattered across route constants, templates, and the `annual_cost()` helper. No validation prevents invalid values from being stored.
- Files: `src/domain/entities/subscription.py` line 39; `src/interfaces/web/routes/subscriptions.py` lines 41–47
- Fix: Add a `BillingCycle(str, Enum)` to `subscription.py`.

---

## Incomplete / In-Progress Features

**[HIGH] `icon_emoji` field is a structural orphan:**
- The `icon_emoji` column exists in `src/infrastructure/database/models.py` (line 33) and in the Phase 2B plan document. However, it was **not** added to the `Subscription` entity in `src/domain/entities/subscription.py`, is not mapped in `src/infrastructure/database/sql_subscription_repository.py` `_to_entity` / `add` / `update`, is not accepted by `CreateSubscriptionUseCase` or `UpdateSubscriptionUseCase`, and is not rendered in any template. The DB column exists but the field is unreachable from application code.
- Files: `src/infrastructure/database/models.py` line 33; `src/domain/entities/subscription.py` (missing); `src/infrastructure/database/sql_subscription_repository.py` (missing); use cases (missing)
- Impact: Any data stored in `icon_emoji` via direct SQL is silently dropped on every update. Phase 2B tasks 1, 4, 5, 6, 7 in the plan document are incomplete.
- Fix: Complete Phase 2B task sequence per `docs/superpowers/plans/2026-04-30-phase2b-data-model-extensions.md`.

**[HIGH] `login_password` column exists in DB but is intentionally dead:**
- `src/infrastructure/database/models.py` line 34 defines `login_password = Column(String(500), nullable=True)` described in CLAUDE.md as "exists as DB column only for legacy data but not surfaced in the application." Storing passwords (even service/SaaS account passwords) in plain text in the DB is a security risk, even if the field is currently unused in code.
- Files: `src/infrastructure/database/models.py` line 34
- Impact: If a future developer mistakenly surfaces this field, plaintext credentials could be exposed.
- Recommendation: Either add a DB migration to drop the column, or document clearly that the column must never be populated through the application.

**[MEDIUM] Reports page only renders chart for first currency (`first_cats`):**
- In `src/interfaces/web/routes/subscriptions.py` lines 417–425, the chart data (`cat_labels_json`, `cat_values_json`) is derived only from `sections[0]["categories"]` — the highest-cost currency. If the organization has subscriptions in multiple currencies, only the first one gets a pie chart; others get a table but no chart.
- Files: `src/interfaces/web/routes/subscriptions.py` lines 417–425; `src/interfaces/web/templates/reports.html`
- Impact: Multi-currency visibility is incomplete.

**[MEDIUM] Bulk-renew silently drops `payment_account`, `auto_renew`, `trial_end_date`, `next_billing_date` fields:**
- The `bulk_renew` POST handler in `src/interfaces/web/routes/subscriptions.py` (lines 429–467) calls `uc.execute(...)` without passing `payment_account`, `auto_renew`, `trial_end_date`, or `next_billing_date`. These fields will be reset to their defaults on every bulk renew operation.
- Files: `src/interfaces/web/routes/subscriptions.py` lines 443–458
- Impact: Data loss for Phase 2B fields on bulk renew.

**[MEDIUM] Notification settings page allows saving with empty `notification_emails`:**
- In `src/interfaces/web/routes/notifications.py` lines 65–67, if a subscription's "enabled" toggle is unchecked, `emails` is set to `""` and saved. An empty string is stored as `notification_emails` in the DB. The `check_and_notify` use case then calls `"".split(",")` which produces `[""]`, and `SmtpEmailSender.send()` will attempt delivery to an empty recipient — this will likely raise an SMTP error that is silently caught per-recipient.
- Files: `src/interfaces/web/routes/notifications.py` lines 65–67; `src/application/use_cases/check_and_notify.py` lines 25–29

**[LOW] `resend-invite` route imports `secrets` and `datetime` inside the function body:**
- `src/interfaces/web/routes/admin.py` lines 92–93 perform `import secrets` and `from datetime import datetime, timedelta` inside a route function. These are also inlined as `from src.infrastructure.email.smtp_email_sender import SmtpEmailSender` on line 103. This pattern is non-standard and increases first-call latency marginally.
- Files: `src/interfaces/web/routes/admin.py` lines 92–93, 103
- Fix: Move imports to the module top level.

---

## Operational Concerns

**[HIGH] No application-level structured logging:**
- The web application has no logging at all — no request logging, no error logging, no audit trail at the infrastructure layer. Only the notification script (`scripts/run_notifications.py`) uses Python `logging`. Errors surface only as HTTP 500 responses with FastAPI's default JSON error bodies.
- Files: all route files under `src/interfaces/web/routes/`
- Impact: Silent failures in production are invisible. An SMTP send error in `admin.py` line 80 is swallowed with bare `except Exception: pass`.
- Fix: Add a logging middleware in `src/interfaces/web/app.py` and replace silent `except: pass` with `log.exception(...)`.

**[MEDIUM] Email send failure on invite is silently swallowed:**
- In `src/interfaces/web/routes/admin.py` lines 79–81, SMTP send failure during user invite is caught with `except Exception: pass`. The admin has no indication that the email was not delivered. The user cannot log in without the invite link.
- Files: `src/interfaces/web/routes/admin.py` lines 79–81, 113–115
- Fix: Catch the exception and display a warning message in the redirect (e.g., via a query param `?email_failed=1`).

**[MEDIUM] No health-check endpoint:**
- There is no `/health` or `/ping` endpoint. Windows Task Scheduler running `run_notifications.py` does not verify the web service is healthy. An external monitoring check or uptime tool cannot probe the service.
- Files: `src/interfaces/web/app.py`
- Fix: Add a `@app.get("/health")` returning `{"status": "ok"}`.

**[LOW] Notification job only fires on exact trigger day:**
- `Subscription.should_notify_today()` in `src/domain/entities/subscription.py` line 47–49 checks `today == trigger` (strict equality). If the Windows Task Scheduler job misses a day (machine offline, task failure), that notification window is permanently lost with no catch-up mechanism.
- Files: `src/domain/entities/subscription.py` lines 47–49
- Recommendation: Consider `today >= trigger and today <= expiry_date` or a "last notified" column to allow catch-up.

**[LOW] Log file rotation not configured:**
- `scripts/run_notifications.py` writes to `logs/notifications.log` using a plain `FileHandler`. On a long-running deployment this file grows indefinitely.
- Files: `scripts/run_notifications.py` lines 24–33
- Fix: Replace `FileHandler` with `RotatingFileHandler` from `logging.handlers`.

---

## Data Model Concerns

**[MEDIUM] No DB migration tooling (Alembic absent):**
- The project has no migration framework. Schema changes require manual SQL execution in SSMS and a matching ORM change in `src/infrastructure/database/models.py`. There is no record of applied migrations. The comment-based schema in `session.py` is the only historical reference and it is already stale.
- Files: `src/infrastructure/database/session.py`; `src/infrastructure/database/models.py`
- Impact: Schema drift between environments is undetectable. A developer setting up a fresh DB must reconstruct the schema from models.py alone.
- Fix: Introduce Alembic for migration tracking. At minimum, maintain a `schema.sql` file that always reflects the current full schema.

**[MEDIUM] `ConfigOptionModel` has no foreign key constraint on `parent_id`:**
- `src/infrastructure/database/models.py` line 63 defines `parent_id = Column(Integer, nullable=True)` with no `ForeignKey("config_options.id")`. Deleting a parent config option cascades in application code (`sql_config_option_repository.py` lines 77–80) but there is no DB-level enforcement. Direct DB edits or future bugs could leave orphaned child rows.
- Files: `src/infrastructure/database/models.py` line 63
- Fix: Add `ForeignKey("config_options.id", ondelete="CASCADE")`.

**[MEDIUM] `AuditLogModel` has no foreign key on `user_id`:**
- `src/infrastructure/database/models.py` line 72 stores `user_id` without a FK to the `users` table. Deleting a user (`sql_user_repository.py` line 73) leaves orphaned audit log rows with a dangling `user_id`.
- Files: `src/infrastructure/database/models.py` line 72; `src/infrastructure/database/sql_user_repository.py` lines 73–77
- Fix: Either add a FK with `ON DELETE SET NULL` or prevent hard-deletes of users (soft-delete only).

**[LOW] `notification_emails` stored as a raw comma-separated string:**
- The `notification_emails` field is stored as a single `NVARCHAR(1000)` string with no structural validation. Maximum of 1000 chars limits the number of recipients. Parsing and deduplication happens at notification send time.
- Files: `src/domain/entities/subscription.py` line 28; `src/infrastructure/database/models.py` line 18
- Impact: Low risk for current use; would need a join table if recipient counts grow significantly.

---

## Scalability Limits

**[LOW] All subscriptions loaded into memory for every list/dashboard/report request:**
- `ListSubscriptionsUseCase.execute()` fetches all subscriptions on every page load. Currently called by the index page, dashboard, reports page, bulk-renew, notification settings, and CSV export — all without filtering or pagination at the DB level.
- Files: `src/application/use_cases/list_subscriptions.py`; `src/infrastructure/database/sql_subscription_repository.py` lines 67–74
- Impact: At typical corporate scale (100–500 subscriptions) this is fine. At 10,000+ rows this becomes noticeable.
- Fix: Add query-level filtering and pagination to `get_all_active()` if the dataset grows.

---

## Missing Features Implied by Architecture

**[MEDIUM] No "search" or filter at the repository layer:**
- The index page implements client-side JS filtering (`applyFilters()`) over all subscriptions rendered into the DOM. There is no server-side search or filter capability. For large datasets the DOM will become unwieldy.
- Files: `src/interfaces/web/templates/index.html` lines 40–48; `src/domain/repositories/subscription_repository.py`

**[MEDIUM] No password complexity enforcement:**
- The change-password flow in `src/interfaces/web/routes/auth.py` does not validate password complexity — only minimum length (8 chars, enforced via HTML `minlength` on the invite form; not enforced in the change-password route at all). The change-password route at lines 55–88 passes the new password directly to the use case with no length check.
- Files: `src/interfaces/web/routes/auth.py` lines 55–88

**[LOW] No "forgot password" or admin-reset flow:**
- There is no way for a user to recover their account if they forget their password other than having an admin delete and recreate the account (losing the original user's history).
- Files: `src/interfaces/web/routes/auth.py`; `src/interfaces/web/routes/admin.py`

---

## Git Status / In-Progress Work

The working tree has significant uncommitted changes across nearly all source files. Key observations:

- **Phase 2B is partially implemented but not committed.** `icon_emoji` is in the ORM model but missing from the entity, repository, use cases, and templates. The plan document (`docs/superpowers/plans/2026-04-30-phase2b-data-model-extensions.md`) tracks remaining tasks with `- [ ]` checkboxes.

- **New untracked files not yet wired into the app:**
  - `src/domain/entities/config_option.py` — untracked but already imported by `admin.py`
  - `src/domain/repositories/config_option_repository.py` — untracked
  - `src/infrastructure/database/sql_config_option_repository.py` — untracked
  - `src/interfaces/web/routes/notifications.py` — untracked but already included in `app.py`
  - `src/interfaces/web/static/style.css` — untracked; referenced by `app.py` StaticFiles mount
  - Templates: `auth/set_password.html`, `notifications/settings.html`, `admin/settings.html`, `reports.html` — all untracked but referenced by routes

- **Three old plan docs deleted** (`docs/superpowers/plans/2026-04-17-*`, `2026-04-20-*`, `2026-04-23-*`) — these were historical implementation plans that have already been executed.

- **A design mockup file** (`SaaS Tracker Redesign v3 _standalone_.html`) sits in the project root untracked — this is a standalone HTML prototype, likely for the visual redesign described in `docs/superpowers/specs/2026-05-04-visual-redesign-reports-notifications-design.md`.

---

*Concerns audit: 2026-05-06*
