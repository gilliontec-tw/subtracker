# User Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add admin-only user management: list users, invite new users by email, edit role/status, delete, and a public invite-acceptance page for setting passwords.

**Architecture:** Clean Architecture — new use cases in `application/use_cases/`, two new FastAPI routers (`users`, `invite`) added to the existing `main.py`, and a new React page + modals following established patterns. No DB migrations needed — all required columns (`invite_token`, `invite_token_expires_at`, `is_active`, etc.) already exist on the `users` table.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, bcrypt, React 19, TanStack Query v5, react-hook-form + zod v4, Tailwind CSS v4, shadcn/ui (Dialog, Select, Input, Button, Badge, Table).

---

## File Map

**Create (backend):**
- `backend/src/domain/exceptions.py` — add `DuplicateEmailException`, `LastAdminException`
- `backend/src/api/exception_handlers.py` — add handlers for the two new exceptions
- `backend/src/application/use_cases/create_user.py`
- `backend/src/application/use_cases/update_user.py`
- `backend/src/application/use_cases/toggle_user_status.py`
- `backend/src/application/use_cases/delete_user.py`
- `backend/src/application/use_cases/validate_invite.py`
- `backend/src/application/use_cases/accept_invite.py`
- `backend/src/api/v1/schemas/user.py`
- `backend/src/api/v1/routers/users.py`
- `backend/src/api/v1/routers/invite.py`
- `backend/tests/unit/test_create_user_use_case.py`
- `backend/tests/unit/test_delete_user_use_case.py`
- `backend/tests/unit/test_accept_invite_use_case.py`

**Modify (backend):**
- `backend/src/api/main.py` — include users + invite routers

**Create (frontend):**
- `frontend/src/api/users.ts`
- `frontend/src/pages/UsersPage.tsx`
- `frontend/src/components/users/CreateUserModal.tsx`
- `frontend/src/components/users/EditUserModal.tsx`
- `frontend/src/components/users/DeleteUserDialog.tsx`
- `frontend/src/pages/InvitePage.tsx`

**Modify (frontend):**
- `frontend/src/types/api.ts` — add `UserDetail` interface
- `frontend/src/App.tsx` — add `/users` and `/invite/:token` routes
- `frontend/src/layouts/AppLayout.tsx` — add Users nav link (admin only)

---

## Task 1: Domain exceptions + all backend use cases + tests

**Context:** Working directory is `backend/`. Run pytest from `backend/` with venv active (`.venv\Scripts\activate`). The `User` entity is in `backend/src/domain/entities/user.py` and has fields: `email`, `display_name`, `password_hash`, `role`, `can_create`, `can_update`, `can_delete`, `is_active`, `id`, `invite_token`, `invite_token_expires_at`, `created_at`, `updated_at`. `SqlUserRepository` already has `get_by_id`, `get_by_email`, `get_by_invite_token`, `list_all`, `save`, `delete` — no changes needed to it. Tests use `MagicMock` + `AsyncMock` against the repository interface, no DB required.

**Files:**
- Modify: `backend/src/domain/exceptions.py`
- Modify: `backend/src/api/exception_handlers.py`
- Create: `backend/src/application/use_cases/create_user.py`
- Create: `backend/src/application/use_cases/update_user.py`
- Create: `backend/src/application/use_cases/toggle_user_status.py`
- Create: `backend/src/application/use_cases/delete_user.py`
- Create: `backend/src/application/use_cases/validate_invite.py`
- Create: `backend/src/application/use_cases/accept_invite.py`
- Create: `backend/tests/unit/test_create_user_use_case.py`
- Create: `backend/tests/unit/test_delete_user_use_case.py`
- Create: `backend/tests/unit/test_accept_invite_use_case.py`

---

- [ ] **Step 1: Add two new domain exceptions**

Replace the contents of `backend/src/domain/exceptions.py`:

```python
class DomainException(Exception):
    pass


class NotAuthenticatedException(DomainException):
    pass


class ForbiddenException(DomainException):
    pass


class NotFoundException(DomainException):
    pass


class DuplicateEmailException(DomainException):
    pass


class LastAdminException(DomainException):
    pass
```

- [ ] **Step 2: Add exception handlers for the two new exceptions**

In `backend/src/api/exception_handlers.py`, add two imports and two handlers inside `register_exception_handlers`. The final file:

```python
import logging

from domain.exceptions import (
    DuplicateEmailException,
    ForbiddenException,
    LastAdminException,
    NotAuthenticatedException,
    NotFoundException,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotAuthenticatedException)
    async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
        return JSONResponse(
            status_code=401,
            content={"success": False, "data": None, "message": "請先登入", "meta": None},
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_handler(request: Request, exc: ForbiddenException):
        return JSONResponse(
            status_code=403,
            content={"success": False, "data": None, "message": "權限不足", "meta": None},
        )

    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException):
        return JSONResponse(
            status_code=404,
            content={"success": False, "data": None, "message": "資源不存在", "meta": None},
        )

    @app.exception_handler(DuplicateEmailException)
    async def duplicate_email_handler(request: Request, exc: DuplicateEmailException):
        return JSONResponse(
            status_code=409,
            content={"success": False, "data": None, "message": "此 Email 已被使用", "meta": None},
        )

    @app.exception_handler(LastAdminException)
    async def last_admin_handler(request: Request, exc: LastAdminException):
        return JSONResponse(
            status_code=400,
            content={"success": False, "data": None, "message": "無法刪除唯一的管理員", "meta": None},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "message": "伺服器錯誤，請稍後再試",
                "meta": None,
            },
        )
```

