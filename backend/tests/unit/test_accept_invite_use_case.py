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
