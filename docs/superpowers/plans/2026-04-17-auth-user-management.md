# Auth & User Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user authentication (login/logout with signed-cookie sessions) and per-user CRUD permission management to the SaaS Tracker web application.

**Architecture:** Users are stored in a `users` SQL Server table. Passwords are hashed with bcrypt via passlib. Sessions use `itsdangerous` URLSafeTimedSerializer to create signed, HttpOnly cookies (no server-side session storage needed). A custom `NotAuthenticatedException` + FastAPI exception handler redirects unauthenticated requests to `/login`. Admin users manage other users and their per-subscription permissions via `/admin/users` routes.

**Tech Stack:** FastAPI, Jinja2, SQLAlchemy 2, pyodbc (SQL Server), passlib[bcrypt]==1.7.4, itsdangerous==2.2.0, pytest

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `src/domain/entities/user.py` | User dataclass |
| `src/domain/repositories/user_repository.py` | Abstract UserRepository interface |
| `src/infrastructure/auth/__init__.py` | (empty) |
| `src/infrastructure/auth/hash_utils.py` | `hash_password()`, `verify_password()` |
| `src/infrastructure/database/sql_user_repository.py` | SQLAlchemy UserRepository |
| `src/application/use_cases/auth/__init__.py` | (empty) |
| `src/application/use_cases/auth/login_user.py` | LoginUserUseCase |
| `src/application/use_cases/auth/register_user.py` | RegisterUserUseCase (admin-only, @gilliontec.com.tw) |
| `src/application/use_cases/auth/update_user_permissions.py` | UpdateUserPermissionsUseCase |
| `src/application/use_cases/auth/list_users.py` | ListUsersUseCase |
| `src/interfaces/web/session.py` | Cookie create/clear/read helpers |
| `src/interfaces/web/routes/auth.py` | `/login` GET/POST, `/logout` POST |
| `src/interfaces/web/routes/admin.py` | `/admin/users` CRUD routes |
| `src/interfaces/web/templates/login.html` | Login page |
| `src/interfaces/web/templates/admin/users.html` | User list |
| `src/interfaces/web/templates/admin/user_create.html` | Create user form |
| `src/interfaces/web/templates/admin/user_edit.html` | Edit permissions form |
| `scripts/seed_admin.py` | Bootstrap first admin account |
| `tests/unit/auth/__init__.py` | (empty) |
| `tests/unit/auth/test_user_entity.py` | |
| `tests/unit/auth/test_login_user.py` | |
| `tests/unit/auth/test_register_user.py` | |
| `tests/unit/auth/test_update_user_permissions.py` | |

### Modified Files
| File | Change |
|------|--------|
| `src/infrastructure/database/models.py` | Add `UserModel` class |
| `src/interfaces/web/app.py` | Register auth & admin routers, add exception handlers |
| `src/interfaces/web/dependencies.py` | Add user repo, auth use cases, guard dependencies |
| `src/interfaces/web/routes/subscriptions.py` | Add `current_user` dependency to all routes |
| `src/interfaces/web/templates/base.html` | Add user display + logout in navbar |
| `requirements.txt` | Add passlib[bcrypt], itsdangerous |
| `.env` | Add SECRET_KEY |

---

### Task 1: User entity + UserRepository interface

**Files:**
- Create: `src/domain/entities/user.py`
- Create: `src/domain/repositories/user_repository.py`
- Create: `tests/unit/auth/__init__.py`
- Create: `tests/unit/auth/test_user_entity.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/auth/test_user_entity.py
from src.domain.entities.user import User


def test_user_defaults():
    user = User(
        email="alice@gilliontec.com.tw",
        display_name="Alice",
        hashed_password="hashed",
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
    )
    assert user.is_active is True
    assert user.id is None
    assert user.created_at is None
    assert user.last_login_at is None


def test_admin_has_all_permissions():
    user = User(
        email="admin@gilliontec.com.tw",
        display_name="Admin",
        hashed_password="hashed",
        role="admin",
        can_create=True,
        can_update=True,
        can_delete=True,
    )
    assert user.role == "admin"
    assert user.can_create is True
    assert user.can_update is True
    assert user.can_delete is True
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/unit/auth/test_user_entity.py -v
```
Expected: `ERROR ... ModuleNotFoundError: No module named 'src.domain.entities.user'`

- [ ] **Step 3: Create User entity**

```python
# src/domain/entities/user.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    email: str
    display_name: str
    hashed_password: str
    role: str           # "admin" | "user"
    can_create: bool
    can_update: bool
    can_delete: bool
    id: int | None = None
    is_active: bool = True
    created_at: datetime | None = None
    last_login_at: datetime | None = None
```

- [ ] **Step 4: Create UserRepository interface**

```python
# src/domain/repositories/user_repository.py
from abc import ABC, abstractmethod
from src.domain.entities.user import User


class UserRepository(ABC):

    @abstractmethod
    def add(self, user: User) -> User:
        """Persist a new user; returns entity with assigned id."""
        ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def get_all(self) -> list[User]:
        """Return all users including inactive, for admin management."""
        ...

    @abstractmethod
    def update(self, user: User) -> User:
        """Persist updated user; user.id must be set."""
        ...
```

- [ ] **Step 5: Create empty `__init__` file**

Create `tests/unit/auth/__init__.py` as an empty file.

- [ ] **Step 6: Run test to verify it passes**