- [ ] **Step 3: Create CreateUserUseCase**

Create `backend/src/application/use_cases/create_user.py`:

```python
import uuid
from datetime import datetime, timedelta

from domain.entities.user import User
from domain.exceptions import DuplicateEmailException
from domain.repositories.user_repository import UserRepository


class CreateUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, email: str, display_name: str, role: str) -> User:
        existing = await self._repo.get_by_email(email)
        if existing is not None:
            raise DuplicateEmailException(email)

        is_admin = role == "admin"
        token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)

        user = User(
            email=email,
            display_name=display_name,
            password_hash="",
            role=role,
            can_create=is_admin,
            can_update=is_admin,
            can_delete=is_admin,
            is_active=True,
            invite_token=token,
            invite_token_expires_at=expires_at,
        )
        return await self._repo.save(user)
```

- [ ] **Step 4: Create UpdateUserUseCase**

Create `backend/src/application/use_cases/update_user.py`:

```python
from domain.entities.user import User
from domain.exceptions import NotFoundException
from domain.repositories.user_repository import UserRepository


class UpdateUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, id: int, display_name: str, role: str) -> User:
        user = await self._repo.get_by_id(id)
        if user is None:
            raise NotFoundException(f"User {id} not found")

        is_admin = role == "admin"
        user.display_name = display_name
        user.role = role
        user.can_create = is_admin
        user.can_update = is_admin
        user.can_delete = is_admin
        return await self._repo.save(user)
```

- [ ] **Step 5: Create ToggleUserStatusUseCase**

Create `backend/src/application/use_cases/toggle_user_status.py`:

```python
from domain.entities.user import User
from domain.exceptions import NotFoundException
from domain.repositories.user_repository import UserRepository


class ToggleUserStatusUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, id: int, is_active: bool) -> User:
        user = await self._repo.get_by_id(id)
        if user is None:
            raise NotFoundException(f"User {id} not found")
        user.is_active = is_active
        return await self._repo.save(user)
```

- [ ] **Step 6: Create DeleteUserUseCase**

Create `backend/src/application/use_cases/delete_user.py`:

```python
from domain.exceptions import LastAdminException, NotFoundException
from domain.repositories.user_repository import UserRepository


class DeleteUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, id: int) -> None:
        user = await self._repo.get_by_id(id)
        if user is None:
            raise NotFoundException(f"User {id} not found")

        if user.role == "admin":
            all_users = await self._repo.list_all()
            admin_count = sum(1 for u in all_users if u.role == "admin")
            if admin_count <= 1:
                raise LastAdminException("Cannot delete the only admin")

        await self._repo.delete(id)
```

- [ ] **Step 7: Create ValidateInviteUseCase**

Create `backend/src/application/use_cases/validate_invite.py`:

```python
from datetime import datetime

from domain.entities.user import User
from domain.exceptions import NotFoundException
from domain.repositories.user_repository import UserRepository


class ValidateInviteUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, token: str) -> User:
        user = await self._repo.get_by_invite_token(token)
        if user is None:
            raise NotFoundException("Invite token not found or expired")
        if user.invite_token_expires_at is None or user.invite_token_expires_at < datetime.utcnow():
            raise NotFoundException("Invite token not found or expired")
        return user
```

- [ ] **Step 8: Create AcceptInviteUseCase**

Create `backend/src/application/use_cases/accept_invite.py`:

```python
from datetime import datetime

import bcrypt

from domain.exceptions import NotFoundException
from domain.repositories.user_repository import UserRepository


class AcceptInviteUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, token: str, password: str) -> None:
        user = await self._repo.get_by_invite_token(token)
        if user is None:
            raise NotFoundException("Invite token not found or expired")
        if user.invite_token_expires_at is None or user.invite_token_expires_at < datetime.utcnow():
            raise NotFoundException("Invite token not found or expired")

        user.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user.invite_token = None
        user.invite_token_expires_at = None
        await self._repo.save(user)
```

- [ ] **Step 9: Write tests for CreateUserUseCase**

