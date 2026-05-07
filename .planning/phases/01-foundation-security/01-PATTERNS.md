# Phase 1: Foundation & Security - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 13 (11 modified, 1 created, 1 read-only verify)
**Analogs found:** 13 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/interfaces/web/app.py` | app entry point | request-response | `scripts/run_notifications.py` (logging init pattern) | partial |
| `src/interfaces/web/session.py` | config/auth utility | request-response | itself (line 5 fix only) | self |
| `src/infrastructure/database/session.py` | config/infra | — | itself (comment deletion only) | self |
| `src/infrastructure/auth/hash_utils.py` | utility | — | itself (read-only verify) | self |
| `requirements.txt` | config | — | itself (line deletion only) | self |
| `src/interfaces/web/routes/subscriptions.py` | route/controller | request-response | itself (targeted removals) | self |
| `src/interfaces/web/routes/notifications.py` | route/controller | request-response | itself (targeted removal + import) | self |
| `src/interfaces/web/routes/admin.py` | route/controller | request-response | itself (except-block fix) | self |
| `src/domain/entities/subscription.py` | domain entity | transform | `should_notify_today()` method in same file | exact |
| `src/infrastructure/database/sql_subscription_repository.py` | infrastructure/repo | CRUD | itself (`datetime.now()` fix at line 97) | self |
| `src/infrastructure/database/models.py` | infrastructure/ORM | CRUD | itself (`datetime.now` default fix lines 35–36) | self |
| `src/interfaces/web/dependencies.py` | DI wiring | request-response | itself (add `Jinja2Templates` instance) | self |
| `src/interfaces/web/constants.py` (NEW) | constants module | — | `NOTIFICATION_OPTIONS` block in `subscriptions.py` lines 22–29 | exact |

---

## Pattern Assignments

### `src/interfaces/web/app.py` (app entry point — add lifespan, logging, SECRET_KEY check)

**Current state** (lines 1–31 — full file):
```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from src.interfaces.web.routes.subscriptions import router as sub_router
from src.interfaces.web.routes.auth import router as auth_router
from src.interfaces.web.routes.admin import router as admin_router
from src.interfaces.web.routes.notifications import router as notif_router
from src.interfaces.web.dependencies import NotAuthenticatedException, ForbiddenException

app = FastAPI(title="SubTrack")
app.mount("/static", StaticFiles(directory="src/interfaces/web/static"), name="static")

app.include_router(auth_router)
app.include_router(sub_router)
app.include_router(admin_router)
app.include_router(notif_router)


@app.exception_handler(NotAuthenticatedException)
async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
    return RedirectResponse("/login", status_code=302)


@app.exception_handler(ForbiddenException)
async def forbidden_handler(request: Request, exc: ForbiddenException):
    return HTMLResponse(
        "<h3 style='color:#c62828;padding:2rem;'>403 — 您沒有執行此操作的權限。</h3>"
        "<p style='padding:0 2rem;'><a href='/'>← 返回首頁</a></p>",
        status_code=403,
    )
```

**Logging init analog** — `scripts/run_notifications.py` lines 26–34:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)
```

**What to add — lifespan event with SECRET_KEY check + JSON logging init:**

Decision references: D-01 (stdlib logging), D-02 (JSON format), D-04 (lifespan location), D-08 (SECRET_KEY check).

The new `app.py` must:
1. Import `contextlib.asynccontextmanager`, `logging`, `os`, `json`, `time`
2. Define a `JsonFormatter(logging.Formatter)` class with `format()` returning `json.dumps({...})`
   - Fields: `timestamp` (ISO), `level`, `method`, `path`, `status_code`, `duration_ms`
3. Define `@asynccontextmanager async def lifespan(app)` that:
   - Checks `os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")` — raise `RuntimeError` if missing or equals the dev default string
   - Calls `logging.basicConfig(...)` with `JsonFormatter` on `StreamHandler(sys.stdout)`
   - `yield`
