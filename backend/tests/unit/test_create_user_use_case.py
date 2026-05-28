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