```
pytest tests/unit/auth/test_user_entity.py -v
```
Expected: `2 passed`

- [ ] **Step 7: Commit**

```bash
git add src/domain/entities/user.py src/domain/repositories/user_repository.py tests/unit/auth/__init__.py tests/unit/auth/test_user_entity.py
git commit -m "feat: add User entity and UserRepository interface"
```

---

### Task 2: Hash utilities + UserModel + install dependencies

**Files:**
- Create: `src/infrastructure/auth/__init__.py`
- Create: `src/infrastructure/auth/hash_utils.py`
- Modify: `src/infrastructure/database/models.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add dependencies to requirements.txt**

Open `requirements.txt` and append these two lines:

```
passlib[bcrypt]==1.7.4
itsdangerous==2.2.0
```

- [ ] **Step 2: Install new packages**

```
pip install passlib[bcrypt]==1.7.4 itsdangerous==2.2.0
```
Expected: both packages install with no errors.

- [ ] **Step 3: Create hash utilities**

Create `src/infrastructure/auth/__init__.py` as an empty file.

```python
# src/infrastructure/auth/hash_utils.py
from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _ctx.verify(plain, hashed)
```

- [ ] **Step 4: Add UserModel to models.py**

Open `src/infrastructure/database/models.py`. At the end of the file, after the `SubscriptionModel` class, append:

```python
class UserModel(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    email           = Column(String(200), nullable=False, unique=True)
    display_name    = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(20), nullable=False, default="user")
    can_create      = Column(Boolean, nullable=False, default=False)
    can_update      = Column(Boolean, nullable=False, default=False)
    can_delete      = Column(Boolean, nullable=False, default=False)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime, nullable=False, default=datetime.now)
    last_login_at   = Column(DateTime, nullable=True)
```

- [ ] **Step 5: Create users table in SQL Server**

Open SSMS, connect to `localhost\SQLEXPRESS`, and run:

```sql
USE subscription_tracker;
GO
CREATE TABLE users (
    id               INT             IDENTITY(1,1) PRIMARY KEY,
    email            NVARCHAR(200)   NOT NULL UNIQUE,
    display_name     NVARCHAR(100)   NOT NULL,
    hashed_password  NVARCHAR(255)   NOT NULL,
    role             NVARCHAR(20)    NOT NULL DEFAULT 'user',
    can_create       BIT             NOT NULL DEFAULT 0,
    can_update       BIT             NOT NULL DEFAULT 0,
    can_delete       BIT             NOT NULL DEFAULT 0,
    is_active        BIT             NOT NULL DEFAULT 1,
    created_at       DATETIME        NOT NULL DEFAULT GETDATE(),
    last_login_at    DATETIME        NULL
);
GO
```
Expected: `Commands completed successfully.`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt src/infrastructure/auth/__init__.py src/infrastructure/auth/hash_utils.py src/infrastructure/database/models.py
git commit -m "feat: add hash utilities, UserModel, users table SQL"
```

---

### Task 3: SqlUserRepository

**Files:**
- Create: `src/infrastructure/database/sql_user_repository.py`

- [ ] **Step 1: Create SqlUserRepository**

```python
# src/infrastructure/database/sql_user_repository.py
from sqlalchemy.orm import Session
from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.database.models import UserModel


class SqlUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            display_name=model.display_name,
            hashed_password=model.hashed_password,
            role=model.role,
            can_create=model.can_create,
            can_update=model.can_update,
            can_delete=model.can_delete,
            is_active=model.is_active,
            created_at=model.created_at,
            last_login_at=model.last_login_at,
        )

    def add(self, user: User) -> User:
        model = UserModel(
            email=user.email,
            display_name=user.display_name,
            hashed_password=user.hashed_password,
            role=user.role,
            can_create=user.can_create,
            can_update=user.can_update,
            can_delete=user.can_delete,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, user_id: int) -> User | None:
        model = self._session.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        model = (
            self._session.query(UserModel)
            .filter(UserModel.email == email)
            .first()
        )
        return self._to_entity(model) if model else None

    def get_all(self) -> list[User]:
        models = (
            self._session.query(UserModel)
            .order_by(UserModel.created_at)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def update(self, user: User) -> User:
        model = self._session.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"User {user.id} not found")
        model.display_name    = user.display_name
        model.hashed_password = user.hashed_password
        model.role            = user.role
        model.can_create      = user.can_create
        model.can_update      = user.can_update
        model.can_delete      = user.can_delete
        model.is_active       = user.is_active
        model.last_login_at   = user.last_login_at
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)
```

- [ ] **Step 2: Commit**

```bash
git add src/infrastructure/database/sql_user_repository.py
git commit -m "feat: add SqlUserRepository"
```

---

### Task 4: Auth use cases — login + register

