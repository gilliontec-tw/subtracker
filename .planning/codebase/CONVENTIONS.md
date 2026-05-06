# Coding Conventions

**Analysis Date:** 2026-05-06

## Naming Patterns

**Files:**
- Python source files: `snake_case.py` throughout (e.g., `create_subscription.py`, `sql_subscription_repository.py`)
- Infrastructure repos prefixed `sql_`: `sql_subscription_repository.py`, `sql_user_repository.py`, `sql_audit_log_repository.py`, `sql_config_option_repository.py`
- Templates: `snake_case.html` in subdirectories matching logical grouping (`admin/`, `account/`, `auth/`, `notifications/`)
- Use cases grouped in subdirectory when domain-specific: `use_cases/auth/` for auth use cases, `use_cases/` root for subscription use cases

**Classes:**
- PascalCase: `CreateSubscriptionUseCase`, `SqlSubscriptionRepository`, `NotAuthenticatedException`
- Use cases follow pattern `<Verb><Noun>UseCase`: `CreateSubscriptionUseCase`, `LoginUserUseCase`, `UpdateUserPermissionsUseCase`
- Repository implementations prefixed `Sql`: `SqlSubscriptionRepository`, `SqlUserRepository`
- Exceptions end in `Exception`: `NotAuthenticatedException`, `ForbiddenException`

**Functions:**
- `snake_case` throughout: `create_form`, `edit_submit`, `get_current_user`, `require_admin`
- Private helpers prefixed `_`: `_to_entity`, `_csv_safe`, `_add_billing_period`, `_dept_options`
- Route handlers named by action+noun: `create_form`, `create_submit`, `edit_form`, `edit_submit`
- Dependency provider functions prefixed `get_`: `get_repo`, `get_user_repo`, `get_login_uc`, `get_create_uc`
- Auth guard functions prefixed `require_`: `require_admin`, `require_create`, `require_update`, `require_delete`

**Variables:**
- `snake_case` for all variables
- Module-level option lists in `UPPER_SNAKE_CASE`: `NOTIFICATION_OPTIONS`, `STATUS_OPTIONS`, `BILLING_CYCLE_OPTIONS`, `CAT_COLORS`
- Private instance attributes prefixed `_`: `self._repo`, `self._session`, `self._email_sender`

**Types/Enums:**
- Enums use PascalCase class name, UPPER_SNAKE_CASE members: `NotificationDays.SEVEN`, `SubscriptionStatus.ACTIVE`
- `NotificationDays` extends `IntEnum`, `SubscriptionStatus` extends `str, Enum` (dual inheritance for JSON serialization)

## Code Style

**Formatting:**
- No linting config file detected (no `.eslintrc`, `biome.json`, `pyproject.toml` linting section)
- Alignment padding used for visual clarity in ORM column assignments:
  ```python
  model.service_name        = subscription.service_name
  model.login_account       = subscription.login_account
  model.notification_emails = subscription.notification_emails
  ```
- Column alignment also used in `__init__` assignments within infrastructure layer

**Type Annotations:**
- Full type hints on all function signatures
- Modern union syntax: `str | None`, `date | None`, `int | None` (requires Python 3.11+)
- Return types annotated: `-> Subscription`, `-> list[Subscription]`, `-> None`
- Dependency injection parameters typed loosely (`uc=Depends(get_create_uc)`) without explicit type annotation — only the return type of the provider function matters

**Dataclasses for Entities:**
- Domain entities are `@dataclass`: `Subscription`, `User`, `AuditEntry`, `ConfigOption`
- Required fields first, optional fields with defaults (`= None`, `= False`) at end
- `id: int | None = None` pattern for all entities — None before persistence, int after

## Import Organization

**Order:**
1. Standard library (`datetime`, `decimal`, `csv`, `io`, `json`, `calendar`, `collections`)
2. Third-party (`fastapi`, `sqlalchemy`, `pydantic`)
3. Internal domain layer (`src.domain.entities.*`, `src.domain.repositories.*`)
4. Internal application layer (`src.application.use_cases.*`, `src.application.interfaces.*`)
5. Internal infrastructure layer (`src.infrastructure.*`)
6. Internal interfaces layer (`src.interfaces.web.*`)

**Notable:**
- No path aliases — all imports are full `src.*` paths
- `pyproject.toml` adds `src/` to `pythonpath` for pytest only; production code uses full paths
- Occasional lazy import inside function body (e.g., `import secrets` inside `resend_invite` in `admin.py`)

## Error Handling

**Patterns:**

- Use cases raise `ValueError` with descriptive messages for business rule violations:
  ```python
  raise ValueError("not found")           # entity lookup failures
  raise ValueError("已被使用")              # duplicate email
  raise ValueError("Invalid credentials") # auth failures
  ```
- Routes catch `ValueError` and re-render forms with inline `error` context variable:
  ```python
  except ValueError as e:
      return templates.TemplateResponse("admin/user_create.html", {
          "request": request, "error": str(e), ...
      })
  ```
