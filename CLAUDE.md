# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**SubTrack** — internal SaaS subscription tracker for corporate use. Tracks renewal dates, costs, billing cycles, responsible departments, and sends email notifications before expiry.

## Rule
Do not make any changes until you have 95% confidence in what you need to build. Ask me follow-up questions until you reach that confidence level.

## Commands

All backend commands run from `backend/` with the venv active (`. .venv/bin/activate` on Linux).

```bash
# Run the backend API server (development)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_create_subscription.py

# Run a specific test
pytest tests/unit/test_create_subscription.py::test_function_name

# Lint
ruff check src/
black --check src/

# Seed the initial admin account (run once after DB setup)
python scripts/seed_admin.py

# Run the notification job manually (normally scheduled via cron, daily 08:00)
python scripts/run_notifications.py
```

Frontend runs from `frontend/`:

```bash
npm run dev       # dev server on :5173
npm run build     # TypeScript check + Vite build
npm run lint      # ESLint
npx tsc --noEmit  # type-check only
```

## Environment Setup

Copy `backend/.env.example` to `backend/.env`. Required variables:

- `DATABASE_URL` — PostgreSQL via asyncpg, e.g. `postgresql+asyncpg://user:pass@localhost:5432/subtrack`
- `REDIS_URL` — e.g. `redis://localhost:6379/0` (used for login rate-limiting and refresh token blacklist)
- `JWT_ACCESS_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY` — sign JWT tokens
- `CORS_ORIGINS` — comma-separated list, e.g. `http://localhost:5173`
- `SMTP_*` — SMTP credentials for renewal notification emails
- `APP_ENV` — `development` enables `/api/docs`; anything else disables it

DB tables must be created before first run. Schema is defined in `backend/src/infrastructure/database/models.py` — tables: `users`, `saas_subscriptions`, `payment_records`, `audit_log`.

## Architecture

### Backend — Clean Architecture

```
backend/src/
  domain/           → entities (dataclasses) + repository interfaces; zero dependencies
  application/      → use cases + email sender interface; depends on domain only
  infrastructure/   → SQLAlchemy async repos, SMTP sender, bcrypt, JWT service, Redis client
  api/              → FastAPI app, routers, Pydantic schemas, exception handlers, CSRF middleware
```

**Request flow:** Router → `api/dependencies.py` auth guard (via `Depends`) → use case → repository interface → `Sql*Repository` → PostgreSQL.

**Adding a feature:** entity field in `domain/entities/` → method in `domain/repositories/` + `infrastructure/database/repositories/` → use case in `application/use_cases/` → Pydantic schemas in `api/v1/schemas/` → router in `api/v1/routers/` → register router in `api/main.py`.

**API response envelope:** All endpoints return `ApiResponse[T]` from `api/v1/schemas/base.py`:
```json
{ "success": true, "data": ..., "message": "", "meta": null }
```

### Auth

JWT stored in httponly cookies (`access_token` 30 min, `refresh_token` 7 days) + a readable `csrf_token` cookie. The frontend reads `csrf_token` and sends it as `X-CSRF-Token` on every mutating request (handled by the axios client interceptor). CSRF middleware validates this double-submit pattern.

`api/dependencies.py` provides auth guards used with `Depends()`:
- `get_current_user` — any active user
- `require_admin` — `role == "admin"`, returns the user object
- `require_can_create/update/delete` — admin or granular `can_*` flag

User registration is invite-based: admin creates user → `CreateUserUseCase` generates a UUID4 invite token (7-day expiry) stored on the user row → frontend constructs `${window.location.origin}/invite/${token}` and shares it → user sets password via the public `/invite/:token` page.

`NotAuthenticatedException` → 401 JSON; `ForbiddenException` → 403 JSON.

### Frontend

React 19 SPA (Vite, TypeScript, Tailwind CSS v4). All API calls go through `frontend/src/api/client.ts` (axios, `withCredentials: true`, auto-injects `X-CSRF-Token`).

State: TanStack Query v5 for server state, Zustand (`useAuthStore`) for current user.

Forms: `react-hook-form` + `zodResolver`. Wire `Select` fields via `setValue(field, value, { shouldValidate: true })`. No shadcn `Form`/`FormField` wrappers — build a local `Field` wrapper instead (see existing modals for the pattern).

**Available shadcn/ui components:** `Button`, `Input`, `Badge`, `Table/*`, `Dialog/*`, `Select/*`, `Card/*`, `Toaster`. No `RadioGroup`, `Switch`, or `AlertDialog` — use `Select` for toggles.

Toast: `useToast` from `@/hooks/use-toast`, call `toast({ title, variant })`.

Cache invalidation: `queryClient.invalidateQueries({ queryKey: ['key'] })` after mutations.

### Subscription Entity Fields

Core: `service_name`, `login_account`, `expiry_date`, `notification_emails`, `notification_days`

Optional: `cost`, `currency` (default TWD), `exchange_rate`, `notes`, `owner_name`, `category`, `department`, `billing_cycle` (monthly/quarterly/semi_annual/annual/biennial), `payment_account`, `auto_renew`, `trial_end_date`, `next_billing_date`, `status` (active/renewed/cancelled/suspended)

Soft-delete via `deleted_at` column (NULL = not deleted).

### Tests

All tests are pure unit tests using `MagicMock`/`AsyncMock` against repository/email-sender interfaces — no database or Redis required. Shared helpers live in `tests/unit/helpers.py`. `pyproject.toml` sets `pythonpath = ["src"]` so imports work without install.

### Notifications

`scripts/run_notifications.py` is the cron entry point (daily 08:00 on the Linux server). Calls `CheckAndNotifyUseCase` → checks `Subscription.should_notify_today()` for each active subscription → sends SMTP email.