**Files:**
- Create: `src/application/use_cases/auth/__init__.py`
- Create: `src/application/use_cases/auth/login_user.py`
- Create: `src/application/use_cases/auth/register_user.py`
- Create: `tests/unit/auth/test_login_user.py`
- Create: `tests/unit/auth/test_register_user.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/auth/test_login_user.py
import pytest
from unittest.mock import MagicMock
from src.application.use_cases.auth.login_user import LoginUserUseCase
from src.domain.entities.user import User
from src.infrastructure.auth.hash_utils import hash_password


@pytest.fixture
def repo():
    return MagicMock()


def _make_user(hashed_pw: str, is_active: bool = True) -> User:
    return User(
        id=1,
        email="alice@gilliontec.com.tw",
        display_name="Alice",
        hashed_password=hashed_pw,
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
        is_active=is_active,
    )


def test_login_success(repo):
    pw = hash_password("correct!")
    repo.get_by_email.return_value = _make_user(pw)
    result = LoginUserUseCase(repo).execute("alice@gilliontec.com.tw", "correct!")
    assert result.email == "alice@gilliontec.com.tw"


def test_login_wrong_password(repo):
    pw = hash_password("correct!")
    repo.get_by_email.return_value = _make_user(pw)
    with pytest.raises(ValueError, match="Invalid credentials"):
        LoginUserUseCase(repo).execute("alice@gilliontec.com.tw", "wrong!")


def test_login_user_not_found(repo):
    repo.get_by_email.return_value = None
    with pytest.raises(ValueError, match="Invalid credentials"):
        LoginUserUseCase(repo).execute("nobody@gilliontec.com.tw", "pw")


def test_login_inactive_user(repo):
    pw = hash_password("correct!")
    repo.get_by_email.return_value = _make_user(pw, is_active=False)
    with pytest.raises(ValueError, match="Invalid credentials"):
        LoginUserUseCase(repo).execute("alice@gilliontec.com.tw", "correct!")
```

```python
# tests/unit/auth/test_register_user.py
import pytest
from unittest.mock import MagicMock
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.domain.entities.user import User


@pytest.fixture
def repo():
    mock = MagicMock()
    mock.get_by_email.return_value = None
    mock.add.side_effect = lambda u: User(
        id=1,
        email=u.email,
        display_name=u.display_name,
        hashed_password=u.hashed_password,
        role=u.role,
        can_create=u.can_create,
        can_update=u.can_update,
        can_delete=u.can_delete,
    )
    return mock


def test_register_success(repo):
    result = RegisterUserUseCase(repo).execute(
        "alice@gilliontec.com.tw", "Alice", "Passw0rd!",
        can_create=True, can_update=True, can_delete=False,
    )
    assert result.id == 1
    assert result.email == "alice@gilliontec.com.tw"
    assert result.role == "user"
    repo.add.assert_called_once()


def test_register_invalid_domain(repo):
    with pytest.raises(ValueError, match="gilliontec.com.tw"):
        RegisterUserUseCase(repo).execute(
            "alice@gmail.com", "Alice", "Passw0rd!",
            can_create=False, can_update=False, can_delete=False,
        )


def test_register_duplicate_email(repo):
    existing = User(
        id=1, email="alice@gilliontec.com.tw", display_name="Alice",
        hashed_password="x", role="user",
        can_create=False, can_update=False, can_delete=False,
    )
    repo.get_by_email.return_value = existing
    with pytest.raises(ValueError, match="already registered"):
        RegisterUserUseCase(repo).execute(
            "alice@gilliontec.com.tw", "Alice2", "Passw0rd!",
            can_create=False, can_update=False, can_delete=False,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/auth/test_login_user.py tests/unit/auth/test_register_user.py -v
```
Expected: `ERROR ... ModuleNotFoundError: No module named 'src.application.use_cases.auth'`

- [ ] **Step 3: Create empty `__init__.py`**

Create `src/application/use_cases/auth/__init__.py` as an empty file.

- [ ] **Step 4: Implement LoginUserUseCase**

```python
# src/application/use_cases/auth/login_user.py
from datetime import datetime
from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.auth.hash_utils import verify_password


class LoginUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(self, email: str, password: str) -> User:
        user = self._repo.get_by_email(email)
        if not user or not user.is_active:
            raise ValueError("Invalid credentials")
        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        user.last_login_at = datetime.now()
        self._repo.update(user)
        return user
```

- [ ] **Step 5: Implement RegisterUserUseCase**

```python
# src/application/use_cases/auth/register_user.py
from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.auth.hash_utils import hash_password


class RegisterUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(
        self,
        email: str,
        display_name: str,
        password: str,
        can_create: bool,
        can_update: bool,
        can_delete: bool,
    ) -> User:
        if not email.endswith("@gilliontec.com.tw"):
            raise ValueError("Email must end with @gilliontec.com.tw")
        if self._repo.get_by_email(email) is not None:
            raise ValueError("Email already registered")
        user = User(
            email=email,
            display_name=display_name,
            hashed_password=hash_password(password),
            role="user",
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
        )
        return self._repo.add(user)
```

- [ ] **Step 6: Run tests to verify they pass**

```
pytest tests/unit/auth/test_login_user.py tests/unit/auth/test_register_user.py -v
```
Expected: `7 passed`

- [ ] **Step 7: Commit**

```bash
git add src/application/use_cases/auth/__init__.py src/application/use_cases/auth/login_user.py src/application/use_cases/auth/register_user.py tests/unit/auth/test_login_user.py tests/unit/auth/test_register_user.py
git commit -m "feat: add LoginUserUseCase and RegisterUserUseCase"
```

---

### Task 5: Auth use cases — permission management