Create `backend/tests/unit/test_create_user_use_case.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.create_user import CreateUserUseCase
from domain.entities.user import User
from domain.exceptions import DuplicateEmailException


def make_user(**kwargs) -> User:
    defaults = dict(
        id=1,
        email="u@corp.com",
        display_name="User",
        password_hash="hash",
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
        is_active=True,
    )
    defaults.update(kwargs)
    return User(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return CreateUserUseCase(repo)


@pytest.mark.asyncio
async def test_creates_user_with_invite_token(use_case, repo):
    repo.get_by_email = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda u: u)

    user = await use_case.execute(email="new@corp.com", display_name="New User", role="user")

    assert user.email == "new@corp.com"
    assert user.invite_token is not None
    assert user.invite_token_expires_at is not None
    assert user.password_hash == ""
    assert user.is_active is True


@pytest.mark.asyncio
async def test_admin_role_sets_all_permissions(use_case, repo):
    repo.get_by_email = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda u: u)

    user = await use_case.execute(email="admin@corp.com", display_name="Admin", role="admin")

    assert user.can_create is True
    assert user.can_update is True
    assert user.can_delete is True


@pytest.mark.asyncio
async def test_user_role_has_no_permissions(use_case, repo):
    repo.get_by_email = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda u: u)

    user = await use_case.execute(email="user@corp.com", display_name="User", role="user")

    assert user.can_create is False
    assert user.can_update is False
    assert user.can_delete is False


@pytest.mark.asyncio
async def test_raises_if_email_already_exists(use_case, repo):
    repo.get_by_email = AsyncMock(return_value=make_user(email="dup@corp.com"))

    with pytest.raises(DuplicateEmailException):
        await use_case.execute(email="dup@corp.com", display_name="New", role="user")
```

- [ ] **Step 10: Run CreateUserUseCase tests — verify they pass**

Run: `pytest tests/unit/test_create_user_use_case.py -v`
Expected: 4 tests PASSED

- [ ] **Step 11: Write tests for DeleteUserUseCase**

Create `backend/tests/unit/test_delete_user_use_case.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.delete_user import DeleteUserUseCase
from domain.entities.user import User
from domain.exceptions import LastAdminException, NotFoundException


def make_user(**kwargs) -> User:
    defaults = dict(
        id=1,
        email="u@corp.com",
        display_name="User",
        password_hash="hash",
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
        is_active=True,
    )
    defaults.update(kwargs)
    return User(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return DeleteUserUseCase(repo)


@pytest.mark.asyncio
async def test_raises_when_user_not_found(use_case, repo):
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await use_case.execute(99)


@pytest.mark.asyncio
async def test_deletes_non_admin(use_case, repo):
    user = make_user(id=2, role="user")
    repo.get_by_id = AsyncMock(return_value=user)
    repo.delete = AsyncMock()

    await use_case.execute(2)

    repo.delete.assert_called_once_with(2)


@pytest.mark.asyncio
async def test_raises_when_deleting_last_admin(use_case, repo):
    admin = make_user(id=1, role="admin", can_create=True, can_update=True, can_delete=True)
    repo.get_by_id = AsyncMock(return_value=admin)
    repo.list_all = AsyncMock(return_value=[admin])

    with pytest.raises(LastAdminException):
        await use_case.execute(1)


@pytest.mark.asyncio
async def test_deletes_admin_when_another_admin_exists(use_case, repo):
    admin1 = make_user(id=1, role="admin", can_create=True, can_update=True, can_delete=True)
    admin2 = make_user(id=2, email="a2@corp.com", role="admin", can_create=True, can_update=True, can_delete=True)
    repo.get_by_id = AsyncMock(return_value=admin1)
    repo.list_all = AsyncMock(return_value=[admin1, admin2])
    repo.delete = AsyncMock()

    await use_case.execute(1)

    repo.delete.assert_called_once_with(1)
```

- [ ] **Step 12: Run DeleteUserUseCase tests — verify they pass**

Run: `pytest tests/unit/test_delete_user_use_case.py -v`
Expected: 4 tests PASSED

- [ ] **Step 13: Write tests for AcceptInviteUseCase**

Create `backend/tests/unit/test_accept_invite_use_case.py`:

```python
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.accept_invite import AcceptInviteUseCase
from domain.entities.user import User
from domain.exceptions import NotFoundException


def make_user(**kwargs) -> User:
    defaults = dict(
        id=1,
        email="u@corp.com",
        display_name="User",
        password_hash="",
        role="user",
        can_create=False,
        can_update=False,
        can_delete=False,
        is_active=True,
        invite_token="validtoken",
        invite_token_expires_at=datetime.utcnow() + timedelta(days=1),
    )
    defaults.update(kwargs)
    return User(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return AcceptInviteUseCase(repo)


@pytest.mark.asyncio
async def test_sets_password_hash_and_clears_token(use_case, repo):
    user = make_user()
    repo.get_by_invite_token = AsyncMock(return_value=user)
    repo.save = AsyncMock(side_effect=lambda u: u)

    await use_case.execute("validtoken", "mynewpassword123")

    saved = repo.save.call_args[0][0]
    assert saved.password_hash != ""
    assert saved.invite_token is None
    assert saved.invite_token_expires_at is None


@pytest.mark.asyncio
async def test_raises_for_unknown_token(use_case, repo):
    repo.get_by_invite_token = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await use_case.execute("badtoken", "password")


@pytest.mark.asyncio
async def test_raises_for_expired_token(use_case, repo):
    user = make_user(invite_token_expires_at=datetime.utcnow() - timedelta(days=1))
    repo.get_by_invite_token = AsyncMock(return_value=user)

    with pytest.raises(NotFoundException):
        await use_case.execute("validtoken", "password")
```

