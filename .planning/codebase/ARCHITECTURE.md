<!-- refreshed: 2026-05-06 -->
# Architecture

**Analysis Date:** 2026-05-06

## System Overview

```text
┌──────────────────────────────────────────────────────────────────┐
│                    interfaces/web (FastAPI)                       │
│  routes/subscriptions.py  routes/admin.py  routes/auth.py        │
│  routes/notifications.py  app.py  dependencies.py  session.py   │
└──────────┬───────────────────────────────────────────────────────┘
           │ calls use case .execute()
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    application/use_cases/                         │
│  CreateSubscriptionUseCase  UpdateSubscriptionUseCase            │
│  DeleteSubscriptionUseCase  GetSubscriptionUseCase               │
│  ListSubscriptionsUseCase   CheckAndNotifyUseCase                │
│  auth/LoginUserUseCase  auth/RegisterUserUseCase                 │
│  auth/ChangePasswordUseCase auth/UpdateUserPermissionsUseCase    │
└──────────┬────────────────────────────────┬─────────────────────┘
           │ depends on interfaces only      │
           ▼                                 ▼
┌──────────────────┐              ┌──────────────────────────────┐
│  domain/entities │              │  application/interfaces/      │
│  Subscription    │              │  EmailSender (ABC)            │
│  User            │              └──────────┬───────────────────┘
│  AuditEntry      │                         │ implemented by
│  ConfigOption    │              ┌──────────▼───────────────────┐
└──────────────────┘              │  infrastructure/email/        │
                                  │  SmtpEmailSender              │
┌──────────────────────────────┐  └──────────────────────────────┘
│  domain/repositories/ (ABCs) │
│  SubscriptionRepository      │
│  UserRepository              │
│  AuditLogRepository          │
│  ConfigOptionRepository      │
└──────────┬───────────────────┘
           │ implemented by
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    infrastructure/database/                       │
│  SqlSubscriptionRepository  SqlUserRepository                    │
│  SqlAuditLogRepository      SqlConfigOptionRepository            │
│  models.py (SQLAlchemy ORM) session.py (engine + SessionLocal)   │
│  auth/hash_utils.py (bcrypt)                                     │
└──────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  SQL Server (pyodbc / ODBC)  │
│  Tables: saas_subscriptions  │
│          users               │
│          audit_log           │
│          config_options      │
└──────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `FastAPI app` | Mounts routers, registers exception handlers | `src/interfaces/web/app.py` |
| `dependencies.py` | Wires DB session → repositories → use cases via `Depends()` | `src/interfaces/web/dependencies.py` |
| `session.py` | Signs/reads session cookies with `itsdangerous` | `src/interfaces/web/session.py` |
| `routes/subscriptions.py` | CRUD routes, CSV export, dashboard, reports, bulk-renew | `src/interfaces/web/routes/subscriptions.py` |
| `routes/admin.py` | User management, config options (categories/departments), audit log | `src/interfaces/web/routes/admin.py` |
| `routes/auth.py` | Login/logout, password change, invite accept | `src/interfaces/web/routes/auth.py` |
| `routes/notifications.py` | Per-subscription notification settings UI | `src/interfaces/web/routes/notifications.py` |
| `Subscription` entity | Core domain object + `should_notify_today()` logic | `src/domain/entities/subscription.py` |
| `User` entity | User with role + granular permission flags | `src/domain/entities/user.py` |
| `AuditEntry` entity | Immutable record of a user action | `src/domain/entities/audit_entry.py` |
| `ConfigOption` entity | Category / department option, supports parent–child tree | `src/domain/entities/config_option.py` |
| `SubscriptionRepository` | Abstract CRUD interface for subscriptions | `src/domain/repositories/subscription_repository.py` |
| `UserRepository` | Abstract CRUD + invite-token lookup for users | `src/domain/repositories/user_repository.py` |
| `SqlSubscriptionRepository` | SQLAlchemy implementation, maps ORM ↔ domain entity | `src/infrastructure/database/sql_subscription_repository.py` |
| `SqlUserRepository` | SQLAlchemy implementation | `src/infrastructure/database/sql_user_repository.py` |
| `SqlConfigOptionRepository` | Tree-aware repo with `get_tree()` and `seed_defaults_if_empty()` | `src/infrastructure/database/sql_config_option_repository.py` |
| `SmtpEmailSender` | Implements `EmailSender` via `smtplib.SMTP_SSL` | `src/infrastructure/email/smtp_email_sender.py` |
| `hash_utils` | bcrypt `hash_password` / `verify_password` helpers | `src/infrastructure/auth/hash_utils.py` |
| `models.py` | SQLAlchemy ORM models (`SubscriptionModel`, `UserModel`, etc.) | `src/infrastructure/database/models.py` |
| `session.py` | `create_engine` + `SessionLocal` factory from env | `src/infrastructure/database/session.py` |

## Pattern Overview

**Overall:** Clean Architecture (Uncle Bob)

**Key Characteristics:**
- Dependency rule strictly enforced: domain has zero imports from outer layers; application imports only domain and its own `interfaces/`
- Repository interfaces defined in `domain/repositories/` as ABCs; implementations in `infrastructure/database/`
- `EmailSender` interface in `application/interfaces/`; implementation in `infrastructure/email/`
- Each use case is a single-method class with `execute()`
- FastAPI `Depends()` is the DI container — no separate framework needed

## Layers

**Domain:**
- Purpose: Pure business rules and entity definitions; no I/O, no framework imports
- Location: `src/domain/`
- Contains: `@dataclass` entities, `ABC` repository interfaces, domain enums (`NotificationDays`, `SubscriptionStatus`)
- Depends on: Nothing (stdlib `dataclasses`, `abc`, `datetime` only)
- Used by: Application layer

**Application:**
- Purpose: Orchestrates use cases; coordinates domain entities + repository interfaces + email interface
- Location: `src/application/`
- Contains: Use case classes (`*UseCase`), `EmailSender` ABC
- Depends on: `src/domain/` only
- Used by: `src/interfaces/web/dependencies.py`

**Infrastructure:**
- Purpose: Concrete adapters for persistence, email, password hashing
- Location: `src/infrastructure/`
- Contains: SQLAlchemy ORM models + repository implementations, `SmtpEmailSender`, bcrypt helpers
- Depends on: `src/domain/` (to return entity types), SQLAlchemy, bcrypt, smtplib
- Used by: `src/interfaces/web/dependencies.py` (injected into use cases)

**Interfaces/Web:**
- Purpose: HTTP delivery layer — receives requests, validates input, invokes use cases, renders templates
- Location: `src/interfaces/web/`
- Contains: FastAPI routers, Jinja2 template rendering, DI wiring (`dependencies.py`), session management
- Depends on: Application use cases (via `Depends()`), domain entities for type hints
- Used by: `main.py` (ASGI entry point)

## Data Flow

### Primary Request Path (Web CRUD)

1. HTTP request arrives → FastAPI matches route in `routes/subscriptions.py` (or other router)
2. `Depends()` chain in `dependencies.py` fires: `get_db_session()` yields a `Session`, `get_repo()` wraps it in `SqlSubscriptionRepository`, `get_create_uc()` wraps repo in `CreateSubscriptionUseCase`
3. Route handler calls `uc.execute(...)` with validated form data
4. Use case constructs a `Subscription` dataclass and calls `self._repo.add(entity)`
5. `SqlSubscriptionRepository.add()` maps entity → `SubscriptionModel`, calls `session.commit()`, maps back to entity
6. Route handler logs to `AuditLogRepository`, returns `RedirectResponse` or `TemplateResponse`

### Notification Job Path

1. Windows Task Scheduler runs `scripts/run_notifications.py` daily at 08:00
2. Script manually creates `SessionLocal()`, instantiates `SqlSubscriptionRepository` + `SmtpEmailSender`
3. `CheckAndNotifyUseCase.execute()` calls `repo.get_all_active()`, filters with `Subscription.should_notify_today(today)`
4. For each due subscription, collects unique recipient emails, sends one SMTP email per recipient via `SmtpEmailSender.send()`
5. Script logs results to `logs/notifications.log`

### Auth Flow — Login

1. `POST /login` → `auth.py:login_submit` → `LoginUserUseCase.execute(email, password)`
2. Use case fetches user by email, calls `verify_password(plain, hashed)` (bcrypt)
3. On success: updates `last_login_at`, returns `User`; route calls `create_session_cookie(response, user.id)`
4. Cookie is a signed URL-safe timed token containing `{"user_id": N}` (itsdangerous, 7-day expiry)

### Auth Flow — Invite (New User)

1. Admin POSTs to `/admin/users/create` → `RegisterUserUseCase.execute(email, display_name, permissions)`
2. Use case creates `User` with placeholder hashed password + `invite_token` (72 h expiry) → persisted
3. Admin route sends invite email with `{base_url}/auth/invite/{token}` link via `SmtpEmailSender`
4. New user visits link → `GET /auth/invite/{token}` → validates token, renders set_password form
5. `POST /auth/invite/{token}` → hashes new password, clears token fields, saves user

**State Management:**
- All state in SQL Server; no in-memory server state
- Session identity carried in signed HTTP cookie (`session` cookie name); user data re-fetched from DB on each request

## Key Abstractions

**Repository ABC pattern:**
- Purpose: Decouple domain/application from SQL Server specifics; enables unit testing with `MagicMock`
- Examples: `src/domain/repositories/subscription_repository.py`, `src/domain/repositories/user_repository.py`
- Pattern: ABC with `@abstractmethod`; concrete classes in `infrastructure/database/sql_*.py`

**Use Case pattern:**
- Purpose: One class per operation; single `execute()` method; injected with repository
- Examples: `src/application/use_cases/create_subscription.py`, `src/application/use_cases/auth/login_user.py`
- Pattern: Constructor takes repository interface (or email sender); `execute()` contains all business logic

**EmailSender ABC:**
- Purpose: Decouple notification logic from SMTP details; testable with `MagicMock`
- File: `src/application/interfaces/email_sender.py`
- Implementation: `src/infrastructure/email/smtp_email_sender.py`

**ORM ↔ Entity mapping:**
- Purpose: Isolate SQLAlchemy types from domain dataclasses
- Pattern: `_to_entity(model)` private method in every `Sql*Repository`; no SQLAlchemy objects ever leave infrastructure layer

## Entry Points

**Web server:**
- Location: `main.py` (project root)
- Triggers: `uvicorn` via `python main.py`
- Responsibilities: Loads `app` from `src/interfaces/web/app.py`, starts ASGI server on `APP_HOST:APP_PORT`

**Notification job:**
- Location: `scripts/run_notifications.py`
- Triggers: Windows Task Scheduler or direct `python scripts/run_notifications.py`
- Responsibilities: Bootstraps DB session + email sender, runs `CheckAndNotifyUseCase`, logs to `logs/notifications.log`

**DB seed:**
- Location: `scripts/seed_admin.py`
- Triggers: Manual one-time run after DB setup
- Responsibilities: Creates the initial admin user

## Architectural Constraints

- **Threading:** Single-process ASGI; SQLAlchemy sessions are per-request (yielded via `get_db_session()` generator, closed in `finally`)
- **Global state:** `engine` and `SessionLocal` are module-level singletons in `src/infrastructure/database/session.py`; `_serializer` is a module-level singleton in `src/interfaces/web/session.py`
- **No circular imports:** Domain imports nothing from application/infrastructure/interfaces; application imports only domain
- **DB schema:** Tables created manually via SQL DDL before first run — no Alembic migrations; schema defined in `src/infrastructure/database/models.py`
- **Legacy DB columns:** `login_password` and `icon_emoji` exist in `SubscriptionModel` but are intentionally excluded from the `Subscription` domain entity — do not surface them

## Anti-Patterns

### Direct SmtpEmailSender instantiation in route

**What happens:** `routes/admin.py` instantiates `SmtpEmailSender()` directly inside the route handler when sending invite emails, bypassing the `EmailSender` interface and `Depends()` DI system.
**Why it's wrong:** Makes the invite-email path untestable via mocks; breaks the Clean Architecture boundary (interface layer reaching into infrastructure directly).
**Do this instead:** Add a `get_email_sender` provider in `dependencies.py` and inject it via `Depends(get_email_sender)`, the same way repositories are injected.

### Business logic in route handler

**What happens:** `routes/subscriptions.py:bulk_renew` and `routes/subscriptions.py:dashboard` contain date arithmetic and cost aggregation logic inline.
**Why it's wrong:** Business logic in the delivery layer is not testable without an HTTP client; it belongs in use cases.
**Do this instead:** Extract into `application/use_cases/bulk_renew_subscription.py` and a dedicated dashboard use case.

## Error Handling

**Strategy:** Use-case layer raises `ValueError` for domain validation failures; web layer raises `NotAuthenticatedException` / `ForbiddenException` for auth errors

**Patterns:**
- `ValueError` from use cases is caught inline in route handlers and re-rendered as form errors (e.g., duplicate email on user creation)
- `NotAuthenticatedException` → global exception handler in `app.py` → `302 /login`
- `ForbiddenException` → global exception handler in `app.py` → `403 HTML response`
- Notification job catches all exceptions at the top level and calls `sys.exit(1)` on failure

## Cross-Cutting Concerns

**Logging:** `scripts/run_notifications.py` logs to `logs/notifications.log` via Python `logging`; web layer has no structured logging (unhandled errors surface as 500s)
**Validation:** Form input validated at the route layer (FastAPI `Form(...)` required params, manual `datetime.strptime`, `Decimal()` coercion); no Pydantic schemas used
**Authentication:** Signed cookie session (`itsdangerous`); checked on every protected route via `get_current_user` dependency; no JWT, no OAuth
**Audit trail:** All subscription create/update/delete/renew actions write an `AuditEntry` via `SqlAuditLogRepository.add()` directly in the route handler after the use case call

---

*Architecture analysis: 2026-05-06*