**Files:**
- Create: `src/application/use_cases/auth/update_user_permissions.py`
- Create: `src/application/use_cases/auth/list_users.py`
- Create: `tests/unit/auth/test_update_user_permissions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/auth/test_update_user_permissions.py
import pytest
from unittest.mock import MagicMock
from src.application.use_cases.auth.update_user_permissions import UpdateUserPermissionsUseCase
from src.domain.entities.user import User


@pytest.fixture
def repo():
    return MagicMock()


def _make_user() -> User:
    return User(
        id=2, email="bob@gilliontec.com.tw", display_name="Bob",
        hashed_password="x", role="user",
        can_create=False, can_update=False, can_delete=False,
    )


def test_update_permissions_success(repo):
    user = _make_user()
    repo.get_by_id.return_value = user
    repo.update.side_effect = lambda u: u
    result = UpdateUserPermissionsUseCase(repo).execute(
        user_id=2, can_create=True, can_update=True, can_delete=False, is_active=True,
    )
    assert result.can_create is True
    assert result.can_update is True
    assert result.can_delete is False


def test_update_permissions_user_not_found(repo):
    repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="not found"):
        UpdateUserPermissionsUseCase(repo).execute(
            user_id=99, can_create=True, can_update=True, can_delete=True, is_active=True,
        )
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/unit/auth/test_update_user_permissions.py -v
```
Expected: `ERROR ... ModuleNotFoundError`

- [ ] **Step 3: Implement UpdateUserPermissionsUseCase**

```python
# src/application/use_cases/auth/update_user_permissions.py
from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository


class UpdateUserPermissionsUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(
        self,
        user_id: int,
        can_create: bool,
        can_update: bool,
        can_delete: bool,
        is_active: bool,
    ) -> User:
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        user.can_create = can_create
        user.can_update = can_update
        user.can_delete = can_delete
        user.is_active  = is_active
        return self._repo.update(user)
```

- [ ] **Step 4: Implement ListUsersUseCase**

```python
# src/application/use_cases/auth/list_users.py
from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository


class ListUsersUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(self) -> list[User]:
        return self._repo.get_all()
```

- [ ] **Step 5: Run test to verify it passes**

```
pytest tests/unit/auth/test_update_user_permissions.py -v
```
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add src/application/use_cases/auth/update_user_permissions.py src/application/use_cases/auth/list_users.py tests/unit/auth/test_update_user_permissions.py
git commit -m "feat: add UpdateUserPermissionsUseCase and ListUsersUseCase"
```

---

### Task 6: Session helpers + updated dependencies.py

**Files:**
- Create: `src/interfaces/web/session.py`
- Modify: `src/interfaces/web/dependencies.py`
- Modify: `.env`

- [ ] **Step 1: Add SECRET_KEY to .env**

Open `.env` and append:

```
SECRET_KEY=change-this-to-a-random-secret-key-before-deploying
```

- [ ] **Step 2: Create session.py**

```python
# src/interfaces/web/session.py
import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response

_SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
_serializer = URLSafeTimedSerializer(_SECRET_KEY)
SESSION_COOKIE = "session"
SESSION_MAX_AGE = 86400 * 7  # 7 days


def create_session_cookie(response: Response, user_id: int) -> None:
    token = _serializer.dumps({"user_id": user_id})
    response.set_cookie(
        SESSION_COOKIE, token,
        httponly=True, samesite="lax",
        max_age=SESSION_MAX_AGE,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)


def get_session_user_id(request: Request) -> int | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None
```

- [ ] **Step 3: Replace dependencies.py with the full updated version**

Replace the entire contents of `src/interfaces/web/dependencies.py` with:

```python
# src/interfaces/web/dependencies.py
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from src.infrastructure.database.session import SessionLocal
from src.infrastructure.database.sql_subscription_repository import SqlSubscriptionRepository
from src.infrastructure.database.sql_user_repository import SqlUserRepository
from src.application.use_cases.create_subscription import CreateSubscriptionUseCase
from src.application.use_cases.update_subscription import UpdateSubscriptionUseCase
from src.application.use_cases.delete_subscription import DeleteSubscriptionUseCase
from src.application.use_cases.get_subscription import GetSubscriptionUseCase
from src.application.use_cases.list_subscriptions import ListSubscriptionsUseCase
from src.application.use_cases.auth.login_user import LoginUserUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.application.use_cases.auth.update_user_permissions import UpdateUserPermissionsUseCase
from src.application.use_cases.auth.list_users import ListUsersUseCase
from src.domain.entities.user import User
from src.interfaces.web.session import get_session_user_id


class NotAuthenticatedException(Exception):
    pass


class ForbiddenException(Exception):
    pass


def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_repo(session: Session = Depends(get_db_session)) -> SqlSubscriptionRepository:
    return SqlSubscriptionRepository(session)


def get_user_repo(session: Session = Depends(get_db_session)) -> SqlUserRepository:
    return SqlUserRepository(session)


# ── Subscription use cases ──────────────────────────────────────────────────
def get_list_uc(repo=Depends(get_repo)) -> ListSubscriptionsUseCase:
    return ListSubscriptionsUseCase(repo)


def get_create_uc(repo=Depends(get_repo)) -> CreateSubscriptionUseCase:
    return CreateSubscriptionUseCase(repo)


def get_update_uc(repo=Depends(get_repo)) -> UpdateSubscriptionUseCase:
    return UpdateSubscriptionUseCase(repo)


def get_delete_uc(repo=Depends(get_repo)) -> DeleteSubscriptionUseCase:
    return DeleteSubscriptionUseCase(repo)