- [ ] **Step 14: Run AcceptInviteUseCase tests — verify they pass**

Run: `pytest tests/unit/test_accept_invite_use_case.py -v`
Expected: 3 tests PASSED

- [ ] **Step 15: Run full test suite — verify nothing broken**

Run: `pytest -v`
Expected: All tests PASSED (no regressions)

- [ ] **Step 16: Commit**

```bash
git add backend/src/domain/exceptions.py \
        backend/src/api/exception_handlers.py \
        backend/src/application/use_cases/create_user.py \
        backend/src/application/use_cases/update_user.py \
        backend/src/application/use_cases/toggle_user_status.py \
        backend/src/application/use_cases/delete_user.py \
        backend/src/application/use_cases/validate_invite.py \
        backend/src/application/use_cases/accept_invite.py \
        backend/tests/unit/test_create_user_use_case.py \
        backend/tests/unit/test_delete_user_use_case.py \
        backend/tests/unit/test_accept_invite_use_case.py
git commit -m "feat: add user management use cases and tests"
```

---

## Task 2: Backend API layer — schemas, routers, main.py registration

**Context:** Working directory is `backend/`. The API follows a pattern where: all responses use `ApiResponse` from `api/v1/schemas/base.py`; routers are included in `api/main.py` with `app.include_router(...)`; the `require_admin` dependency from `api/dependencies.py` guards admin-only endpoints. The `/invite` endpoints are public (no auth required). The `request.base_url` in FastAPI gives the API base URL — but the invite URL must point to the **frontend** `/invite/:token` page. Return just the `invite_token` from the create endpoint; the frontend constructs the full URL from `window.location.origin`.

**Files:**
- Create: `backend/src/api/v1/schemas/user.py`
- Create: `backend/src/api/v1/routers/users.py`
- Create: `backend/src/api/v1/routers/invite.py`
- Modify: `backend/src/api/main.py`

---

- [ ] **Step 1: Create user schemas**

Create `backend/src/api/v1/schemas/user.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, EmailStr
from typing import Literal

RoleType = Literal["admin", "user"]


class UserListItemResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: str | None


class CreateUserRequest(BaseModel):
    email: EmailStr
    display_name: str
    role: RoleType


class CreateUserResponse(BaseModel):
    id: int
    invite_token: str


class UpdateUserRequest(BaseModel):
    display_name: str
    role: RoleType


class UserStatusRequest(BaseModel):
    is_active: bool


class InviteValidateResponse(BaseModel):
    email: str


class InviteAcceptRequest(BaseModel):
    password: str
```

- [ ] **Step 2: Create users router**

Create `backend/src/api/v1/routers/users.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, require_admin
from api.v1.schemas.base import ApiResponse
from api.v1.schemas.user import (
    CreateUserRequest,
    CreateUserResponse,
    UpdateUserRequest,
    UserListItemResponse,
    UserStatusRequest,
)
from application.use_cases.create_user import CreateUserUseCase
from application.use_cases.delete_user import DeleteUserUseCase
from application.use_cases.toggle_user_status import ToggleUserStatusUseCase
from application.use_cases.update_user import UpdateUserUseCase
from infrastructure.database.repositories.user_repository import SqlUserRepository

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _to_response(user) -> UserListItemResponse:
    return UserListItemResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        created_at=str(user.created_at.date()) if user.created_at else None,
    )


@router.get("", response_model=ApiResponse[list[UserListItemResponse]])
async def list_users(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    users = await repo.list_all()
    return ApiResponse.ok(data=[_to_response(u) for u in users])


@router.post("", response_model=ApiResponse[CreateUserResponse])
async def create_user(
    body: CreateUserRequest,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = CreateUserUseCase(repo)
    user = await use_case.execute(
        email=body.email,
        display_name=body.display_name,
        role=body.role,
    )
    return ApiResponse.ok(data=CreateUserResponse(id=user.id, invite_token=user.invite_token))


@router.patch("/{id}", response_model=ApiResponse[UserListItemResponse])
async def update_user(
    id: int,
    body: UpdateUserRequest,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = UpdateUserUseCase(repo)
    user = await use_case.execute(id=id, display_name=body.display_name, role=body.role)
    return ApiResponse.ok(data=_to_response(user))


@router.patch("/{id}/status", response_model=ApiResponse[UserListItemResponse])
async def toggle_status(
    id: int,
    body: UserStatusRequest,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = ToggleUserStatusUseCase(repo)
    user = await use_case.execute(id=id, is_active=body.is_active)
    return ApiResponse.ok(data=_to_response(user))


@router.delete("/{id}", response_model=ApiResponse[None])
async def delete_user(
    id: int,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = DeleteUserUseCase(repo)
    await use_case.execute(id=id)
    return ApiResponse.ok()
```

- [ ] **Step 3: Create invite router**

