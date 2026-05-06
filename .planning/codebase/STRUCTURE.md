# Codebase Structure

**Analysis Date:** 2026-05-06

## Directory Layout

```
saas-tracker/
├── main.py                          # ASGI entry point (uvicorn)
├── pyproject.toml                   # Project config, adds src/ to pythonpath
├── .env.example                     # Environment variable template
├── src/
│   ├── domain/                      # Pure domain — no I/O, no framework imports
│   │   ├── entities/
│   │   │   ├── subscription.py      # Subscription dataclass + NotificationDays enum + SubscriptionStatus enum
│   │   │   ├── user.py              # User dataclass (role + granular permission flags)
│   │   │   ├── audit_entry.py       # AuditEntry dataclass (immutable action record)
│   │   │   └── config_option.py     # ConfigOption dataclass (category/department, parent-child)
│   │   └── repositories/            # Abstract repository interfaces (ABCs)
│   │       ├── subscription_repository.py
│   │       ├── user_repository.py
│   │       ├── audit_log_repository.py
│   │       └── config_option_repository.py
│   ├── application/                 # Use cases + application-level interfaces
│   │   ├── interfaces/
│   │   │   └── email_sender.py      # EmailSender ABC
│   │   └── use_cases/
│   │       ├── create_subscription.py
│   │       ├── update_subscription.py
│   │       ├── delete_subscription.py
│   │       ├── get_subscription.py
│   │       ├── list_subscriptions.py
│   │       ├── check_and_notify.py  # Daily notification job use case
│   │       └── auth/
│   │           ├── login_user.py
│   │           ├── register_user.py  # Invite-based; no password param
│   │           ├── change_password.py
│   │           ├── update_user_permissions.py
│   │           └── list_users.py
│   ├── infrastructure/              # Concrete adapters (DB, email, auth utils)
│   │   ├── database/
│   │   │   ├── models.py            # SQLAlchemy ORM: SubscriptionModel, UserModel, AuditLogModel, ConfigOptionModel
│   │   │   ├── session.py           # create_engine + SessionLocal from DB_CONNECTION_STRING env var
│   │   │   ├── sql_subscription_repository.py
│   │   │   ├── sql_user_repository.py
│   │   │   ├── sql_audit_log_repository.py
│   │   │   └── sql_config_option_repository.py
│   │   ├── email/
│   │   │   └── smtp_email_sender.py # SmtpEmailSender implements EmailSender via smtplib.SMTP_SSL
│   │   └── auth/
│   │       └── hash_utils.py        # bcrypt hash_password / verify_password
│   └── interfaces/
│       └── web/
│           ├── app.py               # FastAPI app, router mounting, exception handlers
│           ├── dependencies.py      # All Depends() providers: DB sessions, repos, use cases, auth guards
│           ├── session.py           # itsdangerous cookie sign/read helpers
│           ├── routes/
│           │   ├── subscriptions.py # /, /dashboard, /reports, CRUD, CSV export, bulk-renew
│           │   ├── admin.py         # /admin/users/*, /admin/settings/*, /admin/audit-log
│           │   ├── auth.py          # /login, /logout, /account/password, /auth/invite/{token}
│           │   └── notifications.py # /notifications/settings (per-subscription notification config)
│           ├── templates/           # Jinja2 templates (zh-TW UI)
│           │   ├── base.html        # Shared layout with nav bar
│           │   ├── login.html
│           │   ├── index.html       # Subscription list
│           │   ├── dashboard.html   # Cost summary + charts
│           │   ├── create.html      # New subscription form
│           │   ├── edit.html        # Edit subscription form
│           │   ├── reports.html     # Cost analysis report
│           │   ├── account/
│           │   │   └── change_password.html
│           │   ├── admin/
│           │   │   ├── users.html
│           │   │   ├── user_create.html
│           │   │   ├── user_edit.html
│           │   │   ├── settings.html    # Category/department config options
│           │   │   └── audit_log.html
│           │   ├── auth/
│           │   │   └── set_password.html  # Invite accept / set password
│           │   └── notifications/
│           │       └── settings.html
│           └── static/              # Static assets (CSS, JS, images)
├── scripts/
│   ├── run_notifications.py         # Windows Task Scheduler entry point (daily 08:00)
│   └── seed_admin.py                # One-time admin account seed
├── tests/
│   └── unit/
│       ├── conftest.py              # Shared MagicMock fixtures
│       ├── test_create_subscription.py
│       ├── test_update_subscription.py
│       ├── test_delete_subscription.py
│       ├── test_list_subscriptions.py
│       ├── test_check_and_notify.py
│       └── auth/
│           ├── test_login_user.py
│           ├── test_register_user.py
│           └── test_change_password.py
├── logs/
│   └── notifications.log            # Written by run_notifications.py (auto-created)
├── docs/
│   └── superpowers/
│       ├── plans/                   # Phase planning documents
│       └── specs/                   # Feature specifications
├── mockups/                         # HTML design mockups
└── .planning/
    └── codebase/                    # This directory — codebase map documents
```

## Key File Locations

**Entry Points:**
- `main.py`: Starts uvicorn on `APP_HOST:APP_PORT` (default `0.0.0.0:8000`)
- `src/interfaces/web/app.py`: FastAPI `app` object; include routers here when adding new routes
- `scripts/run_notifications.py`: Daily scheduler entry point