def get_single_uc(repo=Depends(get_repo)) -> GetSubscriptionUseCase:
    return GetSubscriptionUseCase(repo)


# ── Auth use cases ──────────────────────────────────────────────────────────
def get_login_uc(repo=Depends(get_user_repo)) -> LoginUserUseCase:
    return LoginUserUseCase(repo)


def get_register_uc(repo=Depends(get_user_repo)) -> RegisterUserUseCase:
    return RegisterUserUseCase(repo)


def get_update_permissions_uc(repo=Depends(get_user_repo)) -> UpdateUserPermissionsUseCase:
    return UpdateUserPermissionsUseCase(repo)


def get_list_users_uc(repo=Depends(get_user_repo)) -> ListUsersUseCase:
    return ListUsersUseCase(repo)


# ── Auth guards ─────────────────────────────────────────────────────────────
def get_current_user(
    request: Request,
    repo: SqlUserRepository = Depends(get_user_repo),
) -> User:
    user_id = get_session_user_id(request)
    if not user_id:
        raise NotAuthenticatedException()
    user = repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise NotAuthenticatedException()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise ForbiddenException()
    return user


def require_create(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin" and not user.can_create:
        raise ForbiddenException()
    return user


def require_update(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin" and not user.can_update:
        raise ForbiddenException()
    return user


def require_delete(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin" and not user.can_delete:
        raise ForbiddenException()
    return user
```

- [ ] **Step 4: Commit**

```bash
git add src/interfaces/web/session.py src/interfaces/web/dependencies.py .env
git commit -m "feat: add session helpers and auth dependency guards"
```

---

### Task 7: Login/logout routes + protect subscription routes

**Files:**
- Create: `src/interfaces/web/routes/auth.py`
- Create: `src/interfaces/web/templates/login.html`
- Modify: `src/interfaces/web/app.py`
- Modify: `src/interfaces/web/routes/subscriptions.py`
- Modify: `src/interfaces/web/templates/base.html`

- [ ] **Step 1: Create auth routes**

```python
# src/interfaces/web/routes/auth.py
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from src.interfaces.web.dependencies import get_login_uc
from src.interfaces.web.session import create_session_cookie, clear_session_cookie, get_session_user_id

router = APIRouter()
templates = Jinja2Templates(directory="src/interfaces/web/templates")


@router.get("/login")
def login_form(request: Request):
    if get_session_user_id(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    uc=Depends(get_login_uc),
):
    try:
        user = uc.execute(email=email, password=password)
    except ValueError:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "帳號或密碼錯誤，請重試。"}
        )
    response = RedirectResponse("/", status_code=303)
    create_session_cookie(response, user.id)
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    clear_session_cookie(response)
    return response
```

- [ ] **Step 2: Create login template**

```html
<!-- src/interfaces/web/templates/login.html -->
{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center mt-5">
  <div class="col-sm-10 col-md-6 col-lg-4">
    <div class="card shadow-sm">
      <div class="card-body p-4">
        <h5 class="card-title text-center mb-4" style="color:#1565c0;">🔐 登入系統</h5>
        {% if error %}
        <div class="alert alert-danger py-2">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/login">
          <div class="mb-3">
            <label class="form-label">Email</label>
            <input type="email" name="email" class="form-control"
                   placeholder="yourname@gilliontec.com.tw" required autofocus>
          </div>
          <div class="mb-4">
            <label class="form-label">密碼</label>
            <input type="password" name="password" class="form-control" required>
          </div>
          <button type="submit" class="btn btn-primary w-100">登入</button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Update app.py with auth router + exception handlers**

Replace the full contents of `src/interfaces/web/app.py` with:

```python
# src/interfaces/web/app.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from src.interfaces.web.routes.subscriptions import router as sub_router
from src.interfaces.web.routes.auth import router as auth_router
from src.interfaces.web.dependencies import NotAuthenticatedException, ForbiddenException

app = FastAPI(title="SaaS Subscription Tracker")

app.include_router(auth_router)
app.include_router(sub_router)


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

- [ ] **Step 4: Replace subscriptions.py to add auth guards**

Replace the full contents of `src/interfaces/web/routes/subscriptions.py` with:

```python
# src/interfaces/web/routes/subscriptions.py
from datetime import date, datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from src.domain.entities.subscription import NotificationDays
from src.interfaces.web.dependencies import (
    get_create_uc, get_delete_uc, get_list_uc, get_single_uc, get_update_uc,
    get_current_user, require_create, require_update, require_delete,
)

router = APIRouter()
templates = Jinja2Templates(directory="src/interfaces/web/templates")

NOTIFICATION_OPTIONS = [
    (3,   "3 天前"),
    (7,   "7 天前"),
    (14,  "14 天前"),
    (30,  "1 個月前"),
    (90,  "3 個月前"),
    (120, "4 個月前"),
]


@router.get("/")
def index(request: Request, uc=Depends(get_list_uc), current_user=Depends(get_current_user)):
    subscriptions = uc.execute()
    today = date.today()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "subscriptions": subscriptions,
        "today": today,
        "current_user": current_user,
    })


@router.get("/subscriptions/create")
def create_form(request: Request, current_user=Depends(require_create)):
    return templates.TemplateResponse("create.html", {
        "request": request,
        "notification_options": NOTIFICATION_OPTIONS,
        "current_user": current_user,
    })