- Auth exceptions (`NotAuthenticatedException`, `ForbiddenException`) are custom exception classes raised in `dependencies.py` and handled globally in `app.py` via `@app.exception_handler`
- Email failures silently swallowed with `pass` in routes (account creation must not fail on email error)
- Notification email failures logged via `print(f"[ERROR] ...")` in use case

## Template/UI Conventions

**Language:** All user-facing text is Traditional Chinese (zh-TW). Error messages, labels, and body copy are in Chinese.

**Base Template:** `src/interfaces/web/templates/base.html` — all pages extend this via Jinja2 `{% extends "base.html" %}`.

**Template Context Variables (consistent across all routes):**
- `request` — always passed (FastAPI/Jinja2 requirement)
- `current_user` — always passed for authenticated routes; used in nav for role-based display
- `error` — optional string; `None` when no error; rendered inline in form templates
- `success` — optional bool; used in `change_password.html`

**Template Directory Structure:**
```
templates/
├── base.html           # shared nav + layout
├── index.html          # subscription list
├── dashboard.html      # KPI + charts
├── create.html         # new subscription form
├── edit.html           # edit subscription form
├── reports.html        # cost reports
├── login.html          # auth — no base.html nav
├── account/
│   └── change_password.html
├── admin/
│   ├── users.html
│   ├── user_create.html
│   ├── user_edit.html
│   ├── audit_log.html
│   └── settings.html
├── auth/
│   └── set_password.html
└── notifications/
    └── settings.html
```

**Option Lists:** Defined as module-level constants in route files, not in templates or config:
- `NOTIFICATION_OPTIONS`, `STATUS_OPTIONS`, `CURRENCY_OPTIONS`, `BILLING_CYCLE_OPTIONS` in `subscriptions.py`
- Passed explicitly to template context on GET routes

## How Routes Are Organized

**Routers:**
- `src/interfaces/web/routes/subscriptions.py` — main subscription CRUD (`/`, `/dashboard`, `/subscriptions/*`, `/reports`, `/subscriptions/bulk-renew`)
- `src/interfaces/web/routes/auth.py` — session auth (`/login`, `/logout`, `/account/password`, `/auth/invite/{token}`)
- `src/interfaces/web/routes/admin.py` — admin-only (`/admin/users`, `/admin/settings`, `/admin/audit-log`)
- `src/interfaces/web/routes/notifications.py` — notification preferences
- All registered in `src/interfaces/web/app.py`

**Route Naming Convention:**
- GET form: `<noun>_form` (e.g., `create_form`, `edit_form`, `login_form`)
- POST submit: `<noun>_submit` (e.g., `create_submit`, `edit_submit`, `login_submit`)
- POST actions: verb-only or `<verb>_<noun>` (e.g., `delete`, `logout`, `bulk_renew`)

**POST/Redirect/GET Pattern:**
- All mutating routes (POST) return `RedirectResponse(url, status_code=303)` on success
- Errors re-render the form template directly (no redirect), passing `error=str(e)`

## How Dependency Injection Works

All wiring lives in `src/interfaces/web/dependencies.py`. The pattern:

```python
# 1. DB session generator (yields, auto-closes)
def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# 2. Repository factory (injects session)
def get_repo(session: Session = Depends(get_db_session)) -> SqlSubscriptionRepository:
    return SqlSubscriptionRepository(session)

# 3. Use case factory (injects repository)
def get_create_uc(repo=Depends(get_repo)) -> CreateSubscriptionUseCase:
    return CreateSubscriptionUseCase(repo)

# 4. Auth guards (inject current user)
def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise ForbiddenException()
    return user
```

Routes declare dependencies as function parameters:
```python
@router.post("/subscriptions/create")
def create_submit(
    service_name: str = Form(...),
    uc=Depends(get_create_uc),
    current_user=Depends(require_create),
    audit_repo=Depends(get_audit_log_repo),
):
```

**Note:** Each `Depends(get_db_session)` in the same request creates a separate session instance. There is no shared session per request — each repository in a route handler gets its own session.

## Common Repeated Patterns

**Use Case Constructor:**
```python
class SomeUseCase:
    def __init__(self, repo: SomeRepository) -> None:
        self._repo = repo

    def execute(self, ...) -> SomeEntity:
        ...
```

**Audit Log Entry After Every Mutating Route:**
```python
audit_repo.add(AuditEntry(
    user_id=current_user.id,
    user_email=current_user.email,
    action="create",          # "create" | "update" | "delete" | "renew"
    target_type="subscription",
    target_id=sub.id,
    target_name=sub.service_name,
))
```

**Repo `_to_entity` Pattern:**
All `Sql*Repository` classes implement a private `_to_entity(model)` method that maps the SQLAlchemy ORM model to a pure domain entity. This is the only place ORM-to-domain conversion occurs.

**`or None` Cleanup in Form Submissions:**
Empty strings from HTML forms are normalized to `None`:
```python
notes=notes or None,
owner_name=owner_name or None,
category=category or None,
```

**Optional Date Parsing:**
```python
trial_end_date=datetime.strptime(trial_end_date, "%Y-%m-%d").date() if trial_end_date else None,
```

---

*Convention analysis: 2026-05-06*
