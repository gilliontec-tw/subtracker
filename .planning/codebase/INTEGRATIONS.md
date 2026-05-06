# External Integrations

**Analysis Date:** 2026-05-06

## APIs & External Services

No third-party cloud APIs or SaaS SDKs are used. All integrations are self-hosted or protocol-based.

## Data Storage

**Databases:**
- Microsoft SQL Server (via ODBC Driver 17 for SQL Server)
  - Connection env var: `DB_CONNECTION_STRING`
  - Format: `mssql+pyodbc:///?odbc_connect=DRIVER={ODBC Driver 17 for SQL Server};Server=...;Database=subtrack;...`
  - Client: SQLAlchemy 2.0 ORM (`src/infrastructure/database/session.py`)
  - Session factory: `SessionLocal` (autocommit=False, autoflush=False)
  - Engine created at module import time; fails fast if `DB_CONNECTION_STRING` is missing

**Tables (defined in `src/infrastructure/database/models.py`):**
- `saas_subscriptions` — subscription records
- `users` — user accounts with invite tokens and permission flags
- `audit_log` — create/update/delete action log
- `config_options` — admin-managed category and department lookup values

**File Storage:**
- Local filesystem only (`src/interfaces/web/static/` mounted at `/static`)

**Caching:**
- None

## Authentication & Identity

**Auth Provider:** Custom, self-hosted (no OAuth, no external identity provider)

- Implementation: signed session cookies via `itsdangerous.URLSafeTimedSerializer`
- Secret key env var: `SECRET_KEY` (defaults to `"dev-secret-key-change-in-production"` — must be overridden in production)
- Cookie name: `session`, 7-day TTL, `httponly=True`, `samesite="lax"`
- Session logic: `src/interfaces/web/session.py`
- Password hashing: bcrypt via `passlib[bcrypt]` in `src/infrastructure/auth/hash_utils.py`
- User registration: invite-based — admin creates user, system issues invite token stored in `users.invite_token` column

## Email / Notifications

**Provider:** Direct SMTP (stdlib `smtplib`), no third-party email service

- Implementation: `src/infrastructure/email/smtp_email_sender.py`
- Protocol: SMTP_SSL (port 465 by default)
- Required env vars:
  - `SMTP_HOST` — SMTP server hostname
  - `SMTP_PORT` — SMTP port (default `465` in `.env.example`)
  - `SMTP_USERNAME` — SMTP login username
  - `SMTP_PASSWORD` — SMTP login password
  - `SMTP_FROM` — From address in sent emails
- Trigger: `scripts/run_notifications.py` → `CheckAndNotifyUseCase` → `SmtpEmailSender.send()`
- Scheduling: Windows Task Scheduler (daily 08:00); Linux crontab also documented in `scripts/run_notifications.py`
- Log output: `logs/notifications.log` (created automatically on first run)

## Monitoring & Observability

**Error Tracking:** None (no Sentry or equivalent)

**Logs:**
- Notification job: file logger at `logs/notifications.log` + stdout (`logging.basicConfig` in `scripts/run_notifications.py`)
- Web app: no structured logging configured; FastAPI/Uvicorn default stdout logging only

## CI/CD & Deployment

**Hosting:** Self-hosted Windows server (primary deployment target)

**CI Pipeline:** None detected (no GitHub Actions, no CI config files)

**Process management:** Direct `python main.py` invocation; no process manager (e.g., systemd, PM2, Supervisor) configured

## Webhooks & Callbacks

**Incoming:** None

**Outgoing:** None

## Environment Configuration

**Required env vars:**
- `DB_CONNECTION_STRING` — full ODBC connect string for SQL Server
- `SMTP_HOST` — SMTP server
- `SMTP_PORT` — SMTP port (typically `465`)
- `SMTP_USERNAME` — SMTP auth username
- `SMTP_PASSWORD` — SMTP auth password
- `SMTP_FROM` — sender email address
- `SECRET_KEY` — session signing key (must be set in production)

**Optional env vars:**
- `APP_HOST` — bind host (default `0.0.0.0`)
- `APP_PORT` — bind port (default `8000`)

**Secrets location:**
- `.env` file at project root (not committed; `.env.example` is the template)

---

*Integration audit: 2026-05-06*