@router.post("/subscriptions/create")
def create_submit(
    request: Request,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    notification_emails: str = Form(...),
    notification_days: int = Form(...),
    notes: str | None = Form(None),
    uc=Depends(get_create_uc),
    current_user=Depends(require_create),
):
    uc.execute(
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
        notification_emails=notification_emails,
        notification_days=NotificationDays(notification_days),
        notes=notes or None,
    )
    return RedirectResponse("/", status_code=303)


@router.get("/subscriptions/{subscription_id}/edit")
def edit_form(
    request: Request,
    subscription_id: int,
    uc=Depends(get_single_uc),
    current_user=Depends(require_update),
):
    sub = uc.execute(subscription_id)
    return templates.TemplateResponse("edit.html", {
        "request": request,
        "sub": sub,
        "notification_options": NOTIFICATION_OPTIONS,
        "current_user": current_user,
    })


@router.post("/subscriptions/{subscription_id}/edit")
def edit_submit(
    subscription_id: int,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    notification_emails: str = Form(...),
    notification_days: int = Form(...),
    notes: str | None = Form(None),
    uc=Depends(get_update_uc),
    current_user=Depends(require_update),
):
    uc.execute(
        subscription_id=subscription_id,
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
        notification_emails=notification_emails,
        notification_days=NotificationDays(notification_days),
        notes=notes or None,
    )
    return RedirectResponse("/", status_code=303)


@router.post("/subscriptions/{subscription_id}/delete")
def delete(
    subscription_id: int,
    uc=Depends(get_delete_uc),
    current_user=Depends(require_delete),
):
    uc.execute(subscription_id)
    return RedirectResponse("/", status_code=303)
```

- [ ] **Step 5: Update base.html navbar to show user info + logout**

Open `src/interfaces/web/templates/base.html`. Replace the `<nav>` line with:

```html
  <nav class="navbar navbar-custom px-4 d-flex justify-content-between align-items-center">
    <a class="navbar-brand" href="/">📋 SaaS 訂閱追蹤</a>
    <div class="d-flex align-items-center gap-3">
      {% if current_user is defined and current_user %}
        <span style="color:#cce5ff;font-size:.9rem;">{{ current_user.display_name }}</span>
        {% if current_user.role == 'admin' %}
        <a href="/admin/users" class="btn btn-sm"
           style="background:#1976d2;color:#fff;border:none;">👥 使用者管理</a>
        {% endif %}
        <form method="POST" action="/logout" class="d-inline m-0">
          <button type="submit" class="btn btn-sm"
                  style="background:#e53935;color:#fff;border:none;">登出</button>
        </form>
        {% if current_user.role == 'admin' or current_user.can_create %}
        <a href="/subscriptions/create" class="btn btn-add btn-sm">＋ 新增訂閱</a>
        {% endif %}
      {% endif %}
    </div>
  </nav>
```

- [ ] **Step 6: Verify app starts and redirects to login**

```
python main.py
```

Open `http://localhost:8000`. Expected: browser redirects to `http://localhost:8000/login` and shows the login form. (Login will not work until Task 9 seeds the admin account.)

- [ ] **Step 7: Commit**

```bash
git add src/interfaces/web/routes/auth.py src/interfaces/web/routes/subscriptions.py src/interfaces/web/templates/login.html src/interfaces/web/app.py src/interfaces/web/templates/base.html
git commit -m "feat: add login/logout, protect all subscription routes with auth"
```

---

### Task 8: Admin user management routes + templates

**Files:**
- Create: `src/interfaces/web/routes/admin.py`
- Create: `src/interfaces/web/templates/admin/users.html`
- Create: `src/interfaces/web/templates/admin/user_create.html`
- Create: `src/interfaces/web/templates/admin/user_edit.html`
- Modify: `src/interfaces/web/app.py` (add admin router)

- [ ] **Step 1: Create admin routes**

```python
# src/interfaces/web/routes/admin.py
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from src.interfaces.web.dependencies import (
    get_user_repo, get_register_uc, get_update_permissions_uc,
    get_list_users_uc, require_admin,
)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="src/interfaces/web/templates")


@router.get("/users")
def list_users(
    request: Request,
    uc=Depends(get_list_users_uc),
    current_user=Depends(require_admin),
):
    users = uc.execute()
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "users": users,
        "current_user": current_user,
    })


@router.get("/users/create")
def create_user_form(request: Request, current_user=Depends(require_admin)):
    return templates.TemplateResponse("admin/user_create.html", {
        "request": request,
        "current_user": current_user,
        "error": None,
    })


@router.post("/users/create")
def create_user_submit(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    can_create: bool = Form(False),
    can_update: bool = Form(False),
    can_delete: bool = Form(False),
    current_user=Depends(require_admin),
    uc=Depends(get_register_uc),
):
    try:
        uc.execute(
            email=email,
            display_name=display_name,
            password=password,
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
        )
    except ValueError as e:
        return templates.TemplateResponse("admin/user_create.html", {
            "request": request,
            "current_user": current_user,
            "error": str(e),
        })
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/users/{user_id}/edit")
def edit_user_form(
    request: Request,
    user_id: int,
    current_user=Depends(require_admin),
    repo=Depends(get_user_repo),
):
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin/user_edit.html", {
        "request": request,
        "user": user,
        "current_user": current_user,
        "error": None,
    })


@router.post("/users/{user_id}/edit")
def edit_user_submit(
    user_id: int,
    can_create: bool = Form(False),
    can_update: bool = Form(False),
    can_delete: bool = Form(False),
    is_active: bool = Form(False),
    current_user=Depends(require_admin),
    uc=Depends(get_update_permissions_uc),
):
    uc.execute(
        user_id=user_id,
        can_create=can_create,
        can_update=can_update,
        can_delete=can_delete,
        is_active=is_active,
    )
    return RedirectResponse("/admin/users", status_code=303)
```

