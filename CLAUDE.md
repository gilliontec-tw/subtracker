# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
python main.py

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_create_subscription.py

# Run a specific test
pytest tests/unit/test_create_subscription.py::test_function_name

# Seed the initial admin account (run once after DB setup)
python scripts/seed_admin.py

# Run the notification job manually (normally scheduled via Windows Task Scheduler)
python scripts/run_notifications.py
```

## Environment Setup

Copy `.env.example` to `.env` and configure:
- `DB_CONNECTION_STRING` — SQL Server via pyodbc (Windows Auth or SQL Auth)
- `SMTP_*` — Gmail SMTP for renewal notifications
- `SECRET_KEY` — signs session cookies (defaults to insecure dev key)
- `APP_HOST` / `APP_PORT` — defaults to `0.0.0.0:8000`

SQL Server tables must be created manually before first run. The schema is defined in `src/infrastructure/database/models.py` (SQLAlchemy models) — tables: `saas_subscriptions`, `users`, `audit_log`.

## Architecture

Clean Architecture with four layers:

```
src/domain/          → entities + repository interfaces (no dependencies)
src/application/     → use cases + email sender interface (depends on domain only)
src/infrastructure/  → SQLAlchemy repos, SMTP, auth hash utils, DB session
src/interfaces/web/  → FastAPI routers, Jinja2 templates, DI wiring
```

**Request flow:** FastAPI route → `dependencies.py` wires use case via `Depends()` → use case calls repository interface → `Sql*Repository` hits SQL Server.

**Adding a new feature** typically means: entity field in `domain/entities/` → repo method in `domain/repositories/` + `infrastructure/database/sql_*_repository.py` → use case in `application/use_cases/` → route + template in `interfaces/web/`.

### Auth & Permissions

Session auth uses signed cookies (`itsdangerous`, 7-day expiry). `dependencies.py` provides four guards:
- `get_current_user` — any logged-in user
- `require_admin` — `role == "admin"`
- `require_create/update/delete` — admin OR granular `can_*` flag on the user row

`NotAuthenticatedException` → redirect to `/login`; `ForbiddenException` → 403 HTML response.

### Tests

All tests are pure unit tests using `MagicMock` against repository/email-sender interfaces — no database required. Fixtures live in `tests/conftest.py`. `pyproject.toml` adds `src/` to the Python path so imports work without install.

### Notifications

`scripts/run_notifications.py` is the Windows Task Scheduler entry point (daily 08:00). It calls `CheckAndNotifyUseCase` which checks `Subscription.should_notify_today()` for each active subscription and sends SMTP email if triggered.

### Templates & UI

Jinja2 templates in `src/interfaces/web/templates/`. The app is server-side rendered — no frontend build step. The UI is in Traditional Chinese (zh-TW).