4. Pass `lifespan=lifespan` to `FastAPI(title="SubTrack", lifespan=lifespan)`
5. Add a Starlette `@app.middleware("http")` that logs one JSON line per request (start time → call `next` → log method/path/status/duration)
6. The two existing `@app.exception_handler` blocks remain unchanged

**FastAPI lifespan signature (stdlib pattern):**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown (nothing needed)

app = FastAPI(title="SubTrack", lifespan=lifespan)
```

---

### `src/interfaces/web/session.py` (fix SECRET_KEY fallback — line 5 only)

**Current state** (full file, 33 lines):
```python
import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response

_SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
_serializer = URLSafeTimedSerializer(_SECRET_KEY)
...
```

**What to change — line 5:**

Decision D-08: The `app.py` lifespan now raises `RuntimeError` before any request arrives if `SECRET_KEY` is wrong. The fallback string in `session.py` line 5 therefore becomes dead code but is still present. The fix is to remove the hardcoded default so the module reads the env var cleanly:

```python
# line 5 — BEFORE:
_SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# line 5 — AFTER:
_SECRET_KEY = os.environ["SECRET_KEY"]
```

Using `os.environ["SECRET_KEY"]` (no default) means the lifespan check runs first (FastAPI starts lifespan before serving any requests) and the `KeyError` here is an additional safety net if session.py is ever imported outside the app context.

---

### `src/infrastructure/database/session.py` (delete stale comment block — lines 1–18)

**Current state** (full file, 29 lines):
```python
# SQL Server setup — run the following in SQL Server Management Studio before use:
#
# CREATE DATABASE subtrack;
# ...18 lines of stale CREATE TABLE DDL...
# GO

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