- [ ] **Step 2: Create templates/admin/ directory**

Create the directory `src/interfaces/web/templates/admin/` (create a placeholder or just the files below).

- [ ] **Step 3: Create user list template**

```html
<!-- src/interfaces/web/templates/admin/users.html -->
{% extends "base.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h4>👥 使用者管理</h4>
  <a href="/admin/users/create" class="btn btn-sm btn-primary">＋ 新增使用者</a>
</div>
<table class="table table-bordered table-hover align-middle">
  <thead class="table-header">
    <tr>
      <th>Email</th>
      <th>姓名</th>
      <th>角色</th>
      <th class="text-center">新增</th>
      <th class="text-center">修改</th>
      <th class="text-center">刪除</th>
      <th>狀態</th>
      <th>操作</th>
    </tr>
  </thead>
  <tbody>
    {% for user in users %}
    <tr class="{% if not user.is_active %}table-secondary{% endif %}">
      <td>{{ user.email }}</td>
      <td>{{ user.display_name }}</td>
      <td>
        {% if user.role == 'admin' %}
        <span class="badge bg-danger">Admin</span>
        {% else %}
        <span class="badge bg-secondary">User</span>
        {% endif %}
      </td>
      <td class="text-center">{% if user.role == 'admin' or user.can_create %}✅{% else %}—{% endif %}</td>
      <td class="text-center">{% if user.role == 'admin' or user.can_update %}✅{% else %}—{% endif %}</td>
      <td class="text-center">{% if user.role == 'admin' or user.can_delete %}✅{% else %}—{% endif %}</td>
      <td>
        {% if user.is_active %}
        <span class="badge bg-success">啟用</span>
        {% else %}
        <span class="badge bg-secondary">停用</span>
        {% endif %}
      </td>
      <td>
        {% if user.role != 'admin' %}
        <a href="/admin/users/{{ user.id }}/edit" class="btn btn-sm btn-outline-primary">編輯</a>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 4: Create user_create template**

```html
<!-- src/interfaces/web/templates/admin/user_create.html -->
{% extends "base.html" %}
{% block content %}
<h4 class="mb-3">新增使用者</h4>
{% if error %}
<div class="alert alert-danger">{{ error }}</div>
{% endif %}
<form method="POST" action="/admin/users/create" style="max-width:480px">
  <div class="mb-3">
    <label class="form-label">Email（需為 @gilliontec.com.tw）</label>
    <input type="email" name="email" class="form-control" required
           placeholder="name@gilliontec.com.tw">
  </div>
  <div class="mb-3">
    <label class="form-label">姓名</label>
    <input type="text" name="display_name" class="form-control" required>
  </div>
  <div class="mb-3">
    <label class="form-label">初始密碼</label>
    <input type="password" name="password" class="form-control" required>
  </div>
  <div class="mb-4">
    <label class="form-label d-block">權限</label>
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="can_create" id="can_create" value="true">
      <label class="form-check-label" for="can_create">可新增訂閱</label>
    </div>
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="can_update" id="can_update" value="true">
      <label class="form-check-label" for="can_update">可修改訂閱</label>
    </div>
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="can_delete" id="can_delete" value="true">
      <label class="form-check-label" for="can_delete">可刪除訂閱</label>
    </div>
  </div>
  <button type="submit" class="btn btn-primary">建立</button>
  <a href="/admin/users" class="btn btn-secondary ms-2">取消</a>
</form>
{% endblock %}
```

- [ ] **Step 5: Create user_edit template**

```html
<!-- src/interfaces/web/templates/admin/user_edit.html -->
{% extends "base.html" %}
{% block content %}
<h4 class="mb-3">編輯使用者權限：{{ user.display_name }}</h4>
{% if error %}
<div class="alert alert-danger">{{ error }}</div>
{% endif %}
<form method="POST" action="/admin/users/{{ user.id }}/edit" style="max-width:480px">
  <div class="mb-3">
    <label class="form-label text-muted">Email</label>
    <p class="form-control-plaintext fw-semibold">{{ user.email }}</p>
  </div>
  <div class="mb-3">
    <label class="form-label d-block">權限</label>
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="can_create" id="can_create" value="true"
             {% if user.can_create %}checked{% endif %}>
      <label class="form-check-label" for="can_create">可新增訂閱</label>
    </div>
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="can_update" id="can_update" value="true"
             {% if user.can_update %}checked{% endif %}>
      <label class="form-check-label" for="can_update">可修改訂閱</label>
    </div>
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="can_delete" id="can_delete" value="true"
             {% if user.can_delete %}checked{% endif %}>
      <label class="form-check-label" for="can_delete">可刪除訂閱</label>
    </div>
  </div>
  <div class="mb-4">
    <label class="form-label d-block">帳號狀態</label>
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="is_active" id="is_active" value="true"
             {% if user.is_active %}checked{% endif %}>
      <label class="form-check-label" for="is_active">啟用中</label>
    </div>
  </div>
  <button type="submit" class="btn btn-primary">儲存</button>
  <a href="/admin/users" class="btn btn-secondary ms-2">取消</a>