Create `backend/src/api/v1/routers/invite.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from api.v1.schemas.base import ApiResponse
from api.v1.schemas.user import InviteAcceptRequest, InviteValidateResponse
from application.use_cases.accept_invite import AcceptInviteUseCase
from application.use_cases.validate_invite import ValidateInviteUseCase
from infrastructure.database.repositories.user_repository import SqlUserRepository

router = APIRouter(prefix="/api/v1/invite", tags=["invite"])


@router.get("/{token}", response_model=ApiResponse[InviteValidateResponse])
async def validate_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = ValidateInviteUseCase(repo)
    user = await use_case.execute(token)
    return ApiResponse.ok(data=InviteValidateResponse(email=user.email))


@router.post("/{token}", response_model=ApiResponse[None])
async def accept_invite(
    token: str,
    body: InviteAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = SqlUserRepository(db)
    use_case = AcceptInviteUseCase(repo)
    await use_case.execute(token=token, password=body.password)
    return ApiResponse.ok(message="密碼設定成功，請登入")
```

- [ ] **Step 4: Register routers in main.py**

Replace `backend/src/api/main.py` with:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.exception_handlers import register_exception_handlers
from api.middleware.csrf import CSRFMiddleware
from api.v1.routers.auth import router as auth_router
from api.v1.routers.invite import router as invite_router
from api.v1.routers.subscriptions import router as subscriptions_router
from api.v1.routers.users import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="SubTrack API",
        version="1.0.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )
    app.add_middleware(CSRFMiddleware)

    register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(subscriptions_router)
    app.include_router(users_router)
    app.include_router(invite_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Smoke-test the API starts without errors**

Run from `backend/`:
```bash
python -c "from api.main import app; print('OK')"
```
Expected output: `OK` (no import errors)

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/v1/schemas/user.py \
        backend/src/api/v1/routers/users.py \
        backend/src/api/v1/routers/invite.py \
        backend/src/api/main.py
git commit -m "feat: add users and invite API routers"
```

---

## Task 3: Frontend types + API client

**Context:** Working directory is `frontend/`. API base URL is configured in `src/api/client.ts` as `axios.create({ baseURL: ..., withCredentials: true })`. The interceptor already adds `X-CSRF-Token` for mutating methods. Error messages from the API are in `response.data.message`. Existing pattern for error extraction: catch the axios error and rethrow with the API message (see `src/api/auth.ts`). `zod` v4 is installed (`"zod": "^4.4.3"`) — use it for the invite page form.

**Files:**
- Modify: `frontend/src/types/api.ts`
- Create: `frontend/src/api/users.ts`

---

- [ ] **Step 1: Add UserDetail to api.ts**

Add to `frontend/src/types/api.ts` (append after the existing `ListResponse` interface):

```typescript
export interface UserDetail {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string | null
}
```

- [ ] **Step 2: Create users API client**

Create `frontend/src/api/users.ts`:

```typescript
import type { AxiosError } from 'axios'
import api from './client'
import type { ApiResponse, UserDetail } from '@/types/api'

interface CreateUserPayload {
  email: string
  display_name: string
  role: 'admin' | 'user'
}

interface CreateUserResult {
  id: number
  invite_token: string
}

interface UpdateUserPayload {
  display_name: string
  role: 'admin' | 'user'
}

function extractMessage(err: unknown, fallback: string): never {
  const message =
    (err as AxiosError<ApiResponse<null>>)?.response?.data?.message ?? fallback
  throw new Error(message)
}

export async function listUsers(): Promise<UserDetail[]> {
  const res = await api.get<ApiResponse<UserDetail[]>>('/api/v1/users')
  return res.data.data ?? []
}

export async function createUser(payload: CreateUserPayload): Promise<CreateUserResult> {
  try {
    const res = await api.post<ApiResponse<CreateUserResult>>('/api/v1/users', payload)
    if (!res.data.data) throw new Error(res.data.message)
    return res.data.data
  } catch (err) {
    extractMessage(err, '建立使用者失敗')
  }
}

export async function updateUser(id: number, payload: UpdateUserPayload): Promise<UserDetail> {
  try {
    const res = await api.patch<ApiResponse<UserDetail>>(`/api/v1/users/${id}`, payload)
    if (!res.data.data) throw new Error(res.data.message)
    return res.data.data
  } catch (err) {
    extractMessage(err, '更新失敗')
  }
}

export async function toggleUserStatus(id: number, is_active: boolean): Promise<UserDetail> {
  try {
    const res = await api.patch<ApiResponse<UserDetail>>(`/api/v1/users/${id}/status`, { is_active })
    if (!res.data.data) throw new Error(res.data.message)
    return res.data.data
  } catch (err) {
    extractMessage(err, '更新狀態失敗')
  }
}

export async function deleteUser(id: number): Promise<void> {
  try {
    await api.delete(`/api/v1/users/${id}`)
  } catch (err) {
    extractMessage(err, '刪除失敗')
  }
}

export async function validateInvite(token: string): Promise<{ email: string }> {
  const res = await api.get<ApiResponse<{ email: string }>>(`/api/v1/invite/${token}`)
  if (!res.data.data) throw new Error(res.data.message)
  return res.data.data
}

export async function acceptInvite(token: string, password: string): Promise<void> {
  try {
    await api.post(`/api/v1/invite/${token}`, { password })
  } catch (err) {
    extractMessage(err, '設定密碼失敗')
  }
}
```

- [ ] **Step 3: TypeScript check — no type errors**

Run: `npm run build 2>&1 | head -30` from `frontend/`
Expected: No TypeScript errors in the new files (build may fail on missing pages — that's fine for now, check there are no errors in `types/api.ts` or `api/users.ts`)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/api/users.ts
git commit -m "feat: add UserDetail type and users API client"
```

---

## Task 4: Frontend UsersPage + CreateUserModal + EditUserModal + DeleteUserDialog

**Context:** Working directory is `frontend/`. Follow these established patterns:
- Forms: use `useForm` + `zodResolver` directly; wire `Select` fields via `setValue(field, value, { shouldValidate: true })`; show errors with `errors.field?.message`. No shadcn Form wrappers (FormField/FormLabel/etc.) — build your own local `Field` wrapper component as done in `SubscriptionForm.tsx`.
- Dialogs: use the `Dialog` component with `open` state and a trigger button alongside (not `DialogTrigger`) — see `DeleteConfirmDialog.tsx`.
- Toast: import `useToast` from `@/hooks/use-toast` and call `toast({ title: '...' })`.
- Cache invalidation: use `queryClient.invalidateQueries({ queryKey: ['users'] })` after mutations.
- Available UI components: `Button`, `Input`, `Select`/`SelectContent`/`SelectItem`/`SelectTrigger`/`SelectValue`, `Dialog`/`DialogContent`/`DialogHeader`/`DialogTitle`/`DialogDescription`/`DialogFooter`, `Badge`, `Table`/`TableHeader`/`TableRow`/`TableHead`/`TableBody`/`TableCell`.
- Available icons from `lucide-react`: `Pencil`, `Trash2`, `UserPlus`.

**Files:**
- Create: `frontend/src/pages/UsersPage.tsx`
- Create: `frontend/src/components/users/CreateUserModal.tsx`
- Create: `frontend/src/components/users/EditUserModal.tsx`
- Create: `frontend/src/components/users/DeleteUserDialog.tsx`

---

- [ ] **Step 1: Create DeleteUserDialog**

Create `frontend/src/components/users/DeleteUserDialog.tsx`:

```tsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteUser } from '@/api/users'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Trash2 } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface Props {
  userId: number
  displayName: string
}

export default function DeleteUserDialog({ userId, displayName }: Props) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { mutate, isPending } = useMutation({
    mutationFn: () => deleteUser(userId),
    onSuccess: () => {
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast({ title: `「${displayName}」已刪除` })
    },
    onError: (err: Error) => {
      toast({ title: err.message || '刪除失敗', variant: 'destructive' })
    },
  })

  return (
    <>
      <Button variant="ghost" size="icon" onClick={() => setOpen(true)}>
        <Trash2 className="size-4 text-destructive" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>確認刪除</DialogTitle>
            <DialogDescription>
              確定要刪除「{displayName}」嗎？此操作無法復原。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={isPending}>
              取消
            </Button>
            <Button variant="destructive" onClick={() => mutate()} disabled={isPending}>
              {isPending ? '刪除中...' : '確認刪除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
```

- [ ] **Step 2: Create CreateUserModal**

Create `frontend/src/components/users/CreateUserModal.tsx`:

```tsx
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createUser } from '@/api/users'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { UserPlus } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

const schema = z.object({
  display_name: z.string().min(1, '顯示名稱為必填'),
  email: z.string().min(1, 'Email 為必填').email('請輸入有效的 Email'),
  role: z.enum(['user', 'admin'] as const),
})
type FormValues = z.infer<typeof schema>

function Field({
  label,
  error,
  required,
  children,
}: {
  label: string
  error?: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">
        {label}
        {required && <span className="ml-1 text-destructive">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

export default function CreateUserModal() {
  const [open, setOpen] = useState(false)
  const [inviteToken, setInviteToken] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { display_name: '', email: '', role: 'user' },
  })

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) => createUser(values),
    onSuccess: (data) => {
      setInviteToken(data.invite_token)
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (err: Error) => {
      toast({ title: err.message || '建立失敗', variant: 'destructive' })
    },
  })

  function handleClose() {
    setOpen(false)
    setInviteToken(null)
    setCopied(false)
    reset()
  }

  const inviteUrl = inviteToken
    ? `${window.location.origin}/invite/${inviteToken}`
    : ''

  async function copyToClipboard() {
    await navigator.clipboard.writeText(inviteUrl)
    setCopied(true)
  }

  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <UserPlus className="mr-2 size-4" />
        新增使用者
      </Button>
      <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(); else setOpen(true) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{inviteToken ? '邀請連結已產生' : '新增使用者'}</DialogTitle>
          </DialogHeader>

          {inviteToken ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                請將以下連結傳送給使用者，連結有效期為 7 天。
              </p>
              <div className="flex gap-2">
                <Input readOnly value={inviteUrl} className="text-xs" />
                <Button variant="outline" onClick={copyToClipboard}>
                  {copied ? '已複製' : '複製'}
                </Button>
              </div>
              <Button className="w-full" onClick={handleClose}>
                關閉
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
              <Field label="顯示名稱" error={errors.display_name?.message} required>
                <Input {...register('display_name')} placeholder="王小明" />
              </Field>
              <Field label="Email" error={errors.email?.message} required>
                <Input type="email" {...register('email')} placeholder="user@corp.com" />
              </Field>
              <Field label="角色" error={errors.role?.message} required>
                <Select
                  defaultValue="user"
                  onValueChange={(v) =>
                    setValue('role', v as 'user' | 'admin', { shouldValidate: true })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="user">一般使用者</SelectItem>
                    <SelectItem value="admin">管理員</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Button type="submit" className="w-full" disabled={isPending}>
                {isPending ? '建立中...' : '建立並產生邀請連結'}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
```

- [ ] **Step 3: Create EditUserModal**

Create `frontend/src/components/users/EditUserModal.tsx`:

```tsx
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateUser, toggleUserStatus } from '@/api/users'
import type { UserDetail } from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Pencil } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

const schema = z.object({
  display_name: z.string().min(1, '顯示名稱為必填'),
  role: z.enum(['user', 'admin'] as const),
  is_active: z.enum(['active', 'inactive'] as const),
})
type FormValues = z.infer<typeof schema>

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

interface Props {
  user: UserDetail
}

export default function EditUserModal({ user }: Props) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: user.display_name,
      role: user.role,
      is_active: user.is_active ? 'active' : 'inactive',
    },
  })

  const { mutate, isPending } = useMutation({
    mutationFn: async (values: FormValues) => {
      const newIsActive = values.is_active === 'active'
      await updateUser(user.id, { display_name: values.display_name, role: values.role })
      if (newIsActive !== user.is_active) {
        await toggleUserStatus(user.id, newIsActive)
      }
    },
    onSuccess: () => {
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast({ title: '使用者已更新' })
    },
    onError: (err: Error) => {
      toast({ title: err.message || '更新失敗', variant: 'destructive' })
    },
  })

  return (
    <>
      <Button variant="ghost" size="icon" onClick={() => setOpen(true)}>
        <Pencil className="size-4" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>編輯使用者</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
            <Field label="顯示名稱" error={errors.display_name?.message}>
              <Input {...register('display_name')} />
            </Field>
            <Field label="角色" error={errors.role?.message}>
              <Select
                defaultValue={user.role}
                onValueChange={(v) =>
                  setValue('role', v as 'user' | 'admin', { shouldValidate: true })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">一般使用者</SelectItem>
                  <SelectItem value="admin">管理員</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="狀態">
              <Select
                defaultValue={user.is_active ? 'active' : 'inactive'}
                onValueChange={(v) =>
                  setValue('is_active', v as 'active' | 'inactive', { shouldValidate: true })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">啟用中</SelectItem>
                  <SelectItem value="inactive">已停用</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? '儲存中...' : '儲存'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
```

- [ ] **Step 4: Create UsersPage**

Create `frontend/src/pages/UsersPage.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query'
import { listUsers } from '@/api/users'
import CreateUserModal from '@/components/users/CreateUserModal'
import EditUserModal from '@/components/users/EditUserModal'
import DeleteUserDialog from '@/components/users/DeleteUserDialog'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function UsersPage() {
  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: listUsers,
  })

  if (isLoading) {
    return <div className="text-muted-foreground">載入中...</div>
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">使用者管理</h1>
        <CreateUserModal />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>顯示名稱</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>角色</TableHead>
            <TableHead>狀態</TableHead>
            <TableHead>建立日期</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                沒有使用者資料
              </TableCell>
            </TableRow>
          )}
          {users.map((user) => (
            <TableRow key={user.id}>
              <TableCell className="font-medium">{user.display_name}</TableCell>
              <TableCell className="text-muted-foreground">{user.email}</TableCell>
              <TableCell>
                {user.role === 'admin' ? (
                  <Badge className="border-transparent bg-purple-100 text-purple-800 hover:bg-purple-100">
                    管理員
                  </Badge>
                ) : (
                  <Badge variant="secondary">一般使用者</Badge>
                )}
              </TableCell>
              <TableCell>
                {user.is_active ? (
                  <Badge className="border-transparent bg-green-100 text-green-800 hover:bg-green-100">
                    啟用中
                  </Badge>
                ) : (
                  <Badge variant="secondary">已停用</Badge>
                )}
              </TableCell>
              <TableCell>{user.created_at ?? '—'}</TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-1">
                  <EditUserModal user={user} />
                  <DeleteUserDialog userId={user.id} displayName={user.display_name} />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
```

- [ ] **Step 5: TypeScript check — no errors in new files**

Run from `frontend/`: `npx tsc --noEmit 2>&1 | head -40`
Expected: No errors in `UsersPage.tsx`, `CreateUserModal.tsx`, `EditUserModal.tsx`, `DeleteUserDialog.tsx`. Fix any type errors before continuing.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/UsersPage.tsx \
        frontend/src/components/users/CreateUserModal.tsx \
        frontend/src/components/users/EditUserModal.tsx \
        frontend/src/components/users/DeleteUserDialog.tsx
git commit -m "feat: add UsersPage and user management modals"
```

---

## Task 5: InvitePage + routing + nav link

**Context:** Working directory is `frontend/`. The `InvitePage` is a public page (no auth required) — it must live **outside** the `ProtectedRoute` wrapper in `App.tsx`. It uses the `Card` component from `@/components/ui/card`. The `AppLayout.tsx` header has no nav links yet — add a "使用者管理" link visible only to admins (check `currentUser?.role === 'admin'`). Import `Link` from `react-router-dom` for navigation. `useQuery` with `retry: false` for token validation so an expired/missing token shows the error immediately without retrying.

**Files:**
- Create: `frontend/src/pages/InvitePage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`

---

- [ ] **Step 1: Create InvitePage**

Create `frontend/src/pages/InvitePage.tsx`:

```tsx
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery } from '@tanstack/react-query'
import { validateInvite, acceptInvite } from '@/api/users'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const schema = z
  .object({
    password: z.string().min(8, '密碼至少 8 個字元'),
    confirm_password: z.string().min(1, '請確認密碼'),
  })
  .refine((v) => v.password === v.confirm_password, {
    message: '密碼不一致',
    path: ['confirm_password'],
  })