**Configuration:**
- `.env` (from `.env.example`): `DB_CONNECTION_STRING`, `SMTP_*`, `SECRET_KEY`, `APP_HOST`, `APP_PORT`
- `pyproject.toml`: `pythonpath = ["src"]` makes `src/` importable without install
- `src/infrastructure/database/session.py`: Engine creation; the `DB_CONNECTION_STRING` must use `mssql+pyodbc:///?odbc_connect=...` format for SQL Server with backslash in server name

**Core Logic:**
- `src/domain/entities/subscription.py`: `Subscription.should_notify_today()` is the sole domain business rule
- `src/interfaces/web/dependencies.py`: Single source of truth for all dependency wiring — edit here when adding new use cases
- `src/infrastructure/database/models.py`: Authoritative DB schema definition (tables created manually from this file)

**Testing:**
- `tests/unit/conftest.py`: `MagicMock` fixtures shared across tests
- All tests under `tests/unit/` — no integration or E2E tests exist

## Naming Conventions

**Files:**
- Domain entities: `snake_case.py` matching entity name (`subscription.py`, `user.py`)
- Repository interfaces: `{entity}_repository.py` (`subscription_repository.py`)
- Infrastructure implementations: `sql_{entity}_repository.py` (`sql_subscription_repository.py`)
- Use cases: `{verb}_{noun}.py` (`create_subscription.py`, `login_user.py`)
- Routes: plural noun or topic (`subscriptions.py`, `admin.py`, `notifications.py`)

**Classes:**
- Entities: PascalCase dataclass (`Subscription`, `User`, `AuditEntry`)
- Use cases: `{Verb}{Noun}UseCase` (`CreateSubscriptionUseCase`)
- Repositories: `{Noun}Repository` for interface; `Sql{Noun}Repository` for implementation
- ORM models: `{Noun}Model` (`SubscriptionModel`, `UserModel`)

**Directories:**
- `use_cases/auth/` — auth-specific use cases are namespaced under `auth/`

## Module Dependencies (what depends on what)

```
interfaces/web  →  application/use_cases  →  domain/entities
                                          →  domain/repositories (ABCs)
                                          →  application/interfaces/email_sender (ABC)
infrastructure  →  domain/entities        (returns entity types)
infrastructure  →  domain/repositories   (implements ABCs)
infrastructure  →  application/interfaces (implements EmailSender)
```

Dependencies that must NEVER exist:
- `domain/` importing from `application/`, `infrastructure/`, or `interfaces/`
- `application/` importing from `infrastructure/` or `interfaces/`

## Where to Add New Code

**New subscription field:**
1. Add field to `Subscription` dataclass: `src/domain/entities/subscription.py`
2. Add column to `SubscriptionModel`: `src/infrastructure/database/models.py`
3. Map field in `_to_entity()` and `add()`/`update()` methods: `src/infrastructure/database/sql_subscription_repository.py`
4. Add parameter to use cases: `src/application/use_cases/create_subscription.py` and `src/application/use_cases/update_subscription.py`
5. Add form field to templates: `src/interfaces/web/templates/create.html` and `edit.html`
6. Add form parameter in route handlers: `src/interfaces/web/routes/subscriptions.py`

**New use case:**
- Implementation: `src/application/use_cases/{verb}_{noun}.py`
- Wire into DI: Add provider function in `src/interfaces/web/dependencies.py`
- Consume in route: `Depends(get_{name}_uc)` in the route handler

**New route group:**
- Router: `src/interfaces/web/routes/{topic}.py` with `router = APIRouter(prefix="/{topic}")`
- Register: `app.include_router(router)` in `src/interfaces/web/app.py`
- Templates go in: `src/interfaces/web/templates/{topic}/`

**New domain entity:**
- Entity: `src/domain/entities/{name}.py` — pure `@dataclass`, no framework imports
- Repository interface: `src/domain/repositories/{name}_repository.py` — ABC
- ORM model: add `class {Name}Model(Base)` in `src/infrastructure/database/models.py`
- Implementation: `src/infrastructure/database/sql_{name}_repository.py`
- Wire: add `get_{name}_repo` provider in `src/interfaces/web/dependencies.py`

**New admin feature:**
- Route: add to `src/interfaces/web/routes/admin.py` (prefix `/admin`)
- Template: `src/interfaces/web/templates/admin/{feature}.html`
- Guard with `Depends(require_admin)` on all admin routes

**Tests:**
- All unit tests: `tests/unit/test_{use_case_name}.py`
- Auth use case tests: `tests/unit/auth/test_{use_case_name}.py`
- Use `MagicMock` for repositories; no database required

## Special Directories

**`.planning/codebase/`:**
- Purpose: Architecture and structure reference documents for GSD tooling
- Generated: By codebase mapper agent
- Committed: Yes

**`logs/`:**
- Purpose: Notification job log output
- Generated: Runtime (auto-created by `run_notifications.py`)
- Committed: No (should be in `.gitignore`)

**`.worktrees/`:**
- Purpose: Git worktrees for parallel feature branches (`feature-auth`, `phase2b`)
- Generated: Yes (git worktree add)
- Committed: No

**`mockups/`:**
- Purpose: Standalone HTML design prototypes
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-05-06*