</form>
{% endblock %}
```

- [ ] **Step 6: Add admin router to app.py**

Replace the full contents of `src/interfaces/web/app.py` with:

```python
# src/interfaces/web/app.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from src.interfaces.web.routes.subscriptions import router as sub_router
from src.interfaces.web.routes.auth import router as auth_router
from src.interfaces.web.routes.admin import router as admin_router
from src.interfaces.web.dependencies import NotAuthenticatedException, ForbiddenException

app = FastAPI(title="SaaS Subscription Tracker")

app.include_router(auth_router)
app.include_router(sub_router)
app.include_router(admin_router)


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

- [ ] **Step 7: Commit**

```bash
git add src/interfaces/web/routes/admin.py src/interfaces/web/templates/admin/ src/interfaces/web/app.py
git commit -m "feat: add admin user management routes and templates"
```

---

### Task 9: Seed admin account + end-to-end verification

**Files:**
- Create: `scripts/seed_admin.py`

- [ ] **Step 1: Create seed_admin.py**

```python
# scripts/seed_admin.py
"""
Bootstrap the first admin account. Run ONCE after creating the users table.
Usage:  python scripts/seed_admin.py
Default credentials:  admin@gilliontec.com.tw  /  Admin@123!
Change the password immediately after first login.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from src.infrastructure.database.session import SessionLocal
from src.infrastructure.database.sql_user_repository import SqlUserRepository
from src.infrastructure.auth.hash_utils import hash_password
from src.domain.entities.user import User

session = SessionLocal()
repo = SqlUserRepository(session)

existing = repo.get_by_email("admin@gilliontec.com.tw")
if existing:
    print("Admin already exists — no changes made.")
else:
    admin = User(
        email="admin@gilliontec.com.tw",
        display_name="系統管理員",
        hashed_password=hash_password("Admin@123!"),
        role="admin",
        can_create=True,
        can_update=True,
        can_delete=True,
    )
    repo.add(admin)
    print("✅ Admin account created:")
    print("   Email:    admin@gilliontec.com.tw")
    print("   Password: Admin@123!")
    print("   ⚠️  Change this password immediately after first login!")

session.close()
```

- [ ] **Step 2: Run seed script**

```
python scripts/seed_admin.py
```
Expected output:
```
✅ Admin account created:
   Email:    admin@gilliontec.com.tw
   Password: Admin@123!
   ⚠️  Change this password immediately after first login!
```

- [ ] **Step 3: Start app and run end-to-end verification**

```
python main.py
```

Open `http://localhost:8000` and verify each step:

1. Browser redirects to `/login` ✓
2. Enter wrong password → "帳號或密碼錯誤，請重試。" appears ✓
3. Enter `admin@gilliontec.com.tw` / `Admin@123!` → redirects to `/` ✓
4. Navbar shows "系統管理員", "👥 使用者管理", "登出", "＋ 新增訂閱" ✓
5. Click "👥 使用者管理" → `/admin/users` shows admin row with `Admin` badge ✓
6. Click "＋ 新增使用者" → fill `test@gilliontec.com.tw`, check only "可新增訂閱" → click 建立 ✓
7. Row appears in user list with ✅ only in 新增 column ✓
8. Try `outside@gmail.com` → "Email must end with @gilliontec.com.tw" error ✓
9. Click "登出" → back to login page ✓
10. Log in as `test@gilliontec.com.tw` → can see subscriptions, ＋ 新增訂閱 visible ✓
11. Log in as `test@gilliontec.com.tw` → try editing (no can_update) → 403 page ✓

- [ ] **Step 4: Run full test suite**

```
pytest tests/ -v
```
Expected: all previously passing tests still pass + all new auth tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/seed_admin.py
git commit -m "feat: seed admin script; Plan 1 auth system complete"
```

---

## Self-Review

**Spec coverage:**
- ✅ Login/logout with signed-cookie sessions
- ✅ Accounts restricted to @gilliontec.com.tw
- ✅ Admin role with full access
- ✅ Per-user can_create / can_update / can_delete flags
- ✅ Admin can manage user accounts + permissions via web UI
- ✅ Subscription routes protected (unauthenticated → /login, unauthorized → 403)
- ✅ current_user passed to all templates (navbar shows name, logout)

**No placeholders:** All code blocks contain complete, runnable code.

**Type consistency:** `User` entity, `UserRepository`, `SqlUserRepository`, use cases, dependencies, and routes all use the same field names throughout.

---

## What's in Plan 2 (coming after this is deployed)

Plan 2 will add:
- **Subscription status** — enum: `active` / `renewed` / `cancelled` / `suspended`; badge display in table; status filter
- **Cost tracking** — `cost` (Decimal) + `currency` (TWD/USD/EUR) fields; total cost dashboard widget
- **Search + filter + sort** — client-side JS filter bar (service name, status, expiry range); server-side sort by expiry
- **Dashboard** — summary cards: total active, expiring in 7/30 days, total monthly cost
- **Audit log** — `audit_log` table recording who changed what and when; log viewer page (admin only)
- **CSV export** — download all subscriptions as CSV (one click in index page)
- **Change password** — self-service page at `/account/password` (any logged-in user)