_connection_string = os.environ["DB_CONNECTION_STRING"]
engine = create_engine(_connection_string, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**What to change — delete lines 1–18, replace with pointer:**

Decision D-12. The entire comment block (lines 1–18, ending with `# GO`) must be replaced with a single line:
```python
# Schema defined in src/infrastructure/database/models.py
```

The result is:
```python
# Schema defined in src/infrastructure/database/models.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

_connection_string = os.environ["DB_CONNECTION_STRING"]
engine = create_engine(_connection_string, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

### `src/infrastructure/auth/hash_utils.py` (read-only verify — no change)

**Current state** (full file, 9 lines):
```python
import bcrypt

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

Confirmed: already imports `bcrypt` directly at line 1. Decision D-11 is satisfied — no code change needed.

---

### `requirements.txt` (remove passlib line — line 11)

**Current state** (full file, 12 lines):
```
fastapi==0.115.6
uvicorn[standard]==0.32.1
jinja2==3.1.4
python-multipart==0.0.20
sqlalchemy==2.0.36
pyodbc==5.2.0
python-dotenv==1.0.1
pytest==8.3.4
pytest-mock==3.14.0
httpx==0.28.1
passlib[bcrypt]==1.7.4   ← DELETE this line
itsdangerous==2.2.0
```

Decision D-11: remove line 11 (`passlib[bcrypt]==1.7.4`). The `bcrypt` package is a transitive dependency pulled in by passlib; after removing passlib, add `bcrypt` as a direct pin. Check current bcrypt version first with `pip show bcrypt`.

**After:**
```
fastapi==0.115.6
uvicorn[standard]==0.32.1
jinja2==3.1.4
python-multipart==0.0.20
sqlalchemy==2.0.36
pyodbc==5.2.0
python-dotenv==1.0.1
pytest==8.3.4
pytest-mock==3.14.0
httpx==0.28.1
bcrypt==<version>
itsdangerous==2.2.0
```

---

### `src/interfaces/web/routes/subscriptions.py` (two changes)

**Current state — NOTIFICATION_OPTIONS** (lines 22–29):
```python
NOTIFICATION_OPTIONS = [
    (3,   "3 天前"),
    (7,   "7 天前"),
    (14,  "14 天前"),
    (30,  "1 個月前"),
    (90,  "3 個月前"),
    (120, "4 個月前"),
]
```

**Current state — templates instantiation** (line 20):
```python
templates = Jinja2Templates(directory="src/interfaces/web/templates")
```

**Current state — annual_cost() inner function** (lines 55–65, first occurrence in `dashboard()`):
```python
def annual_cost(s):
    if s.cost is None:
        return 0.0
    multipliers = {
        "monthly":     12,
        "quarterly":   4,
        "semi_annual": 2,
        "annual":      1,
        "biennial":    0.5,
    }
    return float(s.cost) * multipliers.get(s.billing_cycle or "annual", 1)
```
Same function body repeated at lines 371–381 inside `reports()`.

**What to change:**

1. Remove lines 22–29 (`NOTIFICATION_OPTIONS`). Replace with import from constants:
   ```python
   from src.interfaces.web.constants import NOTIFICATION_OPTIONS
   ```

2. Remove line 20 (`templates = Jinja2Templates(...)`). Replace with shared instance import from dependencies:
   ```python
   from src.interfaces.web.dependencies import templates
   ```
   Also remove `from fastapi.templating import Jinja2Templates` from the import block if no longer needed.

3. Remove the `annual_cost(s)` inner function at lines 55–65 (inside `dashboard()`). Replace the 3 call sites within `dashboard()` (`annual_cost(s)` → `s.annual_cost()`).

4. Remove the `annual_cost(s)` inner function at lines 371–381 (inside `reports()`). Replace the 3 call sites within `reports()` (`annual_cost(s)` → `s.annual_cost()`).

**Call-site replacement pattern** — every occurrence of `annual_cost(s)` in the two functions becomes `s.annual_cost()`. The logic is identical; the computation moves to the entity.

---

### `src/interfaces/web/routes/notifications.py` (two changes)

**Current state — NOTIFICATION_OPTIONS** (lines 14–21):
```python
NOTIFICATION_OPTIONS = [
    (3,   "3 天前"),
    (7,   "7 天前"),
    (14,  "14 天前"),
    (30,  "1 個月前"),
    (90,  "3 個月前"),
    (120, "4 個月前"),
]
```

**Current state — templates instantiation** (line 12):
```python
templates = Jinja2Templates(directory="src/interfaces/web/templates")
```

**What to change:**

1. Remove lines 14–21. Replace with:
   ```python
   from src.interfaces.web.constants import NOTIFICATION_OPTIONS
   ```

2. Remove line 12 (`templates = Jinja2Templates(...)`). Replace with:
   ```python
   from src.interfaces.web.dependencies import templates
   ```
   Also remove `from fastapi.templating import Jinja2Templates` from imports.

---

### `src/interfaces/web/routes/admin.py` (fix silent except blocks + templates)

**Current state — silent except at lines 79–81:**
```python
    except Exception:
        pass  # email failure won't block account creation
```

**Current state — silent except at lines 113–115:**
```python
        except Exception:
            pass
```

**Current state — templates instantiation** (line 12):
```python
templates = Jinja2Templates(directory="src/interfaces/web/templates")
```

**What to change — Decision D-05:**

1. Both `except Exception: pass` blocks must log the exception. Add `import logging` at top and `log = logging.getLogger(__name__)`. Replace both blocks:

   Lines 79–81 (after invite send in `create_user_submit`):
   ```python
   except Exception:
       log.exception("Failed to send invite email to %s", email)
   ```

   Lines 113–115 (after invite resend in `resend_invite`):
   ```python
   except Exception:
       log.exception("Failed to resend invite email to user_id=%s", user_id)
   ```

2. Remove line 12 (`templates = Jinja2Templates(...)`). Replace with:
   ```python
   from src.interfaces.web.dependencies import templates
   ```
   Also remove `from fastapi.templating import Jinja2Templates` from imports.

**Logger pattern to follow** (from `scripts/run_notifications.py` lines 34–52):
```python
log = logging.getLogger(__name__)
# ...
log.exception(f"Notification run failed: {exc}")
```
`log.exception(...)` automatically appends the full traceback to the log entry — no need to pass `exc_info=True` separately.

---

### `src/domain/entities/subscription.py` (add annual_cost() method)

**Current state** (full file, 50 lines):

Existing domain method to follow as structural analog — `should_notify_today()` (lines 47–49):
```python
def should_notify_today(self, today: date) -> bool:
    trigger = self.expiry_date - timedelta(days=self.notification_days.value)
    return today == trigger
```

**What to add — Decision D-09:**

Add `annual_cost()` as an instance method immediately after `should_notify_today()`:

```python
def annual_cost(self) -> float:
    if self.cost is None:
        return 0.0
    multipliers = {
        "monthly":     12,
        "quarterly":   4,
        "semi_annual": 2,
        "annual":      1,
        "biennial":    0.5,
    }
    return float(self.cost) * multipliers.get(self.billing_cycle or "annual", 1)
```

This is the exact same logic extracted verbatim from the two copies in `subscriptions.py` (lines 55–65 and 371–381). The method takes no arguments beyond `self` — billing cycle is already a field on the entity.

No new imports are required (uses only builtins and existing `self.cost` / `self.billing_cycle` fields).

---

### `src/infrastructure/database/sql_subscription_repository.py` (fix datetime.now())

**Current state — line 1 import:**
```python
from datetime import datetime
```

**Current state — line 97 (inside `update()`):**
```python
model.updated_at = datetime.now()
```

**Current state — line 106 (inside `deactivate()`):**
```python
model.updated_at = datetime.now()
```

**What to change — Decision D-15:**

1. Line 1: add `timezone` to the import:
   ```python
   from datetime import datetime, timezone
   ```

2. Line 97: replace `datetime.now()` with timezone-aware call:
   ```python
   model.updated_at = datetime.now(timezone.utc)
   ```

3. Line 106: same fix:
   ```python
   model.updated_at = datetime.now(timezone.utc)
   ```

Note: the CONTEXT.md mentions line 97 only, but `deactivate()` at line 106 has the identical pattern and must be fixed in the same pass.

---

### `src/infrastructure/database/models.py` (fix datetime.now defaults — lines 35–36)

**Current state — line 1 import:**
```python
from datetime import datetime
```

**Current state — lines 35–36 (SubscriptionModel):**
```python
created_at = Column(DateTime, nullable=False, default=datetime.now)
updated_at = Column(DateTime, nullable=True,  onupdate=datetime.now)
```

Note: all other `created_at` columns in this file use the same pattern (UserModel line 51, ConfigOptionModel line 64, AuditLogModel line 77).

**What to change — Decision D-15:**

1. Add `timezone` to line 1:
   ```python
   from datetime import datetime, timezone
   ```

2. Lines 35–36 (SubscriptionModel) — change callables:
   ```python
   created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
   updated_at = Column(DateTime, nullable=True,  onupdate=lambda: datetime.now(timezone.utc))
   ```

3. The same fix must be applied to **all** `default=datetime.now` and `onupdate=datetime.now` occurrences in the file for consistency (UserModel line 51, ConfigOptionModel line 64, AuditLogModel line 77). CONTEXT.md calls out lines 35–36 but the pattern is the same across the whole file.

**Why lambda:** SQLAlchemy `default=` accepts a callable. `datetime.now` (without `()`) passes the bound method, which SQLAlchemy calls at insert time. `datetime.now(timezone.utc)` requires a partial/lambda because it needs an argument:
```python
default=lambda: datetime.now(timezone.utc)
```

---

### `src/interfaces/web/dependencies.py` (add shared Jinja2Templates instance)

**Current state** (full file, 132 lines — key sections):

Imports block (lines 1–19) — no `Jinja2Templates` import present.

DI factory functions follow a clear pattern (lines 38–51):
```python
def get_repo(session: Session = Depends(get_db_session)) -> SqlSubscriptionRepository:
    return SqlSubscriptionRepository(session)
```

**What to add — Decision D-14:**

1. Add import at the top of the imports block:
   ```python
   from fastapi.templating import Jinja2Templates
   ```

2. Add the shared instance as a module-level constant immediately after the imports, before `class NotAuthenticatedException`:
   ```python
   templates = Jinja2Templates(directory="src/interfaces/web/templates")
   ```

3. All four router files (`subscriptions.py`, `notifications.py`, `admin.py`, and `auth.py`) then import it:
   ```python
   from src.interfaces.web.dependencies import templates
   ```

The existing pattern in `dependencies.py` shows that module-level singletons (like `SessionLocal` from `session.py`) are the right home for shared infra objects.

---

### `src/interfaces/web/constants.py` (NEW FILE)

**Analog:** `NOTIFICATION_OPTIONS` block from `src/interfaces/web/routes/subscriptions.py` lines 22–29 — verbatim content to extract.

**File to create:**
```python
# Shared UI constants for the web interface.

NOTIFICATION_OPTIONS = [
    (3,   "3 天前"),
    (7,   "7 天前"),
    (14,  "14 天前"),
    (30,  "1 個月前"),
    (90,  "3 個月前"),
    (120, "4 個月前"),
]
```

No imports required — the list contains only Python literals. The `(int, str)` tuple format is what the Jinja2 templates iterate over; it must not be changed.

---

## Shared Patterns

### Logging setup
**Source:** `scripts/run_notifications.py` lines 26–34
**Apply to:** `app.py` (lifespan) and `admin.py` (module-level logger)

```python
# Module-level logger (all route files that need logging):
import logging
log = logging.getLogger(__name__)

# App-level JSON logging init (app.py lifespan only):
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
# Handler formatter is replaced with JsonFormatter instance per D-02
```

### Exception logging (replacing silent pass)
**Source:** `scripts/run_notifications.py` line 52
**Apply to:** `admin.py` lines 79–81, 113–115

```python
# BEFORE:
except Exception:
    pass

# AFTER:
except Exception:
    log.exception("Descriptive message with context vars")
# log.exception() captures and logs the full traceback automatically
```

### datetime timezone fix
**Source:** pattern from `sql_subscription_repository.py` and `models.py`
**Apply to:** all `datetime.now()` and `default=datetime.now` occurrences

```python
# BEFORE:
from datetime import datetime
datetime.now()
default=datetime.now

# AFTER:
from datetime import datetime, timezone
datetime.now(timezone.utc)
default=lambda: datetime.now(timezone.utc)
```

### Shared templates import
**Source:** `dependencies.py` (after adding the instance there)
**Apply to:** `subscriptions.py`, `notifications.py`, `admin.py`, `auth.py`

```python
# BEFORE (each router file):
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="src/interfaces/web/templates")

# AFTER (each router file):
from src.interfaces.web.dependencies import templates
# Remove the Jinja2Templates import line entirely
```

### NOTIFICATION_OPTIONS import
**Source:** `src/interfaces/web/constants.py` (new file)
**Apply to:** `subscriptions.py` (remove lines 22–29), `notifications.py` (remove lines 14–21)

```python
# BEFORE (each file):
NOTIFICATION_OPTIONS = [
    (3,   "3 天前"),
    ...
]

# AFTER (each file):
from src.interfaces.web.constants import NOTIFICATION_OPTIONS
```

---

## No Analog Found

None — all files have clear analogs or are self-modifications.

---

## Metadata

**Analog search scope:** `src/` (all layers), `scripts/`
**Files read:** 14
**Pattern extraction date:** 2026-05-07