type FormValues = z.infer<typeof schema>

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

export default function InvitePage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [done, setDone] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['invite', token],
    queryFn: () => validateInvite(token!),
    retry: false,
  })

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  const { mutate, isPending, isError: submitError, error: submitErr } = useMutation({
    mutationFn: (values: FormValues) => acceptInvite(token!, values.password),
    onSuccess: () => {
      setDone(true)
      setTimeout(() => navigate('/login', { replace: true }), 2000)
    },
  })

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        驗證中...
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>邀請連結無效</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              此邀請連結已失效或過期，請聯絡管理員重新產生。
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (done) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>密碼設定成功</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">正在導向登入頁面...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>設定密碼</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs text-muted-foreground">帳號</p>
            <p className="font-medium">{data.email}</p>
          </div>
          <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
            <Field label="密碼" error={errors.password?.message}>
              <Input type="password" {...register('password')} />
            </Field>
            <Field label="確認密碼" error={errors.confirm_password?.message}>
              <Input type="password" {...register('confirm_password')} />
            </Field>
            {submitError && (
              <p className="text-sm text-destructive">
                {(submitErr as Error)?.message || '設定失敗，請稍後再試'}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? '設定中...' : '設定密碼'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Add routes to App.tsx**

Replace `frontend/src/App.tsx` with:

```tsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/toaster'
import ProtectedRoute from '@/components/ProtectedRoute'
import AppLayout from '@/layouts/AppLayout'
import LoginPage from '@/pages/LoginPage'
import SubscriptionsPage from '@/pages/SubscriptionsPage'
import SubscriptionNewPage from '@/pages/SubscriptionNewPage'
import SubscriptionEditPage from '@/pages/SubscriptionEditPage'
import UsersPage from '@/pages/UsersPage'
import InvitePage from '@/pages/InvitePage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/invite/:token" element={<InvitePage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<Navigate to="/subscriptions" replace />} />
              <Route path="/subscriptions" element={<SubscriptionsPage />} />
              <Route path="/subscriptions/new" element={<SubscriptionNewPage />} />
              <Route path="/subscriptions/:id/edit" element={<SubscriptionEditPage />} />
              <Route path="/users" element={<UsersPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryClientProvider>
  )
}
```

- [ ] **Step 3: Add Users nav link to AppLayout (admin only)**

Replace `frontend/src/layouts/AppLayout.tsx` with:

```tsx
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { logout } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'

export default function AppLayout() {
  const navigate = useNavigate()
  const { currentUser, clear } = useAuthStore()
  const { toast } = useToast()

  const { mutate: doLogout } = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      clear()
      navigate('/login', { replace: true })
    },
    onError: () => {
      toast({ title: '登出失敗', variant: 'destructive' })
    },
  })

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b bg-background px-6 py-3">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="text-lg font-semibold">SubTrack</span>
            <nav className="flex items-center gap-4 text-sm">
              <Link
                to="/subscriptions"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                訂閱列表
              </Link>
              {currentUser?.role === 'admin' && (
                <Link
                  to="/users"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  使用者管理
                </Link>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{currentUser?.display_name}</span>
            <Button variant="ghost" size="sm" onClick={() => doLogout()}>
              登出
            </Button>
          </div>
        </div>
      </header>
      <main className="flex-1 px-6 py-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 4: TypeScript check — no errors**

Run from `frontend/`: `npx tsc --noEmit 2>&1 | head -40`
Expected: 0 errors. Fix any before continuing.

- [ ] **Step 5: Run frontend linter**

Run from `frontend/`: `npm run lint 2>&1 | head -40`
Expected: 0 errors. Fix any before continuing.

- [ ] **Step 6: Run backend tests one final time**

Run from `backend/`: `pytest -v`
Expected: All tests PASSED

- [ ] **Step 7: Final commit**

```bash
git add frontend/src/pages/InvitePage.tsx \
        frontend/src/App.tsx \
        frontend/src/layouts/AppLayout.tsx
git commit -m "feat: add InvitePage, routing, and admin nav link"
```
